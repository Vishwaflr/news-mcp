from sqlmodel import Session, select, text
from app.database import engine
from app.domain.analysis.schema import AnalysisResult
import json
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class AnalysisRepo:
    @staticmethod
    def upsert(item_id: int, result: AnalysisResult):
        """Insert or update analysis data for an item"""
        with Session(engine) as session:
            try:
                # Build sentiment JSON including geopolitical data if present
                sentiment_data = result.sentiment.model_dump()
                if result.geopolitical:
                    sentiment_data["geopolitical"] = result.geopolitical.model_dump()

                # Use the PostgreSQL function for efficient upsert
                stmt = text("""
                    SELECT upsert_item_analysis(
                        :item_id,
                        :sentiment,
                        :impact,
                        :model_tag
                    )
                    """)
                session.execute(stmt, {
                    "item_id": item_id,
                    "sentiment": json.dumps(sentiment_data),
                    "impact": json.dumps(result.impact.model_dump()),
                    "model_tag": result.model_tag
                })
                session.commit()
                logger.debug(f"Upserted analysis for item {item_id}")
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to upsert analysis for item {item_id}: {e}")
                raise

    @staticmethod
    def get_by_item_id(item_id: int) -> dict | None:
        """Get analysis data for a specific item"""
        with Session(engine) as session:
            try:
                stmt = text("""
                    SELECT sentiment_json, impact_json, model_tag, updated_at
                    FROM item_analysis
                    WHERE item_id = :item_id
                    """)
                result = session.execute(stmt, {"item_id": item_id}).first()

                if result:
                    return {
                        "sentiment_json": result[0],
                        "impact_json": result[1],
                        "model_tag": result[2],
                        "updated_at": result[3]
                    }
                return None
            except Exception as e:
                logger.error(f"Failed to get analysis for item {item_id}: {e}")
                return None

    @staticmethod
    def get_items_without_analysis(limit: int = 200) -> list:
        """Get items that don't have analysis yet"""
        with Session(engine) as session:
            try:
                stmt = text("""
                    SELECT i.id, i.title, i.description, i.content
                    FROM items i
                    LEFT JOIN item_analysis a ON a.item_id = i.id
                    WHERE a.item_id IS NULL
                    ORDER BY i.created_at DESC
                    LIMIT :limit
                    """)
                results = session.execute(stmt, {"limit": limit}).fetchall()

                return [
                    {
                        "id": row[0],
                        "title": row[1],
                        "description": row[2],
                        "content": row[3]
                    }
                    for row in results
                ]
            except Exception as e:
                logger.error(f"Failed to get items without analysis: {e}")
                return []

    @staticmethod
    def count_pending_analysis() -> int:
        """Count items that need analysis"""
        with Session(engine) as session:
            try:
                stmt = text("""
                    SELECT COUNT(*)
                    FROM items i
                    LEFT JOIN item_analysis a ON a.item_id = i.id
                    WHERE a.item_id IS NULL
                    """)
                result = session.execute(stmt).first()
                return result[0] if result else 0
            except Exception as e:
                logger.error(f"Failed to count pending analysis: {e}")
                return 0

    @staticmethod
    def get_analysis_stats() -> dict:
        """Get analysis statistics"""
        with Session(engine) as session:
            try:
                # Get total items count
                total_items_stmt = text("SELECT COUNT(*) FROM items")
                total_items = session.execute(total_items_stmt).scalar() or 0

                # Get analysis stats
                stmt = text("""
                    SELECT
                        COUNT(*) as total_analyzed,
                        COUNT(CASE WHEN sentiment_json->'overall'->>'label' = 'positive' THEN 1 END) as positive,
                        COUNT(CASE WHEN sentiment_json->'overall'->>'label' = 'negative' THEN 1 END) as negative,
                        COUNT(CASE WHEN sentiment_json->'overall'->>'label' = 'neutral' THEN 1 END) as neutral,
                        AVG((impact_json->>'overall')::numeric) as avg_impact,
                        AVG((sentiment_json->>'urgency')::numeric) as avg_urgency
                    FROM item_analysis
                    """)
                stats = session.execute(stmt).first()

                if stats:
                    analyzed_items = stats[0] or 0
                    coverage = (analyzed_items / total_items * 100) if total_items > 0 else 0

                    return {
                        "total_items": total_items,
                        "analyzed_items": analyzed_items,
                        "analysis_coverage": coverage,
                        "total_analyzed": analyzed_items,
                        "sentiment_distribution": {
                            "positive": stats[1] or 0,
                            "negative": stats[2] or 0,
                            "neutral": stats[3] or 0
                        },
                        "avg_impact": float(stats[4]) if stats[4] else 0.52,
                        "avg_urgency": float(stats[5]) if stats[5] else 0.57
                    }

                # Return defaults if no analysis data
                return {
                    "total_items": total_items,
                    "analyzed_items": 0,
                    "analysis_coverage": 0,
                    "total_analyzed": 0,
                    "sentiment_distribution": {
                        "positive": 0,
                        "negative": 0,
                        "neutral": 0
                    },
                    "avg_impact": 0.52,
                    "avg_urgency": 0.57
                }
            except Exception as e:
                logger.error(f"Failed to get analysis stats: {e}")
                return {
                    "total_items": 0,
                    "analyzed_items": 0,
                    "analysis_coverage": 0,
                    "sentiment_distribution": {},
                    "avg_impact": 0.52,
                    "avg_urgency": 0.57
                }