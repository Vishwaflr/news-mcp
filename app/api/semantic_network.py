"""
Semantic Network API Endpoints
Provides access to semantic tags (actors, themes, regions) and related articles
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from sqlmodel import Session, text
from app.database import engine
from pydantic import BaseModel

router = APIRouter(prefix="/api/semantic", tags=["semantic-network"])


# Response Models
class TagStats(BaseModel):
    """Statistics for a semantic tag"""
    tag: str
    count: int
    category_distribution: dict[str, int]


class ActorResponse(BaseModel):
    """Actor tag with statistics"""
    actor: str
    article_count: int
    categories: dict[str, int]


class ThemeResponse(BaseModel):
    """Theme tag with statistics"""
    theme: str
    article_count: int
    categories: dict[str, int]


class RegionResponse(BaseModel):
    """Region tag with statistics"""
    region: str
    article_count: int
    categories: dict[str, int]


class RelatedArticle(BaseModel):
    """Article related by semantic tags"""
    item_id: int
    title: str
    category: str
    actor: str
    theme: str
    region: str
    sentiment: str
    impact: float
    created_at: str


# Endpoints
@router.get("/actors", response_model=List[ActorResponse])
def get_all_actors(
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = None
):
    """
    Get all unique actors with article counts

    - **limit**: Maximum number of actors to return (default 50)
    - **category**: Filter by category (optional)
    """
    with Session(engine) as session:
        # Build query with optional category filter
        category_filter = ""
        if category:
            category_filter = f"AND a.sentiment_json::jsonb->>'category' = '{category}'"

        stmt = text(f"""
            WITH actor_split AS (
                SELECT
                    i.id as item_id,
                    TRIM(unnest(string_to_array(
                        a.sentiment_json::jsonb->'semantic_tags'->>'actor',
                        ','
                    ))) as actor,
                    a.sentiment_json::jsonb->>'category' as category
                FROM items i
                JOIN item_analysis a ON a.item_id = i.id
                WHERE a.sentiment_json::jsonb->'semantic_tags'->>'actor' IS NOT NULL
                    AND a.sentiment_json::jsonb->'semantic_tags'->>'actor' != 'Unknown'
                    {category_filter}
            )
            SELECT
                actor,
                COUNT(*) as article_count,
                jsonb_object_agg(category, cat_count) as categories
            FROM (
                SELECT
                    actor,
                    category,
                    COUNT(*) as cat_count
                FROM actor_split
                GROUP BY actor, category
            ) cat_counts
            GROUP BY actor
            ORDER BY article_count DESC
            LIMIT :limit
        """)

        results = session.execute(stmt, {"limit": limit}).fetchall()

        return [
            ActorResponse(
                actor=row[0],
                article_count=row[1],
                categories=row[2] or {}
            )
            for row in results
        ]


@router.get("/themes", response_model=List[ThemeResponse])
def get_all_themes(
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = None
):
    """
    Get all unique themes with article counts

    - **limit**: Maximum number of themes to return (default 50)
    - **category**: Filter by category (optional)
    """
    with Session(engine) as session:
        category_filter = ""
        if category:
            category_filter = f"AND a.sentiment_json::jsonb->>'category' = '{category}'"

        stmt = text(f"""
            SELECT
                theme,
                COUNT(*) as article_count,
                jsonb_object_agg(category, cat_count) as categories
            FROM (
                SELECT
                    a.sentiment_json::jsonb->'semantic_tags'->>'theme' as theme,
                    a.sentiment_json::jsonb->>'category' as category,
                    COUNT(*) as cat_count
                FROM items i
                JOIN item_analysis a ON a.item_id = i.id
                WHERE a.sentiment_json::jsonb->'semantic_tags'->>'theme' IS NOT NULL
                    AND a.sentiment_json::jsonb->'semantic_tags'->>'theme' != 'General'
                    {category_filter}
                GROUP BY theme, category
            ) cat_counts
            GROUP BY theme
            ORDER BY article_count DESC
            LIMIT :limit
        """)

        results = session.execute(stmt, {"limit": limit}).fetchall()

        return [
            ThemeResponse(
                theme=row[0],
                article_count=row[1],
                categories=row[2] or {}
            )
            for row in results
        ]


@router.get("/regions", response_model=List[RegionResponse])
def get_all_regions(
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = None
):
    """
    Get all unique regions with article counts

    - **limit**: Maximum number of regions to return (default 50)
    - **category**: Filter by category (optional)
    """
    with Session(engine) as session:
        category_filter = ""
        if category:
            category_filter = f"AND a.sentiment_json::jsonb->>'category' = '{category}'"

        stmt = text(f"""
            SELECT
                region,
                COUNT(*) as article_count,
                jsonb_object_agg(category, cat_count) as categories
            FROM (
                SELECT
                    a.sentiment_json::jsonb->'semantic_tags'->>'region' as region,
                    a.sentiment_json::jsonb->>'category' as category,
                    COUNT(*) as cat_count
                FROM items i
                JOIN item_analysis a ON a.item_id = i.id
                WHERE a.sentiment_json::jsonb->'semantic_tags'->>'region' IS NOT NULL
                    AND a.sentiment_json::jsonb->'semantic_tags'->>'region' != 'Global'
                    {category_filter}
                GROUP BY region, category
            ) cat_counts
            GROUP BY region
            ORDER BY article_count DESC
            LIMIT :limit
        """)

        results = session.execute(stmt, {"limit": limit}).fetchall()

        return [
            RegionResponse(
                region=row[0],
                article_count=row[1],
                categories=row[2] or {}
            )
            for row in results
        ]


@router.get("/articles/by-actor/{actor}", response_model=List[RelatedArticle])
def get_articles_by_actor(
    actor: str,
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get articles featuring a specific actor

    - **actor**: Actor name (exact match or partial)
    - **limit**: Maximum number of articles (default 20)
    """
    with Session(engine) as session:
        stmt = text("""
            SELECT
                i.id,
                i.title,
                a.sentiment_json::jsonb->>'category' as category,
                a.sentiment_json::jsonb->'semantic_tags'->>'actor' as actor,
                a.sentiment_json::jsonb->'semantic_tags'->>'theme' as theme,
                a.sentiment_json::jsonb->'semantic_tags'->>'region' as region,
                a.sentiment_json::jsonb->'overall'->>'label' as sentiment,
                (a.sentiment_json::jsonb->'impact'->>'overall')::float as impact,
                i.created_at::text
            FROM items i
            JOIN item_analysis a ON a.item_id = i.id
            WHERE a.sentiment_json::jsonb->'semantic_tags'->>'actor' ILIKE '%' || :actor || '%'
            ORDER BY i.created_at DESC
            LIMIT :limit
        """)

        results = session.execute(stmt, {"actor": actor, "limit": limit}).fetchall()

        if not results:
            raise HTTPException(status_code=404, detail=f"No articles found for actor: {actor}")

        return [
            RelatedArticle(
                item_id=row[0],
                title=row[1],
                category=row[2] or "panorama",
                actor=row[3] or "Unknown",
                theme=row[4] or "General",
                region=row[5] or "Global",
                sentiment=row[6] or "neutral",
                impact=row[7] or 0.0,
                created_at=row[8]
            )
            for row in results
        ]


