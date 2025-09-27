"""
Selection Cache Service
Stores article selections for Preview & Articles synchronization

Future: Replace with Redis for persistence
"""
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class SelectionMetadata:
    """Metadata about a selection"""
    mode: str
    count: int
    feed_id: Optional[int]
    hours: Optional[int]
    date_from: Optional[str]
    date_to: Optional[str]
    unanalyzed_only: bool
    total_items: int
    created_at: str


class SelectionCache:
    """
    In-memory cache for article selections

    Design: Drop-in replaceable with Redis
    - Keys are selection hashes
    - Values are {articles, metadata}
    - No TTL: Cache invalidates only on change
    """

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        logger.info("SelectionCache initialized (in-memory)")

    def generate_key(self, selection_params: Dict[str, Any]) -> str:
        """
        Generate deterministic cache key from selection parameters
        Same params → Same key → Cache hit
        """
        # Sort keys for consistent hash
        normalized = {
            'mode': selection_params.get('mode', 'latest'),
            'count': selection_params.get('count', 50),
            'feed_id': selection_params.get('feed_id'),
            'hours': selection_params.get('hours'),
            'date_from': selection_params.get('date_from'),
            'date_to': selection_params.get('date_to'),
            'unanalyzed_only': selection_params.get('unanalyzed_only', False)
        }

        # Create hash
        key_string = json.dumps(normalized, sort_keys=True)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]

        logger.debug(f"Generated cache key: {key_hash} for {normalized}")
        return key_hash

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached selection by key"""
        result = self._cache.get(cache_key)
        if result:
            logger.info(f"Cache HIT: {cache_key}")
        else:
            logger.info(f"Cache MISS: {cache_key}")
        return result

    def set(
        self,
        cache_key: str,
        articles: List[Dict[str, Any]],
        metadata: SelectionMetadata
    ) -> None:
        """Store selection in cache"""
        self._cache[cache_key] = {
            'articles': articles,
            'metadata': asdict(metadata),
            'cached_at': datetime.utcnow().isoformat()
        }
        logger.info(f"Cached selection {cache_key}: {len(articles)} articles")

    def invalidate(self, cache_key: str) -> None:
        """Remove selection from cache"""
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.info(f"Invalidated cache: {cache_key}")

    def clear_all(self) -> None:
        """Clear entire cache (admin function)"""
        count = len(self._cache)
        self._cache.clear()
        logger.warning(f"Cleared entire cache: {count} entries removed")

    def stats(self) -> Dict[str, int]:
        """Cache statistics"""
        return {
            'total_entries': len(self._cache),
            'total_articles': sum(len(v['articles']) for v in self._cache.values())
        }


# Singleton instance
_selection_cache: Optional[SelectionCache] = None


def get_selection_cache() -> SelectionCache:
    """Get or create singleton SelectionCache instance"""
    global _selection_cache
    if _selection_cache is None:
        _selection_cache = SelectionCache()
    return _selection_cache