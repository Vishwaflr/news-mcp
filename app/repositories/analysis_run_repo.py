"""
Analysis Run Repository

Handles database operations for analysis runs.
Split from analysis_control.py for better maintainability.

Key Responsibilities:
- Create and manage analysis runs
- Queue items for analysis
- Track run status and metrics
- Handle scope-based item selection
- Support skip tracking for already analyzed items

Architecture Notes:
- Uses static methods (no instance state needed)
- Converts between DB models and domain models
- Handles JSON serialization for scope/params
- Supports various scope types (items, feeds, categories, global)

Refactored: 2025-09-30
Original: app/repositories/analysis_control.py (765 lines → 254 lines)
"""

from typing import List, Optional
from datetime import datetime
from sqlmodel import Session, select, func, or_, and_, text
from app.database import engine
from app.models.analysis import AnalysisRun as AnalysisRunDB, AnalysisRunItem
from app.models.core import Item
from app.domain.analysis.control import RunScope, RunParams, RunStatus, AnalysisRun as AnalysisRunDomain, RunMetrics
from app.core.logging_config import get_logger
import json

logger = get_logger(__name__)


class AnalysisRunRepo:
    """
    Repository for analysis run operations.

    This repository manages the lifecycle of analysis runs including:
    - Run creation with proper scope handling
    - Item queueing based on scope filters
    - Status updates and metrics tracking
    - Skip tracking for efficiency
    """

    @staticmethod
    def _convert_to_domain_model(db_run: AnalysisRunDB, scope: Optional[RunScope] = None, params: Optional[RunParams] = None) -> AnalysisRunDomain:
        """
        Convert database model to domain model.

        Args:
            db_run: Database model instance
            scope: Optional pre-parsed scope (avoids re-parsing JSON)
            params: Optional pre-parsed params (avoids re-parsing JSON)

        Returns:
            AnalysisRunDomain: Domain model with all metrics populated
        """
        # Parse JSON fields if needed
        if not scope:
            scope_data = json.loads(db_run.scope_json) if isinstance(db_run.scope_json, str) else db_run.scope_json
            scope = RunScope(**scope_data)

        if not params:
            params_data = json.loads(db_run.params_json) if isinstance(db_run.params_json, str) else db_run.params_json
            params = RunParams(**params_data)

        # Create metrics
        metrics = RunMetrics(
            queued_count=db_run.queued_count or 0,
            processed_count=db_run.processed_count or 0,
            failed_count=db_run.failed_count or 0,
            estimated_cost_usd=db_run.cost_estimate or 0.0,
            actual_cost_usd=db_run.actual_cost or 0.0,
            error_rate=db_run.error_rate or 0.0,
            items_per_min=db_run.items_per_min or 0.0,
            eta_seconds=db_run.eta_seconds or 0,
            coverage_10m=db_run.coverage_10m or 0.0,
            coverage_60m=db_run.coverage_60m or 0.0
        )

        return AnalysisRunDomain(
            id=db_run.id,
            created_at=db_run.created_at,
            updated_at=db_run.updated_at,
            scope=scope,
            params=params,
            scope_hash=db_run.scope_hash or "",
            status=db_run.status,
            started_at=db_run.started_at,
            triggered_by=db_run.triggered_by,
            completed_at=db_run.completed_at,
            last_error=db_run.last_error,
            metrics=metrics
        )

    @staticmethod
    def create_run(scope: RunScope, params: RunParams, triggered_by: str = "manual") -> AnalysisRunDomain:
        """
        Create a new analysis run with skip tracking support.

        Args:
            scope: Defines what items to analyze (feeds, categories, items, etc.)
            params: Run parameters (model, rate limiting, etc.)
            triggered_by: Who triggered the run ("manual", "auto", "scheduled")

        Returns:
            AnalysisRunDomain: Created run with queued items

        Note:
            - Automatically queues items based on scope
            - Sets initial status to "running" if items queued, else "completed"
            - Respects scope.limit and params.limit (params takes precedence if scope.limit is None)
        """

        with Session(engine) as session:
            # Convert scope and params to JSON
            scope_dict = scope.dict() if hasattr(scope, 'dict') else scope
            params_dict = params.dict() if hasattr(params, 'dict') else params

            # Create run record with skip tracking fields
            run = AnalysisRunDB(
                status="pending",
                scope_json=json.dumps(scope_dict),
                params_json=json.dumps(params_dict),
                triggered_by=triggered_by,
                created_at=datetime.utcnow(),
                planned_count=0,  # Will be updated after queueing
                skipped_count=0,
                skipped_items=[]
            )

            session.add(run)
            session.commit()
            session.refresh(run)

            # Queue items for the run
            queued_count = AnalysisRunRepo._queue_items_for_run(session, run.id, scope, params)

            # Update planned count and queued_count
            run.planned_count = queued_count
            run.queued_count = queued_count  # Fix: Set queued_count correctly
            run.status = "running" if queued_count > 0 else "completed"
            session.commit()
            session.refresh(run)

            logger.info(f"Created run {run.id} with {queued_count} items")

            # Convert to domain model before returning
            return AnalysisRunRepo._convert_to_domain_model(run, scope, params)

    @staticmethod
    def _queue_items_for_run(session: Session, run_id: int, scope: RunScope, params: RunParams) -> int:
        """Queue items for analysis run"""
        # Use params.limit if scope.limit is not set
        if scope.limit is None and params.limit:
            scope.limit = params.limit

        # Build query based on scope (include analysis join for unanalyzed_only filter)
        query = AnalysisRunRepo._build_scope_query(scope, include_analysis_join=True)

        # Get item IDs to process (first column is id, second is published date)
        items_query = text(query)
        result = session.exec(items_query)
        item_ids = [row[0] for row in result]

        if not item_ids:
            return 0

        # Create run items
        for item_id in item_ids:
            run_item = AnalysisRunItem(
                run_id=run_id,
                item_id=item_id,
                state="queued"
            )
            session.add(run_item)

        session.commit()
        return len(item_ids)

    @staticmethod
    def _build_scope_query(scope: RunScope, include_analysis_join: bool = True) -> str:
        """
        Build SQL query based on scope configuration.

        Args:
            scope: Scope defining which items to select
            include_analysis_join: Whether to join with item_analysis table (needed for unanalyzed_only filter)

        Returns:
            str: Complete SQL query with SELECT, JOIN, WHERE, ORDER BY and LIMIT clauses

        Query Features:
            - Supports multiple scope types: items, feeds, categories, global
            - Time-based filtering with hours parameter
            - Feed status filtering (active, error, etc.)
            - Unanalyzed items filtering
            - Always orders by published date DESC
            - Respects scope.limit for result size

        Important:
            - Returns DISTINCT results to avoid duplicates
            - Returns (id, published) tuple for proper ordering
        """
        # When using DISTINCT with ORDER BY, the ORDER BY column must be in SELECT
        base_query = """
            SELECT DISTINCT i.id, i.published
            FROM items i
            LEFT JOIN feeds f ON i.feed_id = f.id
        """

        if include_analysis_join:
            base_query += " LEFT JOIN item_analysis ia ON i.id = ia.item_id"

        conditions = []

        # Add scope conditions
        if scope.type == "items" and scope.item_ids:
            conditions.append(f"i.id IN ({','.join(map(str, scope.item_ids))})")
        elif scope.type == "feeds" and scope.feed_ids:
            conditions.append(f"f.id IN ({','.join(map(str, scope.feed_ids))})")
        elif scope.type == "categories" and scope.category_ids:
            # Join with feed_categories
            base_query = base_query.replace(
                "LEFT JOIN feeds f",
                "LEFT JOIN feeds f LEFT JOIN feed_categories fc ON f.id = fc.feed_id"
            )
            conditions.append(f"fc.category_id IN ({','.join(map(str, scope.category_ids))})")

        # Add time range
        if scope.hours:
            conditions.append(f"i.published >= NOW() - INTERVAL '{scope.hours} hours'")

        # Add other filters
        if scope.unanalyzed_only and include_analysis_join:
            conditions.append("ia.item_id IS NULL")

        if scope.feed_status:
            conditions.append(f"f.status = '{scope.feed_status}'")

        # Combine conditions
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        # Add ordering and limit
        order_by = " ORDER BY i.published DESC"
        limit_clause = f" LIMIT {scope.limit}" if scope.limit else ""

        return base_query + where_clause + order_by + limit_clause

    @staticmethod
    def get_run_by_id(run_id: int) -> Optional[AnalysisRunDomain]:
        """Get a specific analysis run by ID"""
        with Session(engine) as session:
            run = session.get(AnalysisRunDB, run_id)
            if run:
                return AnalysisRunRepo._convert_to_domain_model(run)
            return None

    @staticmethod
    def list_runs(limit: int = 20, since: Optional[datetime] = None) -> List[AnalysisRunDomain]:
        """List analysis runs with optional date filter"""
        with Session(engine) as session:
            query = select(AnalysisRunDB)

            if since:
                query = query.where(AnalysisRunDB.created_at >= since)

            query = query.order_by(AnalysisRunDB.created_at.desc()).limit(limit)

            runs = session.exec(query).all()

            # Convert to domain models
            return [AnalysisRunRepo._convert_to_domain_model(run) for run in runs]

    @staticmethod
    def get_recent_runs(limit: int = 20, offset: int = 0) -> List[AnalysisRunDomain]:
        """Get recent analysis runs with pagination"""
        with Session(engine) as session:
            query = select(AnalysisRunDB).order_by(AnalysisRunDB.created_at.desc()).offset(offset).limit(limit)
            runs = session.exec(query).all()
            return [AnalysisRunRepo._convert_to_domain_model(run) for run in runs]

    @staticmethod
    def update_run_status(run_id: int, status: RunStatus, error: Optional[str] = None) -> bool:
        """Update the status of an analysis run"""
        with Session(engine) as session:
            run = session.get(AnalysisRunDB, run_id)
            if not run:
                return False

            run.status = status.value if hasattr(status, 'value') else status
            run.updated_at = datetime.utcnow()

            if status in ["completed", "failed", "cancelled"]:
                run.completed_at = datetime.utcnow()
            elif status == "running":
                run.started_at = datetime.utcnow()

            if error:
                run.error_message = error

            session.commit()
            return True

    @staticmethod
    def get_active_runs() -> List[AnalysisRunDomain]:
        """Get all active (non-completed) analysis runs"""
        with Session(engine) as session:
            query = select(AnalysisRunDB).where(
                AnalysisRunDB.status.in_(["pending", "running", "paused"])  # Fixed: removed invalid statuses
            ).order_by(AnalysisRunDB.created_at.desc())

            runs = session.exec(query).all()

            # Convert to domain models
            return [AnalysisRunRepo._convert_to_domain_model(run) for run in runs]

    @staticmethod
    def get_run(run_id: int) -> Optional[AnalysisRunDomain]:
        """Get a specific run with detailed information"""
        return AnalysisRunRepo.get_run_by_id(run_id)