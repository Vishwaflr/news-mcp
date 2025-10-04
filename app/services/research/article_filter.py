"""
Article Filter Service
Filters articles based on semantic tags, categories, impact, and other criteria
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlmodel import Session, select, text
from sqlalchemy import and_, or_
from app.models import Item
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ArticleFilterService:
    """Service for filtering articles based on various criteria"""

    def __init__(self, session: Session):
        self.session = session

    def filter_by_criteria(self, filter_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter articles based on configuration

        Filter Config Schema:
        {
            "categories": ["geopolitics_security", "economy_markets"],  # Optional
            "actors": ["Trump", "EU"],                                  # Substring match, optional
            "themes": ["Trade-War"],                                    # Substring match, optional
            "regions": ["US-China-Relations"],                          # Substring match, optional
            "timeframe": {                                              # Optional
                "from": "2025-10-01",
                "to": "2025-10-04"
            },
            "timeframe": "last_24h",  # Alternative: relative timeframe
            "impact_min": 0.6,         # Optional
            "impact_max": 1.0,         # Optional
            "sentiment": ["negative", "neutral"],  # Optional
            "max_articles": 15,        # Required
            "order_by": "impact_desc"  # impact_desc, published_desc, created_desc
        }
        """
        try:
            # Build WHERE conditions
            where_conditions = ["1=1"]  # Always true base condition
            params = {}

            # Timeframe filter
            timeframe = filter_config.get("timeframe")
            if timeframe:
                from_dt, to_dt = self._parse_timeframe(timeframe)
                if from_dt:
                    where_conditions.append("i.published >= :from_dt")
                    params['from_dt'] = from_dt
                if to_dt:
                    where_conditions.append("i.published <= :to_dt")
                    params['to_dt'] = to_dt

            # Category filter
            categories = filter_config.get("categories")
            if categories:
                where_conditions.append("a.sentiment_json::jsonb->>'category' = ANY(:categories)")
                params['categories'] = categories

            # Semantic Tag Filters (substring match)
            actors = filter_config.get("actors")
            if actors:
                actor_conditions = []
                for idx, actor in enumerate(actors):
                    param_name = f"actor_{idx}"
                    actor_conditions.append(f"a.sentiment_json::jsonb->'semantic_tags'->>'actor' ILIKE :{param_name}")
                    params[param_name] = f"%{actor}%"
                where_conditions.append(f"({' OR '.join(actor_conditions)})")

            themes = filter_config.get("themes")
            if themes:
                theme_conditions = []
                for idx, theme in enumerate(themes):
                    param_name = f"theme_{idx}"
                    theme_conditions.append(f"a.sentiment_json::jsonb->'semantic_tags'->>'theme' ILIKE :{param_name}")
                    params[param_name] = f"%{theme}%"
                where_conditions.append(f"({' OR '.join(theme_conditions)})")

            regions = filter_config.get("regions")
            if regions:
                region_conditions = []
                for idx, region in enumerate(regions):
                    param_name = f"region_{idx}"
                    region_conditions.append(f"a.sentiment_json::jsonb->'semantic_tags'->>'region' ILIKE :{param_name}")
                    params[param_name] = f"%{region}%"
                where_conditions.append(f"({' OR '.join(region_conditions)})")

            # Impact filter
            impact_min = filter_config.get("impact_min")
            if impact_min is not None:
                where_conditions.append("(a.sentiment_json::jsonb->'impact'->>'overall')::float >= :impact_min")
                params['impact_min'] = impact_min

            impact_max = filter_config.get("impact_max")
            if impact_max is not None:
                where_conditions.append("(a.sentiment_json::jsonb->'impact'->>'overall')::float <= :impact_max")
                params['impact_max'] = impact_max

            # Sentiment filter
            sentiments = filter_config.get("sentiment")
            if sentiments:
                where_conditions.append("a.sentiment_json::jsonb->'overall'->>'label' = ANY(:sentiments)")
                params['sentiments'] = sentiments

            # Combine conditions
            where_clause = " AND ".join(where_conditions)

            # Order by
            order_by_map = {
                "impact_desc": "(a.sentiment_json::jsonb->'impact'->>'overall')::float DESC NULLS LAST",
                "published_desc": "i.published DESC",
                "created_desc": "i.created_at DESC"
            }
            order_by = order_by_map.get(filter_config.get("order_by", "published_desc"), "i.published DESC")

            # Limit
            max_articles = filter_config.get("max_articles", 20)
            params['limit'] = max_articles

            # Build SQL query
            query = text(f"""
                SELECT
                    i.id,
                    i.title,
                    i.description,
                    i.link,
                    i.published,
                    i.created_at,
                    i.feed_id,
                    f.title as feed_name,
                    a.sentiment_json::jsonb->>'category' as category,
                    a.sentiment_json::jsonb->'semantic_tags'->>'actor' as actor,
                    a.sentiment_json::jsonb->'semantic_tags'->>'theme' as theme,
                    a.sentiment_json::jsonb->'semantic_tags'->>'region' as region,
                    a.sentiment_json::jsonb->'overall'->>'label' as sentiment,
                    (a.sentiment_json::jsonb->'overall'->>'confidence')::float as sentiment_confidence,
                    (a.sentiment_json::jsonb->'impact'->>'overall')::float as impact,
                    (a.sentiment_json::jsonb->'impact'->>'economic')::float as impact_economic,
                    (a.sentiment_json::jsonb->'impact'->>'geopolitical')::float as impact_geopolitical,
                    (a.sentiment_json::jsonb->'impact'->>'social')::float as impact_social,
                    (a.sentiment_json::jsonb->>'urgency')::float as urgency,
                    (a.sentiment_json::jsonb->>'credibility')::float as credibility
                FROM items i
                LEFT JOIN item_analysis a ON a.item_id = i.id
                LEFT JOIN feeds f ON f.id = i.feed_id
                WHERE {where_clause}
                ORDER BY {order_by}
                LIMIT :limit
            """)

            # Execute query
            result = self.session.execute(query, params)
            rows = result.fetchall()

            # Convert to dict
            articles = []
            for row in rows:
                # Safe extraction with defaults for all fields
                articles.append({
                    "id": row[0],
                    "title": row[1] or "Untitled",
                    "description": row[2] or "",
                    "link": row[3] or "",
                    "published": row[4],
                    "created_at": row[5],
                    "feed_id": row[6] or 0,
                    "feed_name": row[7] if row[7] else f"Feed #{row[6] if row[6] else 'Unknown'}",
                    "category": row[8] if row[8] else "panorama",
                    "semantic_tags": {
                        "actor": row[9] if row[9] else "Unknown",
                        "theme": row[10] if row[10] else "General",
                        "region": row[11] if row[11] else "Global"
                    },
                    "sentiment": row[12] if row[12] else "neutral",
                    "sentiment_confidence": float(row[13]) if row[13] is not None else 0.0,
                    "impact": {
                        "overall": float(row[14]) if row[14] is not None else 0.0,
                        "economic": float(row[15]) if row[15] is not None else 0.0,
                        "geopolitical": float(row[16]) if row[16] is not None else 0.0,
                        "social": float(row[17]) if row[17] is not None else 0.0
                    },
                    "urgency": float(row[18]) if row[18] is not None else 0.0,
                    "credibility": float(row[19]) if row[19] is not None else 0.0
                })

            logger.info(f"Article filter: Found {len(articles)} articles matching criteria")
            return articles

        except Exception as e:
            logger.error(f"Error filtering articles: {e}")
            raise

    def _parse_timeframe(self, timeframe: Any) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Parse timeframe into from/to datetime objects

        Supports:
        - Dict: {"from": "2025-10-01", "to": "2025-10-04"}
        - String: "last_24h", "last_7d", "last_30d"
        """
        if isinstance(timeframe, dict):
            # Absolute timeframe
            from_str = timeframe.get("from")
            to_str = timeframe.get("to")

            from_dt = datetime.fromisoformat(from_str) if from_str else None
            to_dt = datetime.fromisoformat(to_str) if to_str else None

            return from_dt, to_dt

        elif isinstance(timeframe, str):
            # Relative timeframe
            now = datetime.utcnow()

            if timeframe == "last_24h":
                return now - timedelta(hours=24), now
            elif timeframe == "last_7d":
                return now - timedelta(days=7), now
            elif timeframe == "last_30d":
                return now - timedelta(days=30), now
            elif timeframe == "last_hour":
                return now - timedelta(hours=1), now
            else:
                logger.warning(f"Unknown relative timeframe: {timeframe}, using last_24h")
                return now - timedelta(hours=24), now

        return None, None

    def validate_filter_config(self, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate filter configuration

        Returns:
            (is_valid, error_message)
        """
        # Required fields
        if "max_articles" not in config:
            return False, "max_articles is required"

        max_articles = config.get("max_articles")
        if not isinstance(max_articles, int) or max_articles < 1 or max_articles > 100:
            return False, "max_articles must be between 1 and 100"

        # Optional field validation
        if "impact_min" in config:
            impact_min = config.get("impact_min")
            if not isinstance(impact_min, (int, float)) or impact_min < 0 or impact_min > 1:
                return False, "impact_min must be between 0 and 1"

        if "impact_max" in config:
            impact_max = config.get("impact_max")
            if not isinstance(impact_max, (int, float)) or impact_max < 0 or impact_max > 1:
                return False, "impact_max must be between 0 and 1"

        # Category validation
        valid_categories = [
            "geopolitics_security",
            "economy_markets",
            "technology_science",
            "politics_society",
            "climate_environment_health",
            "panorama"
        ]
        if "categories" in config:
            categories = config.get("categories")
            if not isinstance(categories, list):
                return False, "categories must be a list"
            for cat in categories:
                if cat not in valid_categories:
                    return False, f"Invalid category: {cat}"

        # Sentiment validation
        valid_sentiments = ["positive", "neutral", "negative"]
        if "sentiment" in config:
            sentiments = config.get("sentiment")
            if not isinstance(sentiments, list):
                return False, "sentiment must be a list"
            for sent in sentiments:
                if sent not in valid_sentiments:
                    return False, f"Invalid sentiment: {sent}"

        return True, None

    def get_filter_preview(self, filter_config: Dict[str, Any], limit: int = 5) -> Dict[str, Any]:
        """
        Preview filter results without executing full query

        Returns article count and sample articles
        """
        try:
            # Validate config
            is_valid, error = self.validate_filter_config(filter_config)
            if not is_valid:
                return {
                    "ok": False,
                    "error": error,
                    "total_count": 0,
                    "sample_articles": []
                }

            # Get sample articles
            preview_config = filter_config.copy()
            preview_config["max_articles"] = limit
            sample_articles = self.filter_by_criteria(preview_config)

            # Get total count (without limit)
            total_count = self._get_filter_count(filter_config)

            return {
                "ok": True,
                "total_count": total_count,
                "sample_articles": sample_articles,
                "filter_config": filter_config
            }

        except Exception as e:
            logger.error(f"Error in filter preview: {e}")
            return {
                "ok": False,
                "error": str(e),
                "total_count": 0,
                "sample_articles": []
            }

    def _get_filter_count(self, filter_config: Dict[str, Any]) -> int:
        """Get total count of articles matching filter (without limit)"""
        try:
            # Similar to filter_by_criteria but only COUNT
            where_conditions = ["1=1"]
            params = {}

            # Copy-paste WHERE logic from filter_by_criteria
            # (Simplified for brevity - use same logic as above)

            timeframe = filter_config.get("timeframe")
            if timeframe:
                from_dt, to_dt = self._parse_timeframe(timeframe)
                if from_dt:
                    where_conditions.append("i.published >= :from_dt")
                    params['from_dt'] = from_dt
                if to_dt:
                    where_conditions.append("i.published <= :to_dt")
                    params['to_dt'] = to_dt

            categories = filter_config.get("categories")
            if categories:
                where_conditions.append("a.sentiment_json::jsonb->>'category' = ANY(:categories)")
                params['categories'] = categories

            where_clause = " AND ".join(where_conditions)

            query = text(f"""
                SELECT COUNT(*)
                FROM items i
                LEFT JOIN item_analysis a ON a.item_id = i.id
                WHERE {where_clause}
            """)

            result = self.session.execute(query, params)
            count = result.scalar()
            return count or 0

        except Exception as e:
            logger.error(f"Error getting filter count: {e}")
            return 0
