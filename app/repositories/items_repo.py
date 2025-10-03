"""Items repository implementation."""

from app.core.logging_config import get_logger
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.base import BaseRepository, NotFoundError, PaginatedResponse
from app.schemas.items import ItemResponse, ItemCreate, ItemUpdate, ItemQuery, ItemStatistics
from app.db.session import DatabaseSession

logger = get_logger(__name__)


class ItemsRepository(BaseRepository[ItemResponse, ItemCreate, ItemUpdate, ItemQuery]):
    """
    Repository for items with analysis data.

    Required indexes:
    - items(feed_id, created_at DESC) -- feed timeline
    - items(published DESC) -- global timeline
    - items(content_hash) -- duplicate detection
    - GIN(to_tsvector('english', title || ' ' || coalesce(description, ''))) -- full-text search
    """

    def __init__(self, db_session: DatabaseSession):
        super().__init__(db_session)

    async def get_by_id(self, item_id: int) -> Optional[ItemResponse]:
        """Get single item by ID with feed and analysis data."""
        query = """
        SELECT
            i.id, i.title, i.link, i.description, i.content, i.author,
            i.published, i.guid, i.content_hash, i.feed_id, i.created_at,
            f.title as feed_title, f.url as feed_url,
            a.item_id as analysis_id,
            (a.sentiment_json->'overall'->>'label')::text as sentiment_label,
            (a.sentiment_json->'overall'->>'score')::float as sentiment_score,
            (a.impact_json->>'overall')::float as impact_score,
            (a.sentiment_json->>'urgency')::float as urgency_score
        FROM items i
        LEFT JOIN feeds f ON i.feed_id = f.id
        LEFT JOIN item_analysis a ON i.id = a.item_id
        WHERE i.id = :item_id
        """

        results = self._execute_query(query, {"item_id": item_id})
        if not results:
            return None

        row = results[0]
        return self._row_to_item_response(row)

    async def list(self, limit: int = 100, offset: int = 0) -> List[ItemResponse]:
        """List items with basic pagination."""
        return await self.query(ItemQuery(), limit=limit, offset=offset)

    async def query(self, filter_obj: ItemQuery, limit: int = 100, offset: int = 0) -> List[ItemResponse]:
        """Query items with filters."""
        params = {}
        where_conditions = []

        # Base query with joins
        base_query = """
        SELECT
            i.id, i.title, i.link, i.description, i.content, i.author,
            i.published, i.guid, i.content_hash, i.feed_id, i.created_at,
            f.title as feed_title, f.url as feed_url,
            a.item_id as analysis_id,
            (a.sentiment_json->'overall'->>'label')::text as sentiment_label,
            (a.sentiment_json->'overall'->>'score')::float as sentiment_score,
            (a.impact_json->>'overall')::float as impact_score,
            (a.sentiment_json->>'urgency')::float as urgency_score
        FROM items i
        LEFT JOIN feeds f ON i.feed_id = f.id
        LEFT JOIN item_analysis a ON i.id = a.item_id
        """

        # Build WHERE conditions
        if filter_obj.feed_ids:
            placeholders = [f":feed_id_{i}" for i in range(len(filter_obj.feed_ids))]
            where_conditions.append(f"i.feed_id IN ({','.join(placeholders)})")
            for i, feed_id in enumerate(filter_obj.feed_ids):
                params[f"feed_id_{i}"] = feed_id

        if filter_obj.category_id:
            # Need to join with feed_categories
            base_query = base_query.replace(
                "FROM items i",
                "FROM items i JOIN feed_categories fc ON i.feed_id = fc.feed_id"
            )
            where_conditions.append("fc.category_id = :category_id")
            params["category_id"] = filter_obj.category_id

        if filter_obj.from_date:
            where_conditions.append("i.created_at >= :from_date")
            params["from_date"] = filter_obj.from_date

        if filter_obj.to_date:
            where_conditions.append("i.created_at <= :to_date")
            params["to_date"] = filter_obj.to_date

        if filter_obj.search:
            where_conditions.append(
                "(i.title ILIKE :search OR i.description ILIKE :search)"
            )
            params["search"] = f"%{filter_obj.search}%"

        if filter_obj.sentiment:
            where_conditions.append("a.sentiment_label = :sentiment")
            params["sentiment"] = filter_obj.sentiment

        if filter_obj.impact_min is not None:
            where_conditions.append("a.impact_score >= :impact_min")
            params["impact_min"] = filter_obj.impact_min

        if filter_obj.urgency_min is not None:
            where_conditions.append("a.urgency_score >= :urgency_min")
            params["urgency_min"] = filter_obj.urgency_min

        if filter_obj.has_analysis is not None:
            if filter_obj.has_analysis:
                where_conditions.append("a.id IS NOT NULL")
            else:
                where_conditions.append("a.id IS NULL")

        # Build complete query
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)

        # Add sorting
        sort_column = self._get_sort_column(filter_obj.sort_by)
        direction = "DESC" if filter_obj.sort_desc else "ASC"
        base_query += f" ORDER BY {sort_column} {direction}"

        # Add pagination
        base_query += " LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        results = self._execute_query(base_query, params)
        return [self._row_to_item_response(row) for row in results]

    async def count(self, filter_obj: Optional[ItemQuery] = None) -> int:
        """Count items matching filter."""
        if not filter_obj:
            filter_obj = ItemQuery()

        params = {}
        where_conditions = []

        base_query = "SELECT COUNT(DISTINCT i.id) FROM items i"

        # Apply same filters as in query method (simplified)
        if filter_obj.feed_ids:
            placeholders = [f":feed_id_{i}" for i in range(len(filter_obj.feed_ids))]
            where_conditions.append(f"i.feed_id IN ({','.join(placeholders)})")
            for i, feed_id in enumerate(filter_obj.feed_ids):
                params[f"feed_id_{i}"] = feed_id

        if filter_obj.category_id:
            base_query += " JOIN feed_categories fc ON i.feed_id = fc.feed_id"
            where_conditions.append("fc.category_id = :category_id")
            params["category_id"] = filter_obj.category_id

        if filter_obj.from_date:
            where_conditions.append("i.created_at >= :from_date")
            params["from_date"] = filter_obj.from_date

        if filter_obj.to_date:
            where_conditions.append("i.created_at <= :to_date")
            params["to_date"] = filter_obj.to_date

        if filter_obj.search:
            where_conditions.append(
                "(i.title ILIKE :search OR i.description ILIKE :search)"
            )
            params["search"] = f"%{filter_obj.search}%"

        # Analysis-related filters need LEFT JOIN
        if (filter_obj.sentiment or filter_obj.impact_min is not None or
            filter_obj.urgency_min is not None or filter_obj.has_analysis is not None):
            base_query += " LEFT JOIN item_analysis a ON i.id = a.item_id"

            if filter_obj.sentiment:
                where_conditions.append("a.sentiment_label = :sentiment")
                params["sentiment"] = filter_obj.sentiment

            if filter_obj.impact_min is not None:
                where_conditions.append("a.impact_score >= :impact_min")
                params["impact_min"] = filter_obj.impact_min

            if filter_obj.urgency_min is not None:
                where_conditions.append("a.urgency_score >= :urgency_min")
                params["urgency_min"] = filter_obj.urgency_min

            if filter_obj.has_analysis is not None:
                if filter_obj.has_analysis:
                    where_conditions.append("a.id IS NOT NULL")
                else:
                    where_conditions.append("a.id IS NULL")

        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)

        result = self._execute_query(base_query, params)
        return result[0][0] if result else 0

    async def insert(self, data: ItemCreate) -> ItemResponse:
        """Insert new item."""
        query = """
        INSERT INTO items (title, link, description, content, author, published,
                          guid, content_hash, feed_id, created_at)
        VALUES (:title, :link, :description, :content, :author, :published,
                :guid, :content_hash, :feed_id, NOW())
        RETURNING id, created_at
        """

        params = data.dict()
        result = self._execute_insert(query, params)

        if not result:
            raise Exception("Failed to insert item")

        # Return the created item
        return await self.get_by_id(result.id)

    async def update(self, item_id: int, data: ItemUpdate) -> Optional[ItemResponse]:
        """Update existing item (rarely used)."""
        # Build dynamic update query
        update_fields = []
        params = {"item_id": item_id}

        for field, value in data.dict(exclude_unset=True).items():
            if value is not None:
                update_fields.append(f"{field} = :{field}")
                params[field] = value

        if not update_fields:
            return await self.get_by_id(item_id)

        query = f"""
        UPDATE items
        SET {', '.join(update_fields)}
        WHERE id = :item_id
        RETURNING id
        """

        result = self._execute_insert(query, params)
        if not result:
            raise NotFoundError(f"Item {item_id} not found")

        return await self.get_by_id(item_id)

    async def delete(self, item_id: int) -> bool:
        """Delete item by ID."""
        query = "DELETE FROM items WHERE id = :item_id RETURNING id"
        result = self._execute_insert(query, {"item_id": item_id})
        return result is not None

    async def get_by_content_hash(self, content_hash: str) -> Optional[ItemResponse]:
        """Find item by content hash (for duplicate detection)."""
        query = """
        SELECT
            i.id, i.title, i.link, i.description, i.content, i.author,
            i.published, i.guid, i.content_hash, i.feed_id, i.created_at,
            f.title as feed_title, f.url as feed_url,
            a.item_id as analysis_id,
            (a.sentiment_json->'overall'->>'label')::text as sentiment_label,
            (a.sentiment_json->'overall'->>'score')::float as sentiment_score,
            (a.impact_json->>'overall')::float as impact_score,
            (a.sentiment_json->>'urgency')::float as urgency_score
        FROM items i
        LEFT JOIN feeds f ON i.feed_id = f.id
        LEFT JOIN item_analysis a ON i.id = a.item_id
        WHERE i.content_hash = :content_hash
        """

        results = self._execute_query(query, {"content_hash": content_hash})
        if not results:
            return None

        return self._row_to_item_response(results[0])

    async def get_statistics(self) -> ItemStatistics:
        """Get item statistics."""
        # Total count
        total_result = self._execute_query("SELECT COUNT(*) FROM items")
        total_count = total_result[0][0] if total_result else 0

        # Today's count
        today_result = self._execute_query("""
        SELECT COUNT(*) FROM items
        WHERE created_at >= CURRENT_DATE
        """)
        today_count = today_result[0][0] if today_result else 0

        # Last 24h count
        last_24h_result = self._execute_query("""
        SELECT COUNT(*) FROM items
        WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        last_24h_count = last_24h_result[0][0] if last_24h_result else 0

        # Last week count
        last_week_result = self._execute_query("""
        SELECT COUNT(*) FROM items
        WHERE created_at >= NOW() - INTERVAL '7 days'
        """)
        last_week_count = last_week_result[0][0] if last_week_result else 0

        # By feed (top 10)
        by_feed_result = self._execute_query("""
        SELECT f.title, f.id, COUNT(i.id) as count
        FROM feeds f
        LEFT JOIN items i ON f.id = i.feed_id
        GROUP BY f.id, f.title
        ORDER BY count DESC
        LIMIT 10
        """)
        by_feed = [{"feed_title": row[0], "feed_id": row[1], "count": row[2]}
                   for row in by_feed_result]

        # By sentiment (if analysis exists)
        by_sentiment_result = self._execute_query("""
        SELECT a.sentiment_label, COUNT(*) as count
        FROM item_analysis a
        GROUP BY a.sentiment_label
        """)
        by_sentiment = {row[0]: row[1] for row in by_sentiment_result}

        return ItemStatistics(
            total_count=total_count,
            today_count=today_count,
            last_24h_count=last_24h_count,
            last_week_count=last_week_count,
            by_feed=by_feed,
            by_sentiment=by_sentiment
        )

    def _row_to_item_response(self, row) -> ItemResponse:
        """Convert database row to ItemResponse DTO."""
        return ItemResponse(
            id=row.id,
            title=row.title,
            link=row.link,
            description=row.description,
            content=row.content,
            author=row.author,
            published=row.published,
            guid=row.guid,
            content_hash=row.content_hash,
            feed_id=row.feed_id,
            created_at=row.created_at,
            feed_title=row.feed_title,
            feed_url=row.feed_url,
            analysis_id=row.analysis_id,
            sentiment_label=row.sentiment_label,
            sentiment_score=row.sentiment_score,
            impact_score=row.impact_score,
            urgency_score=row.urgency_score
        )

    def _get_sort_column(self, sort_by: str) -> str:
        """Map sort field to actual column name."""
        mapping = {
            "created_at": "i.created_at",
            "published": "i.published",
            "title": "i.title",
            "impact_score": "a.impact_score"
        }
        return mapping.get(sort_by, "i.created_at")