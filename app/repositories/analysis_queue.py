from sqlmodel import Session, text
from app.database import engine
from app.domain.analysis.control import AnalysisRun, RunItem, RunStatus, ItemState
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class AnalysisQueueRepo:
    """Repository for Analysis Queue operations with SKIP LOCKED support"""

    @staticmethod
    def get_pending_runs(limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending or running analysis runs"""
        with Session(engine) as session:
            try:
                results = session.execute(text("""
                    SELECT id, scope_json, params_json, status, created_at, updated_at
                    FROM analysis_runs
                    WHERE status IN ('pending', 'running')
                    ORDER BY created_at ASC
                    LIMIT :limit
                """), {"limit": limit}).fetchall()

                runs = []
                for row in results:
                    runs.append({
                        "id": row[0],
                        "scope": json.loads(row[1]) if isinstance(row[1], str) else row[1],
                        "params": json.loads(row[2]) if isinstance(row[2], str) else row[2],
                        "status": row[3],
                        "created_at": row[4],
                        "updated_at": row[5]
                    })
                return runs

            except Exception as e:
                logger.error(f"Failed to get pending runs: {e}")
                return []

    @staticmethod
    def claim_items_for_processing(run_id: int, chunk_size: int = 10) -> List[Dict[str, Any]]:
        """Claim queued items for processing using FOR UPDATE SKIP LOCKED"""
        with Session(engine) as session:
            try:
                # Claim items atomically
                results = session.execute(text("""
                    UPDATE analysis_run_items
                    SET state = 'processing', started_at = NOW()
                    WHERE id IN (
                        SELECT id FROM analysis_run_items
                        WHERE run_id = :run_id AND state = 'queued'
                        ORDER BY created_at ASC
                        LIMIT :chunk_size
                        FOR UPDATE SKIP LOCKED
                    )
                    RETURNING id, item_id, created_at
                """), {"run_id": run_id, "chunk_size": chunk_size}).fetchall()

                session.commit()

                claimed_items = []
                for row in results:
                    claimed_items.append({
                        "queue_id": row[0],
                        "item_id": row[1],
                        "created_at": row[2]
                    })

                logger.debug(f"Claimed {len(claimed_items)} items for run {run_id}")
                return claimed_items

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to claim items for run {run_id}: {e}")
                return []

    @staticmethod
    def get_item_content(item_id: int) -> Optional[Dict[str, Any]]:
        """Get item content for analysis (includes feed_id for scraping)"""
        with Session(engine) as session:
            try:
                result = session.execute(text("""
                    SELECT id, title, description, content, link, created_at, feed_id
                    FROM items
                    WHERE id = :item_id
                """), {"item_id": item_id}).first()

                if result:
                    return {
                        "id": result[0],
                        "title": result[1],
                        "description": result[2],
                        "content": result[3],
                        "link": result[4],
                        "created_at": result[5],
                        "feed_id": result[6]  # NEW: For scraping integration
                    }
                return None

            except Exception as e:
                logger.error(f"Failed to get item content for {item_id}: {e}")
                return None

    @staticmethod
    def update_item_state(queue_id: int, state: ItemState, error_message: Optional[str] = None,
                         tokens_used: Optional[int] = None, cost_usd: Optional[float] = None) -> bool:
        """Update item processing state"""
        with Session(engine) as session:
            try:
                now = datetime.utcnow()
                params = {
                    "queue_id": queue_id,
                    "state": state,
                    "completed_at": now if state in ["completed", "failed", "skipped"] else None,
                    "error_message": error_message,
                    "tokens_used": tokens_used,
                    "cost_usd": cost_usd
                }

                # Build dynamic SQL
                set_clauses = ["state = :state"]
                if state in ["completed", "failed", "skipped"]:
                    set_clauses.append("completed_at = :completed_at")
                if error_message:
                    set_clauses.append("error_message = :error_message")
                if tokens_used is not None:
                    set_clauses.append("tokens_used = :tokens_used")
                if cost_usd is not None:
                    set_clauses.append("cost_usd = :cost_usd")

                sql = f"""
                    UPDATE analysis_run_items
                    SET {', '.join(set_clauses)}
                    WHERE id = :queue_id
                """

                session.execute(text(sql), params)
                session.commit()
                return True

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to update item state for queue_id {queue_id}: {e}")
                return False

    @staticmethod
    def update_run_status(run_id: int, status: RunStatus, error: Optional[str] = None) -> bool:
        """Update run status"""
        with Session(engine) as session:
            try:
                now = datetime.utcnow()
                params = {
                    "run_id": run_id,
                    "status": status,
                    "updated_at": now
                }

                set_clauses = ["status = :status", "updated_at = :updated_at"]

                if status == "running":
                    params["started_at"] = now
                    set_clauses.append("started_at = :started_at")
                elif status in ["completed", "failed", "cancelled"]:
                    params["completed_at"] = now
                    set_clauses.append("completed_at = :completed_at")

                if error:
                    params["last_error"] = error
                    set_clauses.append("last_error = :last_error")

                sql = f"UPDATE analysis_runs SET {', '.join(set_clauses)} WHERE id = :run_id"
                session.execute(text(sql), params)
                session.commit()
                return True

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to update run status for {run_id}: {e}")
                return False

    @staticmethod
    def get_run_metrics(run_id: int) -> Dict[str, Any]:
        """Get current run metrics"""
        with Session(engine) as session:
            try:
                result = session.execute(text("""
                    SELECT
                        COUNT(*) FILTER (WHERE state = 'queued') as queued_count,
                        COUNT(*) FILTER (WHERE state = 'processing') as processing_count,
                        COUNT(*) FILTER (WHERE state = 'completed') as completed_count,
                        COUNT(*) FILTER (WHERE state = 'failed') as failed_count,
                        COUNT(*) FILTER (WHERE state = 'skipped') as skipped_count,
                        COALESCE(SUM(cost_usd), 0) as actual_cost,
                        COALESCE(SUM(tokens_used), 0) as total_tokens
                    FROM analysis_run_items
                    WHERE run_id = :run_id
                """), {"run_id": run_id}).first()

                if result:
                    total_count = sum(result[:5])  # Sum of all state counts
                    processed_count = result[2] + result[3] + result[4]  # completed + failed + skipped

                    return {
                        "queued_count": result[0],
                        "processing_count": result[1],
                        "completed_count": result[2],
                        "failed_count": result[3],
                        "skipped_count": result[4],
                        "total_count": total_count,
                        "processed_count": processed_count,
                        "actual_cost_usd": float(result[5]),
                        "total_tokens": result[6] or 0,
                        "progress_percent": round((processed_count / max(total_count, 1)) * 100, 1),
                        "error_rate": round(result[3] / max(processed_count, 1), 4) if processed_count > 0 else 0.0
                    }

                return {"queued_count": 0, "processing_count": 0, "completed_count": 0,
                       "failed_count": 0, "skipped_count": 0, "total_count": 0,
                       "processed_count": 0, "actual_cost_usd": 0.0, "total_tokens": 0,
                       "progress_percent": 0.0, "error_rate": 0.0}

            except Exception as e:
                logger.error(f"Failed to get run metrics for {run_id}: {e}")
                return {}

    @staticmethod
    def reset_stale_processing_items(stale_seconds: int = 300) -> int:
        """Reset processing items that are older than stale_seconds back to queued"""
        with Session(engine) as session:
            try:
                cutoff_time = datetime.utcnow() - timedelta(seconds=stale_seconds)

                result = session.execute(text("""
                    UPDATE analysis_run_items
                    SET state = 'queued', started_at = NULL
                    WHERE state = 'processing' AND started_at < :cutoff_time
                """), {"cutoff_time": cutoff_time})

                affected_rows = result.rowcount
                session.commit()

                if affected_rows > 0:
                    logger.info(f"Reset {affected_rows} stale processing items to queued")

                return affected_rows

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to reset stale processing items: {e}")
                return 0

    @staticmethod
    def heartbeat_run(run_id: int) -> bool:
        """Update run heartbeat (updated_at)"""
        with Session(engine) as session:
            try:
                session.execute(text("""
                    UPDATE analysis_runs
                    SET updated_at = NOW()
                    WHERE id = :run_id
                """), {"run_id": run_id})
                session.commit()
                return True

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to heartbeat run {run_id}: {e}")
                return False