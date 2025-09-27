"""
Analysis Selection API
Central endpoint for article selection with caching
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlmodel import Session, text
from datetime import datetime

from app.database import get_session
from app.services.selection_cache import get_selection_cache, SelectionMetadata
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class SelectionRequest(BaseModel):
    """Request model for article selection"""
    mode: str = Field(..., description="Selection mode: latest, oldest, random, unanalyzed, time_range")
    count: int = Field(..., ge=1, le=1000, description="Number of articles to select")
    feed_id: Optional[int] = Field(None, description="Optional feed filter")
    hours: Optional[int] = Field(None, description="Hours to look back (for time_range mode)")
    date_from: Optional[str] = Field(None, description="Start date filter (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="End date filter (YYYY-MM-DD)")
    unanalyzed_only: bool = Field(False, description="Select only unanalyzed articles")


class SelectionResponse(BaseModel):
    """Response model for article selection"""
    selection_id: str
    total_items: int
    already_analyzed: int
    to_analyze: int
    cached: bool
    mode: str
    count: int


@router.post("/selection", response_model=SelectionResponse)
async def create_selection(
    request: SelectionRequest,
    db: Session = Depends(get_session)
):
    """
    Create article selection with caching

    This is the central endpoint that:
    1. Queries DB for articles matching criteria
    2. Caches result with deterministic key
    3. Returns selection_id for Preview & Articles
    """
    try:
        cache = get_selection_cache()

        # Generate cache key from request params
        cache_params = request.dict()
        cache_key = cache.generate_key(cache_params)

        # Check cache first
        cached_selection = cache.get(cache_key)
        if cached_selection:
            metadata = cached_selection['metadata']
            articles = cached_selection['articles']

            logger.info(f"Using cached selection {cache_key}: {len(articles)} articles")

            # Calculate analyzed count
            analyzed_count = sum(1 for a in articles if a.get('has_analysis'))

            return SelectionResponse(
                selection_id=cache_key,
                total_items=len(articles),
                already_analyzed=analyzed_count,
                to_analyze=len(articles) - analyzed_count,
                cached=True,
                mode=metadata['mode'],
                count=metadata['count']
            )

        # Cache miss - query database
        logger.info(f"Cache miss for {cache_key}, querying database...")

        # Build WHERE clause
        conditions = []
        params = {'count': request.count}

        if request.feed_id:
            conditions.append("i.feed_id = :feed_id")
            params['feed_id'] = request.feed_id

        if request.date_from:
            conditions.append("i.published >= :date_from")
            params['date_from'] = request.date_from

        if request.date_to:
            conditions.append("i.published <= :date_to")
            params['date_to'] = request.date_to

        if request.mode == 'time_range' and request.hours:
            conditions.append(f"i.published >= NOW() - INTERVAL '{request.hours} hours'")

        if request.mode == 'unanalyzed':
            conditions.append("i.id NOT IN (SELECT DISTINCT item_id FROM item_analysis WHERE item_id IS NOT NULL)")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Order clause
        order_clause = {
            "latest": "i.published DESC NULLS LAST, i.created_at DESC",
            "oldest": "i.published ASC NULLS LAST, i.created_at ASC",
            "random": "RANDOM()",
            "unanalyzed": "i.published DESC NULLS LAST, i.created_at DESC",
            "time_range": "i.published DESC NULLS LAST, i.created_at DESC"
        }.get(request.mode, "i.published DESC NULLS LAST, i.created_at DESC")

        # Query articles
        query = f"""
        SELECT
            i.id,
            i.title,
            i.link,
            i.published,
            i.feed_id,
            i.author,
            i.description,
            f.title as feed_title,
            ia.sentiment_json->>'overall' as sentiment_label,
            ia.item_id as has_analysis
        FROM items i
        LEFT JOIN feeds f ON f.id = i.feed_id
        LEFT JOIN item_analysis ia ON ia.item_id = i.id
        WHERE {where_clause}
        ORDER BY {order_clause}
        LIMIT :count
        """

        result = db.execute(text(query), params)
        rows = result.fetchall()

        # Convert to dict list
        articles = []
        analyzed_count = 0

        for row in rows:
            article = {
                'id': row[0],
                'title': row[1],
                'link': row[2],
                'published': row[3].isoformat() if row[3] else None,
                'feed_id': row[4],
                'author': row[5],
                'description': row[6],
                'feed_title': row[7],
                'sentiment_label': row[8],
                'has_analysis': row[9] is not None
            }
            articles.append(article)
            if article['has_analysis']:
                analyzed_count += 1

        logger.info(f"Selected {len(articles)} articles, {analyzed_count} already analyzed")

        # Store in cache
        metadata = SelectionMetadata(
            mode=request.mode,
            count=request.count,
            feed_id=request.feed_id,
            hours=request.hours,
            date_from=request.date_from,
            date_to=request.date_to,
            unanalyzed_only=request.unanalyzed_only,
            total_items=len(articles),
            created_at=datetime.utcnow().isoformat()
        )

        cache.set(cache_key, articles, metadata)

        return SelectionResponse(
            selection_id=cache_key,
            total_items=len(articles),
            already_analyzed=analyzed_count,
            to_analyze=len(articles) - analyzed_count,
            cached=False,
            mode=request.mode,
            count=request.count
        )

    except Exception as e:
        logger.error(f"Error creating selection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/selection/{selection_id}")
async def get_selection_info(selection_id: str):
    """Get info about a cached selection"""
    cache = get_selection_cache()
    cached = cache.get(selection_id)

    if not cached:
        raise HTTPException(status_code=404, detail="Selection not found or expired")

    metadata = cached['metadata']
    articles = cached['articles']
    analyzed_count = sum(1 for a in articles if a.get('has_analysis'))

    return {
        'selection_id': selection_id,
        'total_items': len(articles),
        'already_analyzed': analyzed_count,
        'to_analyze': len(articles) - analyzed_count,
        'mode': metadata['mode'],
        'count': metadata['count'],
        'created_at': metadata['created_at']
    }


@router.get("/selection/{selection_id}/articles")
async def get_selection_articles(selection_id: str):
    """Get all articles from a cached selection for client-side processing"""
    cache = get_selection_cache()
    cached = cache.get(selection_id)

    if not cached:
        raise HTTPException(status_code=404, detail="Selection not found or expired")

    metadata = cached['metadata']
    articles = cached['articles']

    return {
        'selection_id': selection_id,
        'articles': articles,
        'metadata': {
            'mode': metadata['mode'],
            'count': metadata['count'],
            'created_at': metadata['created_at']
        }
    }