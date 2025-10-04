"""
Research API Endpoints
Endpoints for LLM-driven Perplexity research pipeline
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from app.database import get_session
from app.services.research.article_filter import ArticleFilterService
from app.services.research.llm_query_generator import LLMQueryGeneratorService
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/research", tags=["research"])


class GenerateQueriesRequest(BaseModel):
    filter_config: Dict[str, Any]
    prompt: str
    model: str = None


@router.post("/filter/test")
async def test_article_filter(
    filter_config: Dict[str, Any],
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Test article filter with given configuration

    Returns preview with sample articles and total count
    """
    try:
        service = ArticleFilterService(session)

        # Validate config
        is_valid, error = service.validate_filter_config(filter_config)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error)

        # Get preview (first 10 articles)
        preview = service.get_filter_preview(filter_config, limit=10)

        return preview

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing article filter: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/filter/articles")
async def filter_articles(
    filter_config: Dict[str, Any],
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Get full list of articles matching filter criteria
    """
    try:
        service = ArticleFilterService(session)

        # Validate config
        is_valid, error = service.validate_filter_config(filter_config)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error)

        # Get articles
        articles = service.filter_by_criteria(filter_config)

        return {
            "ok": True,
            "count": len(articles),
            "articles": articles
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error filtering articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-queries")
async def generate_queries(
    request: GenerateQueriesRequest,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Generate research queries using LLM based on filtered articles

    Accepts filter configuration and user prompt, filters articles,
    then calls LLM to generate research questions.
    """
    try:
        # Validate and filter articles
        filter_service = ArticleFilterService(session)

        is_valid, error = filter_service.validate_filter_config(request.filter_config)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid filter config: {error}")

        articles = filter_service.filter_by_criteria(request.filter_config)

        if not articles:
            return {
                "ok": False,
                "error": "No articles found matching filter criteria",
                "generated_queries": None
            }

        logger.info(f"Generating queries for {len(articles)} filtered articles")

        # Generate queries with LLM
        llm_service = LLMQueryGeneratorService()
        result = llm_service.generate_queries(
            articles=articles,
            user_prompt=request.prompt,
            model=request.model
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))