@router.get("/articles/by-theme/{theme}", response_model=List[RelatedArticle])
def get_articles_by_theme(
    theme: str,
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get articles with a specific theme

    - **theme**: Theme name (exact match or partial)
    - **limit**: Maximum number of articles (default 20)
    """
    with Session(engine) as session:
        stmt = text("""
            SELECT
                i.id,
                i.title,
                a.sentiment_json::jsonb->>'category' as category,
                a.sentiment_json::jsonb->'semantic_tags'->>'actor' as actor,
                a.sentiment_json::jsonb->'semantic_tags'->>'theme' as theme,
                a.sentiment_json::jsonb->'semantic_tags'->>'region' as region,
                a.sentiment_json::jsonb->'overall'->>'label' as sentiment,
                (a.sentiment_json::jsonb->'impact'->>'overall')::float as impact,
                i.created_at::text
            FROM items i
            JOIN item_analysis a ON a.item_id = i.id
            WHERE a.sentiment_json::jsonb->'semantic_tags'->>'theme' ILIKE '%' || :theme || '%'
            ORDER BY i.created_at DESC
            LIMIT :limit
        """)

        results = session.execute(stmt, {"theme": theme, "limit": limit}).fetchall()

        if not results:
            raise HTTPException(status_code=404, detail=f"No articles found for theme: {theme}")

        return [
            RelatedArticle(
                item_id=row[0],
                title=row[1],
                category=row[2] or "panorama",
                actor=row[3] or "Unknown",
                theme=row[4] or "General",
                region=row[5] or "Global",
                sentiment=row[6] or "neutral",
                impact=row[7] or 0.0,
                created_at=row[8]
            )
            for row in results
        ]


@router.get("/articles/by-region/{region}", response_model=List[RelatedArticle])
def get_articles_by_region(
    region: str,
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get articles from a specific region

    - **region**: Region name (exact match or partial)
    - **limit**: Maximum number of articles (default 20)
    """
    with Session(engine) as session:
        stmt = text("""
            SELECT
                i.id,
                i.title,
                a.sentiment_json::jsonb->>'category' as category,
                a.sentiment_json::jsonb->'semantic_tags'->>'actor' as actor,
                a.sentiment_json::jsonb->'semantic_tags'->>'theme' as theme,
                a.sentiment_json::jsonb->'semantic_tags'->>'region' as region,
                a.sentiment_json::jsonb->'overall'->>'label' as sentiment,
                (a.sentiment_json::jsonb->'impact'->>'overall')::float as impact,
                i.created_at::text
            FROM items i
            JOIN item_analysis a ON a.item_id = i.id
            WHERE a.sentiment_json::jsonb->'semantic_tags'->>'region' ILIKE '%' || :region || '%'
            ORDER BY i.created_at DESC
            LIMIT :limit
        """)

        results = session.execute(stmt, {"region": region, "limit": limit}).fetchall()

        if not results:
            raise HTTPException(status_code=404, detail=f"No articles found for region: {region}")

        return [
            RelatedArticle(
                item_id=row[0],
                title=row[1],
                category=row[2] or "panorama",
                actor=row[3] or "Unknown",
                theme=row[4] or "General",
                region=row[5] or "Global",
                sentiment=row[6] or "neutral",
                impact=row[7] or 0.0,
                created_at=row[8]
            )
            for row in results
        ]


@router.get("/network/{item_id}", response_model=List[RelatedArticle])
def get_related_articles(
    item_id: int,
    limit: int = Query(10, ge=1, le=50)
):
    """
    Get articles related to a specific item via semantic tags
    Finds articles sharing at least one semantic tag (actor, theme, or region)

    - **item_id**: Item ID
    - **limit**: Maximum number of related articles (default 10)
    """
    with Session(engine) as session:
        # First get the tags for the target item
        target_stmt = text("""
            SELECT
                a.sentiment_json::jsonb->'semantic_tags'->>'actor' as actor,
                a.sentiment_json::jsonb->'semantic_tags'->>'theme' as theme,
                a.sentiment_json::jsonb->'semantic_tags'->>'region' as region
            FROM item_analysis a
            WHERE a.item_id = :item_id
        """)

        target = session.execute(target_stmt, {"item_id": item_id}).first()

        if not target:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found or not analyzed")

        target_actor, target_theme, target_region = target

        # Find related articles (sharing at least one tag)
        stmt = text("""
            SELECT
                i.id,
                i.title,
                a.sentiment_json::jsonb->>'category' as category,
                a.sentiment_json::jsonb->'semantic_tags'->>'actor' as actor,
                a.sentiment_json::jsonb->'semantic_tags'->>'theme' as theme,
                a.sentiment_json::jsonb->'semantic_tags'->>'region' as region,
                a.sentiment_json::jsonb->'overall'->>'label' as sentiment,
                (a.sentiment_json::jsonb->'impact'->>'overall')::float as impact,
                i.created_at::text,
                -- Score based on tag matches (3 = all match, 1 = one match)
                (
                    CASE WHEN a.sentiment_json::jsonb->'semantic_tags'->>'actor' ILIKE '%' || :actor || '%' THEN 1 ELSE 0 END +
                    CASE WHEN a.sentiment_json::jsonb->'semantic_tags'->>'theme' = :theme THEN 1 ELSE 0 END +
                    CASE WHEN a.sentiment_json::jsonb->'semantic_tags'->>'region' = :region THEN 1 ELSE 0 END
                ) as match_score
            FROM items i
            JOIN item_analysis a ON a.item_id = i.id
            WHERE i.id != :item_id
                AND (
                    a.sentiment_json::jsonb->'semantic_tags'->>'actor' ILIKE '%' || :actor || '%'
                    OR a.sentiment_json::jsonb->'semantic_tags'->>'theme' = :theme
                    OR a.sentiment_json::jsonb->'semantic_tags'->>'region' = :region
                )
            ORDER BY match_score DESC, i.created_at DESC
            LIMIT :limit
        """)

        results = session.execute(stmt, {
            "item_id": item_id,
            "actor": target_actor,
            "theme": target_theme,
            "region": target_region,
            "limit": limit
        }).fetchall()

        return [
            RelatedArticle(
                item_id=row[0],
                title=row[1],
                category=row[2] or "panorama",
                actor=row[3] or "Unknown",
                theme=row[4] or "General",
                region=row[5] or "Global",
                sentiment=row[6] or "neutral",
                impact=row[7] or 0.0,
                created_at=row[8]
            )
            for row in results
        ]
