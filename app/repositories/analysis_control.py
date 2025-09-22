from sqlmodel import Session, select, text
from app.database import engine
from app.domain.analysis.control import (
    AnalysisRun, RunScope, RunParams, RunMetrics, RunItem, AnalysisPreset,
    RunPreview, RunStatus, ItemState, ScopeType
)
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import json
import logging

logger = logging.getLogger(__name__)

class AnalysisControlRepo:
    """Repository for Analysis Control Center operations"""

    @staticmethod
    def preview_run(scope: RunScope, params: RunParams) -> RunPreview:
        """Calculate preview metrics for a potential run"""
        import logging
        logger = logging.getLogger(__name__)
        logger.error("ENTRY - preview_run called")

        with Session(engine) as session:
            try:
                # Build query based on scope - but WITHOUT unanalyzed_only filter for preview
                scope_for_preview = scope.model_copy()
                scope_for_preview.unanalyzed_only = False  # Remove filter to get ALL items in scope
                query = AnalysisControlRepo._build_scope_query(scope_for_preview)

                # Execute count query for total items in scope
                count_result = session.execute(text("SELECT COUNT(*) FROM (" + query + ") as preview_query")).first()
                total_items = count_result[0] if count_result else 0

                # Count already analyzed items (unless override_existing is True)
                already_analyzed_count = 0
                if total_items > 0:
                    analyzed_query = (
                        "SELECT COUNT(*) FROM (" + query + ") as scope_items " +
                        "WHERE scope_items.id IN (SELECT DISTINCT item_id FROM item_analysis)"
                    )
                    analyzed_result = session.execute(text(analyzed_query)).first()
                    already_analyzed_count = analyzed_result[0] if analyzed_result else 0

                # Calculate new items that would be processed
                new_items_count = total_items - already_analyzed_count if not params.override_existing else total_items
                final_item_count = min(new_items_count, params.limit)

                # Get sample item IDs (first 10)
                if params.override_existing:
                    sample_query = f"SELECT id FROM ({query}) as sample_query LIMIT 10"
                else:
                    sample_query = f"""
                    SELECT id FROM ({query}) as scope_items
                    WHERE scope_items.id NOT IN (SELECT DISTINCT item_id FROM item_analysis)
                    LIMIT 10
                    """
                sample_results = session.execute(text(sample_query)).fetchall()
                sample_ids = [row[0] for row in sample_results]

                # Calculate preview
                preview = RunPreview.calculate(
                    item_count=final_item_count,
                    rate_per_second=params.rate_per_second,
                    model_tag=params.model_tag
                )
                preview.sample_item_ids = sample_ids
                preview.already_analyzed_count = already_analyzed_count
                preview.new_items_count = new_items_count
                preview.has_conflicts = already_analyzed_count > 0

                # Debug logging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"DEBUG - Preview: item_count={preview.item_count}, already_analyzed={preview.already_analyzed_count}, new_items={preview.new_items_count}, has_conflicts={preview.has_conflicts}")

                return preview

            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"EXCEPTION - Failed to preview run: {e}")
                return RunPreview(item_count=0, estimated_cost_usd=0.0, estimated_duration_minutes=0,
                                already_analyzed_count=0, new_items_count=0, has_conflicts=False)

    @staticmethod
    def _build_scope_query(scope: RunScope) -> str:
        """Build SQL query based on scope definition"""
        base_query = """
            SELECT DISTINCT i.id, i.created_at
            FROM items i
            LEFT JOIN item_analysis a ON a.item_id = i.id
        """

        conditions = []

        # Feed-based scope
        if scope.type == "feeds" and scope.feed_ids:
            feed_ids_str = ",".join(map(str, scope.feed_ids))
            conditions.append(f"i.feed_id IN ({feed_ids_str})")

        # Item-based scope
        if scope.type == "items" and scope.item_ids:
            item_ids_str = ",".join(map(str, scope.item_ids))
            conditions.append(f"i.id IN ({item_ids_str})")

        # Article-based scope (specific articles selection)
        if scope.type == "articles" and scope.article_ids:
            article_ids_str = ",".join(map(str, scope.article_ids))
            conditions.append(f"i.id IN ({article_ids_str})")

        # Time-based scope
        if scope.type == "timerange":
            if scope.start_time:
                conditions.append(f"i.created_at >= '{scope.start_time.isoformat()}'")
            if scope.end_time:
                conditions.append(f"i.created_at <= '{scope.end_time.isoformat()}'")

        # Filters
        if scope.unanalyzed_only:
            conditions.append("a.item_id IS NULL")

        if scope.model_tag_not_current:
            conditions.append("(a.model_tag IS NULL OR a.model_tag != 'gpt-4.1-nano')")

        if scope.min_impact_threshold is not None:
            conditions.append(f"(a.impact_json->>'overall')::numeric >= {scope.min_impact_threshold}")

        if scope.max_impact_threshold is not None:
            conditions.append(f"(a.impact_json->>'overall')::numeric <= {scope.max_impact_threshold}")

        # Add WHERE clause if conditions exist
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        # Always order by newest first
        base_query += " ORDER BY i.created_at DESC"

        return base_query

    @staticmethod
    def create_run(scope: RunScope, params: RunParams) -> AnalysisRun:
        """Create a new analysis run"""
        with Session(engine) as session:
            try:
                # Generate scope hash
                scope_hash = scope.generate_hash()

                # Check for duplicate active runs
                existing_run = session.execute(text("""
                    SELECT id FROM analysis_runs
                    WHERE scope_hash = :scope_hash
                    AND status IN ('pending', 'running', 'paused')
                """), {"scope_hash": scope_hash}).first()

                if existing_run:
                    raise ValueError(f"An active run with the same scope already exists (ID: {existing_run[0]})")

                # Create run record
                now = datetime.utcnow()
                run_result = session.execute(text("""
                    INSERT INTO analysis_runs (
                        created_at, updated_at, scope_json, params_json, scope_hash,
                        status, queued_count, cost_estimate
                    ) VALUES (
                        :created_at, :updated_at, :scope_json, :params_json, :scope_hash,
                        'pending', 0, :cost_estimate
                    ) RETURNING id
                """), {
                    "created_at": now,
                    "updated_at": now,
                    "scope_json": json.dumps(scope.model_dump()),
                    "params_json": json.dumps(params.model_dump()),
                    "scope_hash": scope_hash,
                    "cost_estimate": 0.0  # Will be updated when items are queued
                }).first()

                run_id = run_result[0]

                # Queue items for processing
                items_queued = AnalysisControlRepo._queue_items_for_run(session, run_id, scope, params)

                # Update run with queued count and cost estimate
                preview = RunPreview.calculate(items_queued, params.rate_per_second, params.model_tag)
                session.execute(text("""
                    UPDATE analysis_runs
                    SET queued_count = :count, cost_estimate = :cost
                    WHERE id = :run_id
                """), {
                    "count": items_queued,
                    "cost": preview.estimated_cost_usd,
                    "run_id": run_id
                })

                session.commit()

                # Return created run
                return AnalysisControlRepo.get_run_by_id(run_id)

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to create run: {e}")
                raise

    @staticmethod
    def _queue_items_for_run(session: Session, run_id: int, scope: RunScope, params: RunParams) -> int:
        """Queue items for analysis run"""
        # Build query with limit
        query = AnalysisControlRepo._build_scope_query(scope)

        # Apply override_existing logic - same as in preview_run
        if not params.override_existing:
            # Exclude already analyzed items unless override is enabled
            query_with_filter = f"""
                SELECT id, created_at FROM ({query}) as scope_items
                WHERE scope_items.id NOT IN (SELECT DISTINCT item_id FROM item_analysis)
                ORDER BY created_at DESC
                LIMIT {params.limit}
            """
        else:
            # Include all items if override is enabled
            query_with_filter = f"{query} LIMIT {params.limit}"

        # Insert items into run queue
        session.execute(text(
            "INSERT INTO analysis_run_items (run_id, item_id, state, created_at) " +
            "SELECT :run_id, id, 'queued', NOW() " +
            "FROM (" + query_with_filter + ") as items_to_queue"
        ), {"run_id": run_id})

        # Return count of queued items
        count_result = session.execute(text("""
            SELECT COUNT(*) FROM analysis_run_items WHERE run_id = :run_id
        """), {"run_id": run_id}).first()

        return count_result[0] if count_result else 0

    @staticmethod
    def get_run_by_id(run_id: int) -> Optional[AnalysisRun]:
        """Get analysis run by ID with current metrics"""
        with Session(engine) as session:
            try:
                # Get run data
                run_result = session.execute(text("""
                    SELECT
                        id, created_at, updated_at, scope_json, params_json, scope_hash,
                        status, started_at, completed_at, last_error,
                        cost_estimate, actual_cost, coverage_10m, coverage_60m
                    FROM analysis_runs WHERE id = :run_id
                """), {"run_id": run_id}).first()

                if not run_result:
                    return None

                # Get current metrics using AnalysisQueueRepo
                from app.repositories.analysis_queue import AnalysisQueueRepo
                queue_metrics = AnalysisQueueRepo.get_run_metrics(run_id)

                # Calculate additional metrics
                items_per_min = 0.0
                if run_result[8]:  # started_at
                    started_at = run_result[8]
                    if started_at.tzinfo is None:
                        # Make timezone-naive datetime timezone-aware (UTC)
                        started_at = started_at.replace(tzinfo=timezone.utc)

                    elapsed_minutes = (datetime.utcnow().replace(tzinfo=timezone.utc) - started_at).total_seconds() / 60
                    if elapsed_minutes > 0:
                        items_per_min = queue_metrics.get("processed_count", 0) / elapsed_minutes

                # Build metrics object using queue_metrics (which has correct costs)
                metrics = RunMetrics(
                    queued_count=queue_metrics.get("queued_count", 0),
                    processed_count=queue_metrics.get("processed_count", 0),
                    failed_count=queue_metrics.get("failed_count", 0),
                    error_rate=queue_metrics.get("error_rate", 0.0),
                    eta_seconds=None,  # Not provided by queue_metrics
                    items_per_minute=round(items_per_min, 2),
                    actual_cost_usd=queue_metrics.get("actual_cost_usd", 0.0),  # Use correct cost from items
                    estimated_cost_usd=float(run_result[10]) if run_result[10] else 0.0,
                    coverage_10m=float(run_result[12]) if run_result[12] else 0.0,
                    coverage_60m=float(run_result[13]) if run_result[13] else 0.0
                )
                metrics.update_derived_metrics()

                # Build run object
                run = AnalysisRun(
                    id=run_result[0],
                    created_at=run_result[1],
                    updated_at=run_result[2],
                    scope=RunScope(**run_result[3]) if isinstance(run_result[3], dict) else RunScope(**json.loads(run_result[3])),
                    params=RunParams(**run_result[4]) if isinstance(run_result[4], dict) else RunParams(**json.loads(run_result[4])),
                    scope_hash=run_result[5],
                    status=run_result[6],
                    started_at=run_result[7],
                    completed_at=run_result[8],
                    last_error=run_result[9],
                    metrics=metrics
                )

                return run

            except Exception as e:
                logger.error(f"Failed to get run {run_id}: {e}")
                return None

    @staticmethod
    def get_recent_runs(limit: int = 20, offset: int = 0) -> List[AnalysisRun]:
        """Get recent analysis runs"""
        with Session(engine) as session:
            try:
                results = session.execute(text("""
                    SELECT
                        ar.id, ar.created_at, ar.updated_at, ar.scope_json, ar.params_json, ar.scope_hash,
                        ar.status, ar.started_at, ar.completed_at, ar.last_error,
                        ar.cost_estimate,
                        COALESCE(SUM(ari.cost_usd), 0) as actual_cost,  -- Calculate real cost from items
                        ar.queued_count, ar.processed_count, ar.failed_count
                    FROM analysis_runs ar
                    LEFT JOIN analysis_run_items ari ON ari.run_id = ar.id
                    GROUP BY ar.id, ar.created_at, ar.updated_at, ar.scope_json, ar.params_json, ar.scope_hash,
                             ar.status, ar.started_at, ar.completed_at, ar.last_error,
                             ar.cost_estimate, ar.queued_count, ar.processed_count, ar.failed_count
                    ORDER BY ar.created_at DESC
                    LIMIT :limit OFFSET :offset
                """), {"limit": limit, "offset": offset}).fetchall()

                runs = []
                for row in results:
                    # Build minimal metrics for list view
                    metrics = RunMetrics(
                        queued_count=row[12] or 0,
                        processed_count=row[13] or 0,
                        failed_count=row[14] or 0,
                        estimated_cost_usd=float(row[10]) if row[10] else 0.0,
                        actual_cost_usd=float(row[11]) if row[11] else 0.0
                    )
                    metrics.update_derived_metrics()

                    run = AnalysisRun(
                        id=row[0],
                        created_at=row[1],
                        updated_at=row[2],
                        scope=RunScope(**row[3]) if isinstance(row[3], dict) else RunScope(**json.loads(row[3])),
                        params=RunParams(**row[4]) if isinstance(row[4], dict) else RunParams(**json.loads(row[4])),
                        scope_hash=row[5],
                        status=row[6],
                        started_at=row[7],
                        completed_at=row[8],
                        last_error=row[9],
                        metrics=metrics
                    )
                    runs.append(run)

                return runs

            except Exception as e:
                logger.error(f"Failed to get recent runs: {e}")
                return []

    @staticmethod
    def update_run_status(run_id: int, status: RunStatus, error: Optional[str] = None) -> bool:
        """Update run status"""
        with Session(engine) as session:
            try:
                now = datetime.utcnow()
                update_data = {
                    "status": status,
                    "updated_at": now,
                    "run_id": run_id
                }

                if status == "running" and error is None:
                    update_data["started_at"] = now
                elif status in ["completed", "failed", "cancelled"]:
                    update_data["completed_at"] = now

                if error:
                    update_data["last_error"] = error

                # Build dynamic SQL
                set_clauses = ["status = :status", "updated_at = :updated_at"]
                if "started_at" in update_data:
                    set_clauses.append("started_at = :started_at")
                if "completed_at" in update_data:
                    set_clauses.append("completed_at = :completed_at")
                if "last_error" in update_data:
                    set_clauses.append("last_error = :last_error")

                sql = f"UPDATE analysis_runs SET {', '.join(set_clauses)} WHERE id = :run_id"
                session.execute(text(sql), update_data)
                session.commit()
                return True

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to update run status: {e}")
                return False

    @staticmethod
    def get_active_runs() -> List[AnalysisRun]:
        """Get all currently active runs"""
        with Session(engine) as session:
            try:
                # Quick fix: Limit to prevent hanging + direct query instead of N+1
                results = session.execute(text("""
                    SELECT id, status, created_at, started_at, completed_at, scope_json,
                           cost_estimate, updated_at, params_json, scope_hash
                    FROM analysis_runs
                    WHERE status IN ('pending', 'running', 'paused')
                    ORDER BY created_at ASC
                    LIMIT 10
                """)).fetchall()

                # Convert to AnalysisRun objects without additional queries
                runs = []
                for row in results:
                    try:
                        # Get metrics for this run (single query)
                        metrics_result = session.execute(text("""
                            SELECT state, COUNT(*) as count
                            FROM analysis_run_items
                            WHERE run_id = :run_id
                            GROUP BY state
                        """), {"run_id": row[0]}).fetchall()

                        # Build metrics dict
                        metrics_dict = {r[0]: r[1] for r in metrics_result}
                        total = sum(metrics_dict.values())

                        # Calculate progress
                        processed = metrics_dict.get('completed', 0)
                        failed = metrics_dict.get('failed', 0)
                        progress_percent = round((processed / total * 100), 1) if total > 0 else 0.0

                        runs.append(AnalysisRun(
                            id=row[0],
                            status=row[1],
                            created_at=row[2],
                            started_at=row[3],
                            completed_at=row[4],
                            scope=row[5] if row[5] else {},
                            cost_estimate=row[6],
                            updated_at=row[7],
                            params=row[8] if row[8] else {},
                            scope_hash=row[9],
                            metrics=RunMetrics(
                                total_count=total,
                                processed_count=processed,
                                failed_count=failed,
                                queued_count=metrics_dict.get('queued', 0),
                                progress_percent=progress_percent
                            )
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to build run {row[0]}: {e}")
                        continue

                return runs

            except Exception as e:
                logger.error(f"Failed to get active runs: {e}")
                return []

    @staticmethod
    def get_run(run_id: int) -> Optional[AnalysisRun]:
        """Get a specific analysis run by ID"""
        with Session(engine) as session:
            try:
                result = session.execute(text("""
                    SELECT id, status, created_at, started_at, completed_at, scope_json,
                           cost_estimate, updated_at, params_json, scope_hash
                    FROM analysis_runs
                    WHERE id = :run_id
                """), {"run_id": run_id}).fetchone()

                if not result:
                    return None

                # Get metrics for this run
                metrics_result = session.execute(text("""
                    SELECT state, COUNT(*) as count
                    FROM analysis_run_items
                    WHERE run_id = :run_id
                    GROUP BY state
                """), {"run_id": run_id}).fetchall()

                # Build metrics dict
                metrics_dict = {r[0]: r[1] for r in metrics_result}
                total = sum(metrics_dict.values())

                # Calculate progress
                processed = metrics_dict.get('completed', 0)
                failed = metrics_dict.get('failed', 0)
                progress_percent = round((processed / total * 100), 1) if total > 0 else 0.0

                return AnalysisRun(
                    id=result[0],
                    status=result[1],
                    created_at=result[2],
                    started_at=result[3],
                    completed_at=result[4],
                    scope=result[5] if result[5] else {},
                    cost_estimate=result[6],
                    updated_at=result[7],
                    params=result[8] if result[8] else {},
                    scope_hash=result[9],
                    metrics=RunMetrics(
                        total_count=total,
                        processed_count=processed,
                        failed_count=failed,
                        queued_count=metrics_dict.get('queued', 0),
                        progress_percent=progress_percent
                    )
                )

            except Exception as e:
                logger.error(f"Failed to get run {run_id}: {e}")
                return None

    # Preset Management
    @staticmethod
    def save_preset(preset: AnalysisPreset) -> AnalysisPreset:
        """Save analysis preset"""
        with Session(engine) as session:
            try:
                now = datetime.utcnow()
                result = session.execute(text("""
                    INSERT INTO analysis_presets (
                        name, description, scope_json, params_json, created_at, updated_at
                    ) VALUES (
                        :name, :description, :scope_json, :params_json, :created_at, :updated_at
                    )
                    ON CONFLICT (name) DO UPDATE SET
                        description = EXCLUDED.description,
                        scope_json = EXCLUDED.scope_json,
                        params_json = EXCLUDED.params_json,
                        updated_at = EXCLUDED.updated_at
                    RETURNING id
                """), {
                    "name": preset.name,
                    "description": preset.description,
                    "scope_json": json.dumps(preset.scope.model_dump()),
                    "params_json": json.dumps(preset.params.model_dump()),
                    "created_at": now,
                    "updated_at": now
                }).first()

                preset.id = result[0]
                preset.created_at = now
                preset.updated_at = now

                session.commit()
                return preset

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save preset: {e}")
                raise

    @staticmethod
    def get_presets() -> List[AnalysisPreset]:
        """Get all saved presets"""
        with Session(engine) as session:
            try:
                results = session.execute(text("""
                    SELECT id, name, description, scope_json, params_json, created_at, updated_at
                    FROM analysis_presets
                    ORDER BY name ASC
                """)).fetchall()

                presets = []
                for row in results:
                    preset = AnalysisPreset(
                        id=row[0],
                        name=row[1],
                        description=row[2],
                        scope=RunScope(**row[3]) if isinstance(row[3], dict) else RunScope(**json.loads(row[3])),
                        params=RunParams(**row[4]) if isinstance(row[4], dict) else RunParams(**json.loads(row[4])),
                        created_at=row[5],
                        updated_at=row[6]
                    )
                    presets.append(preset)

                return presets

            except Exception as e:
                logger.error(f"Failed to get presets: {e}")
                return []

    @staticmethod
    def delete_preset(preset_id: int) -> bool:
        """Delete analysis preset"""
        with Session(engine) as session:
            try:
                session.execute(text("DELETE FROM analysis_presets WHERE id = :id"), {"id": preset_id})
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to delete preset: {e}")
                return False