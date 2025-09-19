from sqlmodel import Session, select, text
from app.database import engine
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class ItemsRepo:
    @staticmethod
    def query_with_analysis(
        impact_min: Optional[float] = None,
        sentiment: Optional[str] = None,
        urgency_min: Optional[float] = None,
        limit: int = 50
    ) -> List[dict]:
        """Query items with analysis data using filters"""
        with Session(engine) as session:
            try:
                clauses = []
                params = {}

                if impact_min is not None:
                    clauses.append("(a.impact_json->>'overall')::numeric >= :impact_min")
                    params["impact_min"] = impact_min

                if sentiment:
                    clauses.append("a.sentiment_json->'overall'->>'label' = :sentiment")
                    params["sentiment"] = sentiment

                if urgency_min is not None:
                    clauses.append("(a.sentiment_json->>'urgency')::numeric >= :urgency_min")
                    params["urgency_min"] = urgency_min

                where_clause = "WHERE a.item_id IS NOT NULL"
                if clauses:
                    where_clause += " AND " + " AND ".join(clauses)

                params["limit"] = limit

                sql = f"""
                SELECT
                    i.id, i.title, i.description, i.content, i.link,
                    i.author, i.published, i.created_at,
                    a.sentiment_json, a.impact_json, a.model_tag,
                    a.updated_at AS analysis_updated_at
                FROM items i
                JOIN item_analysis a ON a.item_id = i.id
                {where_clause}
                ORDER BY
                    COALESCE((a.impact_json->>'overall')::numeric, 0) DESC,
                    i.created_at DESC
                LIMIT :limit
                """

                results = session.execute(text(sql), params).fetchall()

                return [
                    {
                        "id": row[0],
                        "title": row[1],
                        "description": row[2],
                        "content": row[3],
                        "link": row[4],
                        "author": row[5],
                        "published": row[6],
                        "created_at": row[7],
                        "sentiment_json": row[8],
                        "impact_json": row[9],
                        "model_tag": row[10],
                        "analysis_updated_at": row[11]
                    }
                    for row in results
                ]

            except Exception as e:
                logger.error(f"Failed to query items with analysis: {e}")
                return []

    @staticmethod
    def get_by_id(item_id: int) -> dict | None:
        """Get a single item by ID"""
        with Session(engine) as session:
            try:
                result = session.execute(
                    text("""
                    SELECT id, title, description, content, link, author, published, created_at
                    FROM items
                    WHERE id = :item_id
                    """),
                    {"item_id": item_id}
                ).first()

                if result:
                    return {
                        "id": result[0],
                        "title": result[1],
                        "description": result[2],
                        "content": result[3],
                        "link": result[4],
                        "author": result[5],
                        "published": result[6],
                        "created_at": result[7]
                    }
                return None

            except Exception as e:
                logger.error(f"Failed to get item {item_id}: {e}")
                return None

    @staticmethod
    def get_recent_items(limit: int = 100) -> List[dict]:
        """Get recent items regardless of analysis status"""
        with Session(engine) as session:
            try:
                results = session.execute(
                    text("""
                    SELECT id, title, description, content, link, author, published, created_at
                    FROM items
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """),
                    {"limit": limit}
                ).fetchall()

                return [
                    {
                        "id": row[0],
                        "title": row[1],
                        "description": row[2],
                        "content": row[3],
                        "link": row[4],
                        "author": row[5],
                        "published": row[6],
                        "created_at": row[7]
                    }
                    for row in results
                ]

            except Exception as e:
                logger.error(f"Failed to get recent items: {e}")
                return []