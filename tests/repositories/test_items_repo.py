"""Tests for ItemsRepository."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from app.repositories.items_repo import ItemsRepository
from app.schemas.items import ItemCreate, ItemQuery, ItemResponse
from app.db.session import DatabaseSession


class TestItemsRepository:
    """Test suite for ItemsRepository."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        mock_session = Mock(spec=DatabaseSession)
        return mock_session

    @pytest.fixture
    def items_repo(self, mock_db_session):
        """ItemsRepository instance with mocked database."""
        return ItemsRepository(mock_db_session)

    @pytest.fixture
    def sample_item_data(self):
        """Sample item data for testing."""
        return {
            "id": 1,
            "title": "Test Article",
            "link": "https://example.com/test",
            "description": "Test description",
            "content": "Test content",
            "author": "Test Author",
            "published": datetime.now(),
            "guid": "test-guid-123",
            "content_hash": "abc123",
            "feed_id": 1,
            "created_at": datetime.now(),
            "feed_title": "Test Feed",
            "feed_url": "https://example.com/feed",
            "analysis_id": 1,
            "sentiment_label": "positive",
            "sentiment_score": 0.8,
            "impact_score": 0.6,
            "urgency_score": 3
        }

    def test_row_to_item_response(self, items_repo, sample_item_data):
        """Test conversion from database row to ItemResponse."""
        # Create mock row object
        class MockRow:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)

        mock_row = MockRow(sample_item_data)
        result = items_repo._row_to_item_response(mock_row)

        assert isinstance(result, ItemResponse)
        assert result.id == sample_item_data["id"]
        assert result.title == sample_item_data["title"]
        assert result.sentiment_label == sample_item_data["sentiment_label"]

    @pytest.mark.asyncio
    async def test_get_by_id_exists(self, items_repo, mock_db_session, sample_item_data):
        """Test get_by_id when item exists."""
        # Mock database response
        class MockRow:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)

        mock_row = MockRow(sample_item_data)
        mock_db_session.execute_query.return_value = [mock_row]

        result = await items_repo.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.title == "Test Article"
        mock_db_session.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, items_repo, mock_db_session):
        """Test get_by_id when item doesn't exist."""
        mock_db_session.execute_query.return_value = []

        result = await items_repo.get_by_id(999)

        assert result is None
        mock_db_session.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_with_filters(self, items_repo, mock_db_session, sample_item_data):
        """Test query method with various filters."""
        # Mock database response
        class MockRow:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)

        mock_row = MockRow(sample_item_data)
        mock_db_session.execute_query.return_value = [mock_row]

        # Test with feed filter
        query = ItemQuery(feed_ids=[1, 2], sentiment="positive")
        results = await items_repo.query(query, limit=10)

        assert len(results) == 1
        assert results[0].id == 1
        mock_db_session.execute_query.assert_called_once()

        # Verify SQL query contains expected filters
        call_args = mock_db_session.execute_query.call_args
        sql_query = call_args[0][0]
        params = call_args[0][1]

        assert "i.feed_id IN" in sql_query
        assert "a.sentiment_label = :sentiment" in sql_query
        assert params["sentiment"] == "positive"

    @pytest.mark.asyncio
    async def test_query_with_search(self, items_repo, mock_db_session, sample_item_data):
        """Test query with search functionality."""
        class MockRow:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)

        mock_row = MockRow(sample_item_data)
        mock_db_session.execute_query.return_value = [mock_row]

        query = ItemQuery(search="test query")
        results = await items_repo.query(query)

        assert len(results) == 1
        call_args = mock_db_session.execute_query.call_args
        sql_query = call_args[0][0]
        params = call_args[0][1]

        assert "ILIKE" in sql_query
        assert params["search"] == "%test query%"

    @pytest.mark.asyncio
    async def test_count_basic(self, items_repo, mock_db_session):
        """Test count method."""
        mock_db_session.execute_query.return_value = [(42,)]

        result = await items_repo.count()

        assert result == 42
        mock_db_session.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_with_filters(self, items_repo, mock_db_session):
        """Test count method with filters."""
        mock_db_session.execute_query.return_value = [(10,)]

        query = ItemQuery(feed_ids=[1], sentiment="positive")
        result = await items_repo.count(query)

        assert result == 10

        # Verify SQL contains COUNT and filters
        call_args = mock_db_session.execute_query.call_args
        sql_query = call_args[0][0]
        assert "COUNT(DISTINCT i.id)" in sql_query
        assert "i.feed_id IN" in sql_query

    @pytest.mark.asyncio
    async def test_insert_item(self, items_repo, mock_db_session, sample_item_data):
        """Test inserting new item."""
        # Mock insert response
        class MockResult:
            id = 1
            created_at = datetime.now()

        mock_db_session.execute_insert.return_value = MockResult()

        # Mock get_by_id response for returning the created item
        class MockRow:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)

        mock_row = MockRow(sample_item_data)
        mock_db_session.execute_query.return_value = [mock_row]

        # Create item data
        create_data = ItemCreate(
            title="New Article",
            link="https://example.com/new",
            description="New description",
            content_hash="def456",
            feed_id=1
        )

        result = await items_repo.insert(create_data)

        assert result is not None
        assert result.id == 1
        mock_db_session.execute_insert.assert_called_once()
        mock_db_session.execute_query.assert_called_once()  # For get_by_id

    @pytest.mark.asyncio
    async def test_get_by_content_hash(self, items_repo, mock_db_session, sample_item_data):
        """Test finding item by content hash."""
        class MockRow:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)

        mock_row = MockRow(sample_item_data)
        mock_db_session.execute_query.return_value = [mock_row]

        result = await items_repo.get_by_content_hash("abc123")

        assert result is not None
        assert result.content_hash == "abc123"

        # Verify query uses content_hash filter
        call_args = mock_db_session.execute_query.call_args
        sql_query = call_args[0][0]
        params = call_args[0][1]

        assert "content_hash = :content_hash" in sql_query
        assert params["content_hash"] == "abc123"

    def test_get_sort_column(self, items_repo):
        """Test sort column mapping."""
        assert items_repo._get_sort_column("created_at") == "i.created_at"
        assert items_repo._get_sort_column("published") == "i.published"
        assert items_repo._get_sort_column("title") == "i.title"
        assert items_repo._get_sort_column("impact_score") == "a.impact_score"
        assert items_repo._get_sort_column("invalid") == "i.created_at"  # Default

    @pytest.mark.asyncio
    async def test_get_statistics(self, items_repo, mock_db_session):
        """Test statistics method."""
        # Mock multiple query responses
        mock_responses = [
            [(1000,)],  # total_count
            [(50,)],    # today_count
            [(75,)],    # last_24h_count
            [(200,)],   # last_week_count
            [("Test Feed", 1, 100), ("Another Feed", 2, 80)],  # by_feed
            [("positive", 30), ("negative", 20), ("neutral", 25)]  # by_sentiment
        ]

        # Configure mock to return different responses for each call
        mock_db_session.execute_query.side_effect = mock_responses

        result = await items_repo.get_statistics()

        assert result.total_count == 1000
        assert result.today_count == 50
        assert result.last_24h_count == 75
        assert result.last_week_count == 200
        assert len(result.by_feed) == 2
        assert result.by_feed[0]["count"] == 100
        assert result.by_sentiment["positive"] == 30

        # Verify 6 queries were made
        assert mock_db_session.execute_query.call_count == 6