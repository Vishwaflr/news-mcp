"""Feed health scoring service.

Implements health score calculation based on:
- Reachability (30%): Can we fetch the feed?
- Volume (25%): Is the feed producing articles?
- Duplicates (15%): Are articles unique?
- Quality (15%): Are articles being analyzed successfully?
- Stability (15%): Is the feed consistently available?
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlmodel import Session, select, func
from app.core.logging_config import get_logger
from app.models import Feed, Item, FetchLog

logger = get_logger(__name__)


class FeedHealthScorer:
    """Calculate health scores for feeds."""

    # Weights for each metric (must sum to 100)
    WEIGHT_REACHABILITY = 30
    WEIGHT_VOLUME = 25
    WEIGHT_DUPLICATES = 15
    WEIGHT_QUALITY = 15
    WEIGHT_STABILITY = 15

    def __init__(self, session: Session):
        self.session = session

    def calculate_health_score(self, feed_id: int) -> Dict[str, any]:
        """Calculate comprehensive health score for a feed.

        Returns:
            Dict with 'score' (0-100), 'components', and 'recommendation'
        """
        feed = self.session.get(Feed, feed_id)
        if not feed:
            return {"score": 0, "components": {}, "recommendation": "Feed not found"}

        # Calculate individual components
        reachability_score = self._calculate_reachability(feed_id)
        volume_score = self._calculate_volume(feed_id)
        duplicates_score = self._calculate_duplicates(feed_id)
        quality_score = self._calculate_quality(feed_id)
        stability_score = self._calculate_stability(feed_id)

        # Weighted total
        total_score = (
            reachability_score * self.WEIGHT_REACHABILITY +
            volume_score * self.WEIGHT_VOLUME +
            duplicates_score * self.WEIGHT_DUPLICATES +
            quality_score * self.WEIGHT_QUALITY +
            stability_score * self.WEIGHT_STABILITY
        ) / 100

        components = {
            "reachability": {"score": reachability_score, "weight": self.WEIGHT_REACHABILITY},
            "volume": {"score": volume_score, "weight": self.WEIGHT_VOLUME},
            "duplicates": {"score": duplicates_score, "weight": self.WEIGHT_DUPLICATES},
            "quality": {"score": quality_score, "weight": self.WEIGHT_QUALITY},
            "stability": {"score": stability_score, "weight": self.WEIGHT_STABILITY}
        }

        recommendation = self._generate_recommendation(components, total_score)

        return {
            "score": int(total_score),
            "components": components,
            "recommendation": recommendation
        }

    def update_feed_statistics(self, feed_id: int) -> bool:
        """Update feed statistics (article counts, analysis percentage).

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from app.models import ItemAnalysis

            feed = self.session.get(Feed, feed_id)
            if not feed:
                return False

            # Count total articles
            total_articles = self.session.exec(
                select(func.count(Item.id)).where(Item.feed_id == feed_id)
            ).one()

            # Count articles in last 24 hours
            cutoff_24h = datetime.utcnow() - timedelta(hours=24)
            articles_24h = self.session.exec(
                select(func.count(Item.id)).where(
                    Item.feed_id == feed_id,
                    Item.published >= cutoff_24h
                )
            ).one()

            # Count analyzed articles
            analyzed_count = self.session.exec(
                select(func.count(ItemAnalysis.item_id))
                .select_from(Item)
                .join(ItemAnalysis, Item.id == ItemAnalysis.item_id)
                .where(Item.feed_id == feed_id)
            ).one()

            # Calculate percentage
            analyzed_percentage = 0.0
            if total_articles > 0:
                analyzed_percentage = round((analyzed_count * 100.0) / total_articles, 2)

            # Update feed
            feed.total_articles = total_articles
            feed.articles_24h = articles_24h
            feed.analyzed_count = analyzed_count
            feed.analyzed_percentage = analyzed_percentage
            feed.updated_at = datetime.utcnow()

            self.session.commit()

            logger.info(
                f"Updated feed {feed_id} stats: {total_articles} articles, "
                f"{analyzed_count} analyzed ({analyzed_percentage}%)"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to update feed statistics for feed {feed_id}: {e}")
            self.session.rollback()
            return False

    def update_feed_health_score(self, feed_id: int) -> bool:
        """Calculate and persist health score to database.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.calculate_health_score(feed_id)
            feed = self.session.get(Feed, feed_id)

            if feed:
                feed.health_score = result["score"]
                feed.updated_at = datetime.utcnow()
                self.session.commit()

                logger.info(f"Updated health score for feed {feed_id}: {result['score']}/100")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to update health score for feed {feed_id}: {e}")
            self.session.rollback()
            return False

    def _calculate_reachability(self, feed_id: int) -> float:
        """Score based on recent fetch success rate (0-100).

        Looks at last 10 fetch attempts:
        - 100 points: All successful
        - 50 points: 50% success rate
        - 0 points: All failed or no fetches
        """
        cutoff = datetime.utcnow() - timedelta(days=7)

        fetch_logs = self.session.exec(
            select(FetchLog)
            .where(FetchLog.feed_id == feed_id)
            .where(FetchLog.created_at >= cutoff)
            .order_by(FetchLog.created_at.desc())
            .limit(10)
        ).all()

        if not fetch_logs:
            return 0.0

        success_count = sum(1 for log in fetch_logs if log.status == 'success')
        success_rate = success_count / len(fetch_logs)

        return success_rate * 100

    def _calculate_volume(self, feed_id: int) -> float:
        """Score based on article production rate (0-100).

        Scoring:
        - 100 points: 20+ articles in last 24h
        - 75 points: 10-19 articles
        - 50 points: 5-9 articles
        - 25 points: 1-4 articles
        - 0 points: No articles
        """
        cutoff = datetime.utcnow() - timedelta(hours=24)

        count = self.session.exec(
            select(func.count(Item.id))
            .where(Item.feed_id == feed_id)
            .where(Item.created_at >= cutoff)
        ).one()

        if count >= 20:
            return 100.0
        elif count >= 10:
            return 75.0
        elif count >= 5:
            return 50.0
        elif count >= 1:
            return 25.0
        else:
            return 0.0

    def _calculate_duplicates(self, feed_id: int) -> float:
        """Score based on article uniqueness (0-100).

        Checks for duplicate titles/links in last 100 articles:
        - 100 points: No duplicates
        - 50 points: 10% duplicates
        - 0 points: 20%+ duplicates
        """
        recent_items = self.session.exec(
            select(Item)
            .where(Item.feed_id == feed_id)
            .order_by(Item.created_at.desc())
            .limit(100)
        ).all()

        if not recent_items:
            return 100.0  # No data = assume good

        # Check for duplicate links
        links = [item.link for item in recent_items if item.link]
        unique_links = len(set(links))
        total_links = len(links)

        if total_links == 0:
            return 100.0

        duplicate_rate = 1 - (unique_links / total_links)

        if duplicate_rate >= 0.20:
            return 0.0
        elif duplicate_rate >= 0.10:
            return 50.0
        else:
            # Linear scaling: 0% duplicates = 100, 10% = 50
            return 100 - (duplicate_rate * 500)

    def _calculate_quality(self, feed_id: int) -> float:
        """Score based on analysis success rate (0-100).

        Uses analyzed_percentage from feed analytics:
        - 100 points: 80%+ articles analyzed
        - 50 points: 40-79% analyzed
        - 0 points: <40% analyzed
        """
        feed = self.session.get(Feed, feed_id)

        if not feed or feed.total_articles == 0:
            return 100.0  # No articles yet = assume good

        analyzed_pct = feed.analyzed_percentage or 0.0

        if analyzed_pct >= 80:
            return 100.0
        elif analyzed_pct >= 40:
            # Linear scaling: 40% = 50 points, 80% = 100 points
            return 50 + ((analyzed_pct - 40) * 1.25)
        else:
            # Linear scaling: 0% = 0 points, 40% = 50 points
            return analyzed_pct * 1.25

    def _calculate_stability(self, feed_id: int) -> float:
        """Score based on fetch consistency (0-100).

        Measures time since last successful fetch:
        - 100 points: Fetched in last hour
        - 75 points: Fetched in last 6 hours
        - 50 points: Fetched in last 24 hours
        - 25 points: Fetched in last 7 days
        - 0 points: No fetch in 7+ days
        """
        feed = self.session.get(Feed, feed_id)

        if not feed or not feed.last_fetched:
            return 0.0

        time_since_fetch = datetime.utcnow() - feed.last_fetched

        if time_since_fetch <= timedelta(hours=1):
            return 100.0
        elif time_since_fetch <= timedelta(hours=6):
            return 75.0
        elif time_since_fetch <= timedelta(hours=24):
            return 50.0
        elif time_since_fetch <= timedelta(days=7):
            return 25.0
        else:
            return 0.0

    def _generate_recommendation(self, components: Dict, total_score: float) -> str:
        """Generate actionable recommendation based on scores."""
        if total_score >= 80:
            return "Healthy - Feed is performing well"

        # Find weakest component
        weakest = min(components.items(), key=lambda x: x[1]["score"])
        component_name = weakest[0]
        component_score = weakest[1]["score"]

        if component_name == "reachability" and component_score < 50:
            return "Action Required - Feed is unreachable, check URL or server status"
        elif component_name == "volume" and component_score < 50:
            return "Low Activity - Feed producing few articles, verify it's still active"
        elif component_name == "duplicates" and component_score < 50:
            return "Quality Issue - High duplicate rate detected, check feed configuration"
        elif component_name == "quality" and component_score < 50:
            return "Analysis Issues - Many articles failing analysis, check content format"
        elif component_name == "stability" and component_score < 50:
            return "Unstable - Feed fetch schedule inconsistent, review fetch intervals"

        return "Needs Attention - Multiple metrics below optimal levels"


def update_all_feed_health_scores(session: Session) -> int:
    """Update health scores for all active feeds.

    Returns:
        int: Number of feeds updated
    """
    scorer = FeedHealthScorer(session)
    feeds = session.exec(select(Feed).where(Feed.status == 'active')).all()

    updated_count = 0
    for feed in feeds:
        if scorer.update_feed_health_score(feed.id):
            updated_count += 1

    logger.info(f"Updated health scores for {updated_count}/{len(feeds)} feeds")
    return updated_count
