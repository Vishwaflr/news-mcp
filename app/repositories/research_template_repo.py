"""
Research Template Repository
CRUD operations for research templates
"""
from typing import List, Optional
from datetime import datetime
from sqlmodel import Session, select
from app.database import engine
from app.models.research import ResearchTemplate
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ResearchTemplateRepo:
    """Repository for research template operations"""

    @staticmethod
    def create(template: ResearchTemplate) -> ResearchTemplate:
        """Create a new research template"""
        with Session(engine) as session:
            template.created_at = datetime.utcnow()
            template.updated_at = datetime.utcnow()
            session.add(template)
            session.commit()
            session.refresh(template)
            logger.info(f"Created research template: {template.name} (ID: {template.id})")
            return template

    @staticmethod
    def get_by_id(template_id: int) -> Optional[ResearchTemplate]:
        """Get template by ID"""
        with Session(engine) as session:
            return session.get(ResearchTemplate, template_id)

    @staticmethod
    def get_by_name(name: str) -> Optional[ResearchTemplate]:
        """Get template by name"""
        with Session(engine) as session:
            statement = select(ResearchTemplate).where(ResearchTemplate.name == name)
            return session.exec(statement).first()

    @staticmethod
    def list_all(
        active_only: bool = False,
        scheduled_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[ResearchTemplate]:
        """List all templates with optional filters"""
        with Session(engine) as session:
            statement = select(ResearchTemplate)

            if active_only:
                statement = statement.where(ResearchTemplate.is_active == True)

            if scheduled_only:
                statement = statement.where(ResearchTemplate.schedule_enabled == True)

            statement = statement.offset(offset).limit(limit).order_by(ResearchTemplate.created_at.desc())

            return list(session.exec(statement).all())

    @staticmethod
    def update(template_id: int, **updates) -> Optional[ResearchTemplate]:
        """Update a template"""
        with Session(engine) as session:
            template = session.get(ResearchTemplate, template_id)
            if not template:
                return None

            for key, value in updates.items():
                if hasattr(template, key):
                    setattr(template, key, value)

            template.updated_at = datetime.utcnow()
            session.add(template)
            session.commit()
            session.refresh(template)
            logger.info(f"Updated research template ID {template_id}")
            return template

    @staticmethod
    def delete(template_id: int) -> bool:
        """Delete a template"""
        with Session(engine) as session:
            template = session.get(ResearchTemplate, template_id)
            if not template:
                return False

            session.delete(template)
            session.commit()
            logger.info(f"Deleted research template ID {template_id}")
            return True

    @staticmethod
    def get_scheduled_templates() -> List[ResearchTemplate]:
        """Get all active templates with scheduling enabled"""
        with Session(engine) as session:
            statement = select(ResearchTemplate).where(
                ResearchTemplate.is_active == True,
                ResearchTemplate.schedule_enabled == True,
                ResearchTemplate.cron_expression.isnot(None)
            )
            return list(session.exec(statement).all())

    @staticmethod
    def count(active_only: bool = False) -> int:
        """Count templates"""
        with Session(engine) as session:
            statement = select(ResearchTemplate)
            if active_only:
                statement = statement.where(ResearchTemplate.is_active == True)

            results = session.exec(statement).all()
            return len(results)
