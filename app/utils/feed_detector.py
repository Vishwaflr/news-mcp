"""
Feed type detection utilities for automatic categorization and interval setting.
"""
import re
from typing import Optional
from sqlmodel import Session, select
from app.models import FeedType

class FeedTypeDetector:
    """Detects appropriate feed type based on URL and content analysis."""

    # URL patterns for automatic feed type detection
    PATTERNS = {
        'breaking_news': [
            r'reuters\.com',
            r'ap\.org',
            r'bbc\.com/news',
            r'cnn\.com',
        ],
        'tech_news': [
            r'techcrunch\.com',
            r'arstechnica\.com',
            r'theverge\.com',
            r'heise\.de',
            r'golem\.de',
            r'hackernews\.com',
        ],
        'crypto_news': [
            r'cointelegraph\.com',
            r'coindesk\.com',
            r'decrypt\.co',
            r'bitcoin\.com',
        ],
        'financial_news': [
            r'wsj\.com',
            r'bloomberg\.com',
            r'ft\.com',
            r'marketwatch\.com',
            r'dowjones\.io',
        ],
        'blogs': [
            r'medium\.com',
            r'substack\.com',
            r'wordpress\.com',
            r'blogspot\.com',
        ],
        'podcasts': [
            r'spotify\.com',
            r'anchor\.fm',
            r'libsyn\.com',
        ]
    }

    @classmethod
    def detect_feed_type(cls, url: str, title: str = None) -> Optional[str]:
        """
        Detect feed type based on URL patterns and optional title analysis.

        Args:
            url: Feed URL to analyze
            title: Optional feed title for additional analysis

        Returns:
            Feed type name or None if not detected
        """
        url_lower = url.lower()

        # Check URL patterns
        for feed_type, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return feed_type

        # Title-based detection as fallback
        if title:
            title_lower = title.lower()
            if any(word in title_lower for word in ['crypto', 'bitcoin', 'blockchain']):
                return 'crypto_news'
            elif any(word in title_lower for word in ['tech', 'technology', 'software']):
                return 'tech_news'
            elif any(word in title_lower for word in ['market', 'financial', 'economy']):
                return 'financial_news'
            elif any(word in title_lower for word in ['podcast', 'audio']):
                return 'podcasts'
            elif any(word in title_lower for word in ['blog', 'personal']):
                return 'blogs'

        return 'general_news'  # Default fallback

    @classmethod
    def get_recommended_interval(cls, session: Session, feed_type_name: str) -> int:
        """
        Get recommended fetch interval for a feed type.

        Args:
            session: Database session
            feed_type_name: Name of the feed type

        Returns:
            Recommended interval in minutes
        """
        feed_type = session.exec(
            select(FeedType).where(FeedType.name == feed_type_name)
        ).first()

        if feed_type:
            return feed_type.default_interval_minutes

        return 15  # Default fallback

    @classmethod
    def auto_configure_feed(cls, session: Session, url: str, title: str = None) -> dict:
        """
        Automatically configure a feed with recommended settings.

        Args:
            session: Database session
            url: Feed URL
            title: Optional feed title

        Returns:
            Dictionary with recommended configuration
        """
        feed_type_name = cls.detect_feed_type(url, title)
        interval = cls.get_recommended_interval(session, feed_type_name)

        # Get feed_type_id
        feed_type = session.exec(
            select(FeedType).where(FeedType.name == feed_type_name)
        ).first()

        return {
            'feed_type_name': feed_type_name,
            'feed_type_id': feed_type.id if feed_type else None,
            'recommended_interval': interval,
            'description': f'Auto-detected as {feed_type_name.replace("_", " ").title()}'
        }

# Test function for development
if __name__ == "__main__":
    # Test URL detection
    test_urls = [
        "https://www.heise.de/rss/heise-atom.xml",
        "https://cointelegraph.com/rss",
        "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
        "https://techcrunch.com/feed/",
        "https://some-blog.medium.com/feed"
    ]

    for url in test_urls:
        detected = FeedTypeDetector.detect_feed_type(url)
        print(f"{url} -> {detected}")