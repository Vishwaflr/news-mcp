import pytest
from sqlmodel import Session, text
from app.database import engine
from app.repositories.analysis import AnalysisRepo
from app.domain.analysis.schema import (
    AnalysisResult, Overall, Market, SentimentPayload, ImpactPayload
)

class TestAnalysisUpsert:
    def create_test_analysis(self) -> AnalysisResult:
        """Create a test analysis result"""
        return AnalysisResult(
            sentiment=SentimentPayload(
                overall=Overall(label="positive", score=0.8, confidence=0.9),
                market=Market(bullish=0.7, bearish=0.2, uncertainty=0.1, time_horizon="short"),
                urgency=0.6,
                themes=["crypto", "bitcoin"]
            ),
            impact=ImpactPayload(overall=0.8, volatility=0.4),
            model_tag="gpt-4o-mini-test"
        )

    def test_upsert_new_analysis(self):
        """Test inserting new analysis data"""
        analysis = self.create_test_analysis()

        # Get a real item ID from the database
        with Session(engine) as session:
            result = session.execute(text("SELECT id FROM items LIMIT 1")).first()
            if not result:
                pytest.skip("No items in database to test with")
            test_item_id = result[0]

        try:
            # Clean any existing analysis first
            with Session(engine) as session:
                session.execute(text("DELETE FROM item_analysis WHERE item_id = :id"), {"id": test_item_id})
                session.commit()

            # Insert new analysis
            AnalysisRepo.upsert(test_item_id, analysis)

            # Verify it was inserted
            result = AnalysisRepo.get_by_item_id(test_item_id)
            assert result is not None
            assert result["model_tag"] == "gpt-4o-mini-test"
            assert result["sentiment_json"]["overall"]["label"] == "positive"
            assert result["impact_json"]["overall"] == 0.8

        finally:
            # Cleanup
            with Session(engine) as session:
                session.execute(text("DELETE FROM item_analysis WHERE item_id = :id"), {"id": test_item_id})
                session.commit()

    def test_upsert_update_existing(self):
        """Test updating existing analysis data"""
        analysis1 = self.create_test_analysis()

        # Get a real item ID from the database
        with Session(engine) as session:
            result = session.execute(text("SELECT id FROM items LIMIT 1 OFFSET 1")).first()
            if not result:
                pytest.skip("Not enough items in database to test with")
            test_item_id = result[0]

        try:
            # Clean any existing analysis first
            with Session(engine) as session:
                session.execute(text("DELETE FROM item_analysis WHERE item_id = :id"), {"id": test_item_id})
                session.commit()

            # Insert first analysis
            AnalysisRepo.upsert(test_item_id, analysis1)

            # Create updated analysis
            analysis2 = AnalysisResult(
                sentiment=SentimentPayload(
                    overall=Overall(label="negative", score=-0.5, confidence=0.8),
                    market=Market(bullish=0.2, bearish=0.7, uncertainty=0.1, time_horizon="medium"),
                    urgency=0.9,
                    themes=["crash", "bearish"]
                ),
                impact=ImpactPayload(overall=0.9, volatility=0.8),
                model_tag="gpt-4o-mini-updated"
            )

            # Update analysis
            AnalysisRepo.upsert(test_item_id, analysis2)

            # Verify it was updated
            result = AnalysisRepo.get_by_item_id(test_item_id)
            assert result is not None
            assert result["model_tag"] == "gpt-4o-mini-updated"
            assert result["sentiment_json"]["overall"]["label"] == "negative"
            assert result["impact_json"]["overall"] == 0.9

        finally:
            # Cleanup
            with Session(engine) as session:
                session.execute(text("DELETE FROM item_analysis WHERE item_id = :id"), {"id": test_item_id})
                session.commit()

    def test_get_nonexistent_analysis(self):
        """Test getting analysis for non-existent item"""
        result = AnalysisRepo.get_by_item_id(999997)
        assert result is None

    def test_count_pending_analysis(self):
        """Test counting items without analysis"""
        count = AnalysisRepo.count_pending_analysis()
        assert isinstance(count, int)
        assert count >= 0

    def test_get_analysis_stats(self):
        """Test getting analysis statistics"""
        stats = AnalysisRepo.get_analysis_stats()
        assert isinstance(stats, dict)

        if stats:  # Only check structure if we have data
            assert "total_analyzed" in stats
            assert "sentiment_distribution" in stats
            assert "avg_impact" in stats
            assert "avg_urgency" in stats