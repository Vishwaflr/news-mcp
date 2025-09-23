"""Shadow comparison utilities for safe repo migration."""

import time
from app.core.logging_config import get_logger
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = get_logger(__name__)


class ComparisonResult(Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    ERROR = "error"


@dataclass
class ShadowCompareMetrics:
    """Metrics for shadow comparison."""
    old_duration_ms: float
    new_duration_ms: float
    old_count: int
    new_count: int
    result: ComparisonResult
    mismatch_details: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class ShadowComparer:
    """Utility for comparing old Raw-SQL vs new Repository implementations."""

    def __init__(self, sample_rate: float = 0.1, max_mismatches: int = 5):
        self.sample_rate = sample_rate  # 10% of requests by default
        self.max_mismatches = max_mismatches
        self.metrics: List[ShadowCompareMetrics] = []

    def should_compare(self) -> bool:
        """Determine if this request should be compared (sampling)."""
        import random
        return random.random() < self.sample_rate

    async def compare_items_list(
        self,
        old_func,
        new_func,
        *args,
        **kwargs
    ) -> ShadowCompareMetrics:
        """
        Compare old Raw-SQL items list with new Repository implementation.

        Args:
            old_func: Function that returns old implementation result
            new_func: Function that returns new implementation result
            *args, **kwargs: Arguments to pass to both functions
        """
        metrics = ShadowCompareMetrics(
            old_duration_ms=0,
            new_duration_ms=0,
            old_count=0,
            new_count=0,
            result=ComparisonResult.ERROR
        )

        try:
            # Execute old implementation
            start_time = time.perf_counter()
            old_result = await old_func(*args, **kwargs)
            metrics.old_duration_ms = (time.perf_counter() - start_time) * 1000

            # Execute new implementation
            start_time = time.perf_counter()
            new_result = await new_func(*args, **kwargs)
            metrics.new_duration_ms = (time.perf_counter() - start_time) * 1000

            # Extract item counts from HTML or data
            metrics.old_count = self._extract_item_count(old_result)
            metrics.new_count = self._extract_item_count(new_result)

            # Compare results
            if metrics.old_count == metrics.new_count:
                # Deep comparison of structure
                old_items = self._extract_items_data(old_result)
                new_items = self._extract_items_data(new_result)

                mismatches = self._compare_items(old_items, new_items)
                if not mismatches:
                    metrics.result = ComparisonResult.MATCH
                else:
                    metrics.result = ComparisonResult.MISMATCH
                    metrics.mismatch_details = {
                        "mismatches": mismatches[:self.max_mismatches],
                        "total_mismatches": len(mismatches)
                    }
            else:
                metrics.result = ComparisonResult.MISMATCH
                metrics.mismatch_details = {
                    "count_diff": metrics.new_count - metrics.old_count
                }

        except Exception as e:
            logger.error(f"Shadow comparison error: {e}")
            metrics.error_details = str(e)
            metrics.result = ComparisonResult.ERROR

        # Store metrics
        self.metrics.append(metrics)

        # Log significant issues
        if metrics.result == ComparisonResult.MISMATCH:
            logger.warning(f"Shadow comparison mismatch: {metrics.mismatch_details}")
        elif metrics.result == ComparisonResult.ERROR:
            logger.error(f"Shadow comparison error: {metrics.error_details}")

        return metrics

    def _extract_item_count(self, html_or_data) -> int:
        """Extract number of items from HTML response or data structure."""
        if isinstance(html_or_data, str):
            # Count card elements in HTML
            return html_or_data.count('class="card mb-3"')
        elif isinstance(html_or_data, list):
            return len(html_or_data)
        elif isinstance(html_or_data, dict) and 'items' in html_or_data:
            return len(html_or_data['items'])
        return 0

    def _extract_items_data(self, html_or_data) -> List[Dict[str, Any]]:
        """Extract structured item data for comparison."""
        if isinstance(html_or_data, list):
            return [item.dict() if hasattr(item, 'dict') else item for item in html_or_data]
        elif isinstance(html_or_data, dict) and 'items' in html_or_data:
            return [item.dict() if hasattr(item, 'dict') else item for item in html_or_data['items']]
        elif isinstance(html_or_data, str):
            # Extract data from HTML (simplified - for real comparison would need proper parsing)
            return self._parse_html_items(html_or_data)
        return []

    def _parse_html_items(self, html: str) -> List[Dict[str, Any]]:
        """Parse item data from HTML (simplified implementation)."""
        import re

        items = []
        # Extract item IDs from HTML
        item_ids = re.findall(r'id="item-(\d+)"', html)

        for item_id in item_ids:
            # Extract basic data - in real implementation would use proper HTML parser
            item_pattern = rf'id="item-{item_id}".*?</div>\s*</div>'
            item_html = re.search(item_pattern, html, re.DOTALL)

            if item_html:
                item_data = {
                    'id': int(item_id),
                    'has_sentiment': 'sentiment-analysis' in item_html.group(),
                    'has_link': 'href=' in item_html.group()
                }
                items.append(item_data)

        return items

    def _compare_items(self, old_items: List[Dict], new_items: List[Dict]) -> List[Dict[str, Any]]:
        """Compare two lists of items and return mismatches."""
        mismatches = []

        # Create lookup by ID for efficient comparison
        old_by_id = {item.get('id'): item for item in old_items if item.get('id')}
        new_by_id = {item.get('id'): item for item in new_items if item.get('id')}

        # Check for missing items
        old_ids = set(old_by_id.keys())
        new_ids = set(new_by_id.keys())

        missing_in_new = old_ids - new_ids
        missing_in_old = new_ids - old_ids

        for item_id in missing_in_new:
            mismatches.append({
                'type': 'missing_in_new',
                'item_id': item_id,
                'old_item': old_by_id[item_id]
            })

        for item_id in missing_in_old:
            mismatches.append({
                'type': 'extra_in_new',
                'item_id': item_id,
                'new_item': new_by_id[item_id]
            })

        # Compare common items
        common_ids = old_ids & new_ids
        for item_id in common_ids:
            old_item = old_by_id[item_id]
            new_item = new_by_id[item_id]

            # Compare key fields
            for field in ['title', 'sentiment_label', 'feed_id']:
                if field in old_item and field in new_item:
                    if old_item[field] != new_item[field]:
                        mismatches.append({
                            'type': 'field_mismatch',
                            'item_id': item_id,
                            'field': field,
                            'old_value': old_item[field],
                            'new_value': new_item[field]
                        })

        return mismatches

    def get_comparison_stats(self) -> Dict[str, Any]:
        """Get aggregated comparison statistics."""
        if not self.metrics:
            return {"message": "No comparisons recorded yet"}

        total = len(self.metrics)
        matches = sum(1 for m in self.metrics if m.result == ComparisonResult.MATCH)
        mismatches = sum(1 for m in self.metrics if m.result == ComparisonResult.MISMATCH)
        errors = sum(1 for m in self.metrics if m.result == ComparisonResult.ERROR)

        # Performance stats
        old_durations = [m.old_duration_ms for m in self.metrics if m.old_duration_ms > 0]
        new_durations = [m.new_duration_ms for m in self.metrics if m.new_duration_ms > 0]

        stats = {
            "total_comparisons": total,
            "match_rate": matches / total if total > 0 else 0,
            "mismatch_count": mismatches,
            "error_count": errors,
            "performance": {
                "old_avg_ms": sum(old_durations) / len(old_durations) if old_durations else 0,
                "new_avg_ms": sum(new_durations) / len(new_durations) if new_durations else 0,
                "old_95p_ms": self._percentile(old_durations, 95) if old_durations else 0,
                "new_95p_ms": self._percentile(new_durations, 95) if new_durations else 0,
            }
        }

        # Add recent mismatches for debugging
        recent_mismatches = [
            {
                "timestamp": m.timestamp.isoformat(),
                "details": m.mismatch_details
            }
            for m in self.metrics[-10:]  # Last 10
            if m.result == ComparisonResult.MISMATCH and m.mismatch_details
        ]

        if recent_mismatches:
            stats["recent_mismatches"] = recent_mismatches

        return stats

    def _percentile(self, data: List[float], p: int) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int((p / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    def reset_metrics(self):
        """Reset collected metrics."""
        self.metrics = []


# Global instance for application use
shadow_comparer = ShadowComparer(sample_rate=0.1)  # 10% sampling