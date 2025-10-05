"""
Research Run Repository
CRUD operations for research runs (execution tracking)
"""
from typing import List, Optional
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.database import engine
from app.models.research import ResearchRun
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ResearchRunRepo:
    """Repository for research run operations"""

    @staticmethod
    def create(run: ResearchRun) -> ResearchRun:
        """Create a new research run"""
        with Session(engine) as session:
            run.created_at = datetime.utcnow()
            session.add(run)
            session.commit()
            session.refresh(run)
            logger.info(f"Created research run ID {run.id} (template: {run.template_id}, status: {run.status})")
            return run

    @staticmethod
    def get_by_id(run_id: int) -> Optional[ResearchRun]:
        """Get run by ID"""
        with Session(engine) as session:
            return session.get(ResearchRun, run_id)

    @staticmethod
    def list_all(
        template_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ResearchRun]:
        """List all runs with optional filters"""
        with Session(engine) as session:
            statement = select(ResearchRun)

            if template_id:
                statement = statement.where(ResearchRun.template_id == template_id)

            if status:
                statement = statement.where(ResearchRun.status == status)

            statement = statement.offset(offset).limit(limit).order_by(ResearchRun.created_at.desc())

            return list(session.exec(statement).all())

    @staticmethod
    def get_pending_runs(limit: int = 10) -> List[ResearchRun]:
        """Get pending runs ready for execution"""
        with Session(engine) as session:
            statement = select(ResearchRun).where(
                ResearchRun.status == "pending"
            ).limit(limit).order_by(ResearchRun.created_at.asc())

            return list(session.exec(statement).all())

    @staticmethod
    def get_active_runs() -> List[ResearchRun]:
        """Get currently running executions"""
        with Session(engine) as session:
            statement = select(ResearchRun).where(
                ResearchRun.status == "running"
            )
            return list(session.exec(statement).all())

    @staticmethod
    def update_status(
        run_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[ResearchRun]:
        """Update run status"""
        with Session(engine) as session:
            run = session.get(ResearchRun, run_id)
            if not run:
                return None

            run.status = status

            if status == "running" and not run.started_at:
                run.started_at = datetime.utcnow()

            if status in ("completed", "failed"):
                run.completed_at = datetime.utcnow()
                if run.started_at:
                    duration = (run.completed_at - run.started_at).total_seconds()
                    run.duration_seconds = int(duration)

            if error_message:
                run.error_message = error_message

            session.add(run)
            session.commit()
            session.refresh(run)
            logger.info(f"Updated research run ID {run_id} status to {status}")
            return run

    @staticmethod
    def update_results(
        run_id: int,
        result_content: str,
        result_metadata: dict,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[float] = None,
        perplexity_cost_usd: Optional[float] = None,
        llm_cost_usd: Optional[float] = None
    ) -> Optional[ResearchRun]:
        """Update run results and costs"""
        with Session(engine) as session:
            run = session.get(ResearchRun, run_id)
            if not run:
                return None

            run.result_content = result_content
            run.result_metadata = result_metadata
            run.tokens_used = tokens_used
            run.cost_usd = cost_usd
            run.perplexity_cost_usd = perplexity_cost_usd
            run.llm_cost_usd = llm_cost_usd

            session.add(run)
            session.commit()
            session.refresh(run)
            logger.info(f"Updated research run ID {run_id} results (tokens: {tokens_used}, cost: ${cost_usd})")
            return run

    @staticmethod
    def get_recent_runs(hours: int = 24, limit: int = 100) -> List[ResearchRun]:
        """Get runs from the last N hours"""
        with Session(engine) as session:
            since = datetime.utcnow() - timedelta(hours=hours)
            statement = select(ResearchRun).where(
                ResearchRun.created_at >= since
            ).limit(limit).order_by(ResearchRun.created_at.desc())

            return list(session.exec(statement).all())

    @staticmethod
    def get_cost_summary(hours: int = 24) -> dict:
        """Get cost summary for recent runs"""
        runs = ResearchRunRepo.get_recent_runs(hours=hours)

        total_cost = sum(run.cost_usd or 0 for run in runs)
        perplexity_cost = sum(run.perplexity_cost_usd or 0 for run in runs)
        llm_cost = sum(run.llm_cost_usd or 0 for run in runs)
        total_tokens = sum(run.tokens_used or 0 for run in runs)

        return {
            "total_runs": len(runs),
            "completed_runs": len([r for r in runs if r.status == "completed"]),
            "failed_runs": len([r for r in runs if r.status == "failed"]),
            "total_cost_usd": round(total_cost, 6),
            "perplexity_cost_usd": round(perplexity_cost, 6),
            "llm_cost_usd": round(llm_cost, 6),
            "total_tokens": total_tokens,
            "timeframe_hours": hours
        }

    @staticmethod
    def delete(run_id: int) -> bool:
        """Delete a run"""
        with Session(engine) as session:
            run = session.get(ResearchRun, run_id)
            if not run:
                return False

            session.delete(run)
            session.commit()
            logger.info(f"Deleted research run ID {run_id}")
            return True
