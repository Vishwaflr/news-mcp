import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestItemsFilters:
    def test_analyzed_items_no_filters(self):
        """Test getting analyzed items without filters"""
        response = client.get("/api/items/analyzed")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_analyzed_items_impact_filter(self):
        """Test impact_min filter"""
        response = client.get("/api/items/analyzed?impact_min=0.7")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Check that all items have impact >= 0.7
        for item in data:
            if "impact_json" in item:
                impact = item["impact_json"].get("overall", 0)
                assert impact >= 0.7

    def test_analyzed_items_sentiment_filter(self):
        """Test sentiment filter"""
        response = client.get("/api/items/analyzed?sentiment=positive")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Check that all items have positive sentiment
        for item in data:
            if "sentiment_json" in item:
                sentiment = item["sentiment_json"].get("overall", {}).get("label")
                assert sentiment == "positive"

    def test_analyzed_items_urgency_filter(self):
        """Test urgency_min filter"""
        response = client.get("/api/items/analyzed?urgency_min=0.6")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Check that all items have urgency >= 0.6
        for item in data:
            if "sentiment_json" in item:
                urgency = item["sentiment_json"].get("urgency", 0)
                assert urgency >= 0.6

    def test_analyzed_items_combined_filters(self):
        """Test combining multiple filters"""
        response = client.get("/api/items/analyzed?sentiment=negative&urgency_min=0.6&impact_min=0.5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Check that all items meet all criteria
        for item in data:
            if "sentiment_json" in item and "impact_json" in item:
                sentiment = item["sentiment_json"].get("overall", {}).get("label")
                urgency = item["sentiment_json"].get("urgency", 0)
                impact = item["impact_json"].get("overall", 0)

                assert sentiment == "negative"
                assert urgency >= 0.6
                assert impact >= 0.5

    def test_analyzed_items_invalid_sentiment(self):
        """Test invalid sentiment value"""
        response = client.get("/api/items/analyzed?sentiment=invalid")
        assert response.status_code == 422  # Validation error

    def test_analyzed_items_invalid_impact_range(self):
        """Test invalid impact range"""
        response = client.get("/api/items/analyzed?impact_min=1.5")
        assert response.status_code == 422  # Validation error

    def test_analyzed_items_limit(self):
        """Test limit parameter"""
        response = client.get("/api/items/analyzed?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5

    def test_analysis_stats_endpoint(self):
        """Test analysis statistics endpoint"""
        response = client.get("/api/items/analysis/stats")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_single_item_analysis(self):
        """Test getting analysis for a specific item"""
        # First get any analyzed item
        response = client.get("/api/items/analyzed?limit=1")
        assert response.status_code == 200
        items = response.json()

        if items:
            item_id = items[0]["id"]
            response = client.get(f"/api/items/{item_id}/analysis")

            if response.status_code == 200:
                data = response.json()
                assert "sentiment_json" in data
                assert "impact_json" in data
                assert "model_tag" in data
            else:
                # Item might not have analysis yet
                assert response.status_code == 404