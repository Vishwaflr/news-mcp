"""
Research Repository
Data access layer for research templates, runs, queries, and results
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlmodel import Session, select, and_, or_
from app.models.research import (
    ResearchTemplate,
    ResearchRun,
    ResearchQuery,
    ResearchResult,
    ResearchArticleLink
)


class ResearchTemplateRepo:
    """Repository for research templates"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, template: ResearchTemplate) -> ResearchTemplate:
        """Create a new research template"""
        self.session.add(template)
        self.session.commit()
        self.session.refresh(template)
        return template

    def get_by_id(self, template_id: int) -> Optional[ResearchTemplate]:
        """Get template by ID"""
        return self.session.get(ResearchTemplate, template_id)

    def get_all(self, active_only: bool = True) -> List[ResearchTemplate]:
        """Get all templates, optionally filtering by active status"""
        query = select(ResearchTemplate)
        if active_only:
            query = query.where(ResearchTemplate.active == True)
        return self.session.exec(query).all()

    def update(self, template: ResearchTemplate) -> ResearchTemplate:
        """Update existing template"""
        template.updated_at = datetime.utcnow()
        self.session.add(template)
        self.session.commit()
        self.session.refresh(template)
        return template

    def delete(self, template_id: int) -> bool:
        """Delete template by ID"""
        template = self.get_by_id(template_id)
        if template:
            self.session.delete(template)
            self.session.commit()
            return True
        return False

    def deactivate(self, template_id: int) -> Optional[ResearchTemplate]:
        """Soft delete: set active=False"""
        template = self.get_by_id(template_id)
        if template:
            template.active = False
            return self.update(template)
        return None


class ResearchRunRepo:
    """Repository for research runs"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, run: ResearchRun) -> ResearchRun:
        """Create a new research run"""
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def get_by_id(self, run_id: int) -> Optional[ResearchRun]:
        """Get run by ID with all relationships loaded"""
        return self.session.get(ResearchRun, run_id)

    def get_pending(self, limit: int = 10) -> List[ResearchRun]:
        """Get pending runs (status='pending')"""
        query = select(ResearchRun).where(
            ResearchRun.status == 'pending'
        ).order_by(ResearchRun.started_at.asc()).limit(limit)
        return self.session.exec(query).all()

    def get_recent(self, limit: int = 20, since_hours: int = 24) -> List[ResearchRun]:
        """Get recent runs"""
        since = datetime.utcnow() - timedelta(hours=since_hours)
        query = select(ResearchRun).where(
            ResearchRun.started_at >= since
        ).order_by(ResearchRun.started_at.desc()).limit(limit)
        return self.session.exec(query).all()

    def update_status(self, run_id: int, status: str, error_message: Optional[str] = None) -> Optional[ResearchRun]:
        """Update run status"""
        run = self.get_by_id(run_id)
        if run:
            run.status = status
            if error_message:
                run.error_message = error_message
            if status == 'completed':
                run.completed_at = datetime.utcnow()
            self.session.add(run)
            self.session.commit()
            self.session.refresh(run)
        return run

    def update_metrics(self, run_id: int, articles_count: int = None,
                      queries_generated: int = None, queries_executed: int = None) -> Optional[ResearchRun]:
        """Update run metrics"""
        run = self.get_by_id(run_id)
        if run:
            if articles_count is not None:
                run.articles_count = articles_count
            if queries_generated is not None:
                run.queries_generated = queries_generated
            if queries_executed is not None:
                run.queries_executed = queries_executed
            self.session.add(run)
            self.session.commit()
            self.session.refresh(run)
        return run

    def link_articles(self, run_id: int, item_ids: List[int], relevance_scores: Optional[List[float]] = None) -> int:
        """Link articles to research run"""
        links = []
        for idx, item_id in enumerate(item_ids):
            relevance = relevance_scores[idx] if relevance_scores and idx < len(relevance_scores) else None
            link = ResearchArticleLink(
                research_run_id=run_id,
                item_id=item_id,
                relevance_score=relevance
            )
            links.append(link)

        self.session.add_all(links)
        self.session.commit()
        return len(links)


class ResearchQueryRepo:
    """Repository for research queries"""

    def __init__(self, session: Session):
        self.session = session

    def create_batch(self, queries: List[ResearchQuery]) -> List[ResearchQuery]:
        """Create multiple queries in batch"""
        self.session.add_all(queries)
        self.session.commit()
        for query in queries:
            self.session.refresh(query)
        return queries

    def get_by_run(self, run_id: int) -> List[ResearchQuery]:
        """Get all queries for a run"""
        query = select(ResearchQuery).where(
            ResearchQuery.run_id == run_id
        ).order_by(ResearchQuery.created_at.asc())
        return self.session.exec(query).all()

    def get_pending(self, run_id: Optional[int] = None, limit: int = 10) -> List[ResearchQuery]:
        """Get pending queries (not yet executed with Perplexity)"""
        query = select(ResearchQuery).where(
            ResearchQuery.perplexity_executed == False
        )
        if run_id:
            query = query.where(ResearchQuery.run_id == run_id)
        query = query.order_by(ResearchQuery.created_at.asc()).limit(limit)
        return self.session.exec(query).all()

    def mark_executed(self, query_id: int, response: Dict[str, Any], sources: List[Dict[str, Any]]) -> Optional[ResearchQuery]:
        """Mark query as executed and store Perplexity response"""
        query_obj = self.session.get(ResearchQuery, query_id)
        if query_obj:
            query_obj.perplexity_executed = True
            query_obj.perplexity_response = response
            query_obj.sources = sources
            query_obj.executed_at = datetime.utcnow()
            self.session.add(query_obj)
            self.session.commit()
            self.session.refresh(query_obj)
        return query_obj


class ResearchResultRepo:
    """Repository for research results"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, result: ResearchResult) -> ResearchResult:
        """Create a new research result"""
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        return result

    def create_batch(self, results: List[ResearchResult]) -> List[ResearchResult]:
        """Create multiple results in batch"""
        self.session.add_all(results)
        self.session.commit()
        for result in results:
            self.session.refresh(result)
        return results

    def get_by_run(self, run_id: int) -> List[ResearchResult]:
        """Get all results for a run"""
        query = select(ResearchResult).where(
            ResearchResult.run_id == run_id
        ).order_by(ResearchResult.created_at.asc())
        return self.session.exec(query).all()

    def get_by_type(self, run_id: int, result_type: str) -> List[ResearchResult]:
        """Get results by type for a specific run"""
        query = select(ResearchResult).where(
            and_(
                ResearchResult.run_id == run_id,
                ResearchResult.result_type == result_type
            )
        )
        return self.session.exec(query).all()
