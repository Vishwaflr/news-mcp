"""Shadow comparison for Analysis operations during repository migration."""

import json
import time
from app.core.logging_config import get_logger
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock

from app.db.session import db_session

logger = get_logger(__name__)


class AnalysisShadowComparer:
    """
    Compares legacy analysis operations with repository-based ones.
    Used during the AnalysisRepo cutover to validate consistency.
    """

    def __init__(self, sample_rate: float = 0.1):
        self.sample_rate = sample_rate
        self.comparisons: List[Dict[str, Any]] = []
        self.stats = defaultdict(int)
        self.lock = Lock()
        self.enabled = False

    def enable(self, sample_rate: float = 0.1):
        """Enable shadow comparison with specified sample rate."""
        self.sample_rate = sample_rate
        self.enabled = True
        logger.info(f"Analysis shadow comparison enabled with {sample_rate*100}% sample rate")

    def disable(self):
        """Disable shadow comparison."""
        self.enabled = False
        logger.info("Analysis shadow comparison disabled")

    def should_sample(self) -> bool:
        """Determine if this operation should be sampled."""
        if not self.enabled:
            return False
        return hash(time.time()) % 100 < (self.sample_rate * 100)

    def compare_analysis_upsert(self,
                               item_id: str,
                               analysis_data: Dict[str, Any],
                               legacy_result: Any,
                               repo_result: Any) -> bool:
        """
        Compare legacy analysis upsert with repository upsert.

        Args:
            item_id: The item ID being analyzed
            analysis_data: The analysis data being upserted
            legacy_result: Result from legacy SQL operation
            repo_result: Result from repository operation

        Returns:
            True if results match, False otherwise
        """
        if not self.should_sample():
            return True

        comparison = {
            "timestamp": datetime.now().isoformat(),
            "operation": "analysis_upsert",
            "item_id": item_id,
            "analysis_data_hash": self._hash_dict(analysis_data),
            "legacy_result": self._serialize_result(legacy_result),
            "repo_result": self._serialize_result(repo_result),
            "match": False,
            "differences": []
        }

        try:
            # Compare the results
            match, differences = self._compare_upsert_results(legacy_result, repo_result)

            comparison["match"] = match
            comparison["differences"] = differences

            with self.lock:
                self.comparisons.append(comparison)
                self.stats["total_comparisons"] += 1
                if match:
                    self.stats["matches"] += 1
                else:
                    self.stats["mismatches"] += 1
                    logger.warning(f"Analysis upsert mismatch for item {item_id}: {differences}")

            return match

        except Exception as e:
            logger.error(f"Error in analysis upsert comparison: {e}")
            comparison["error"] = str(e)
            with self.lock:
                self.comparisons.append(comparison)
                self.stats["errors"] += 1
            return False

    def compare_analysis_get(self,
                           item_id: str,
                           legacy_result: Any,
                           repo_result: Any) -> bool:
        """
        Compare legacy analysis get with repository get.

        Args:
            item_id: The item ID being queried
            legacy_result: Result from legacy SQL query
            repo_result: Result from repository query

        Returns:
            True if results match, False otherwise
        """
        if not self.should_sample():
            return True

        comparison = {
            "timestamp": datetime.now().isoformat(),
            "operation": "analysis_get",
            "item_id": item_id,
            "legacy_result": self._serialize_result(legacy_result),
            "repo_result": self._serialize_result(repo_result),
            "match": False,
            "differences": []
        }

        try:
            # Compare the results
            match, differences = self._compare_get_results(legacy_result, repo_result)

            comparison["match"] = match
            comparison["differences"] = differences

            with self.lock:
                self.comparisons.append(comparison)
                self.stats["total_comparisons"] += 1
                if match:
                    self.stats["matches"] += 1
                else:
                    self.stats["mismatches"] += 1
                    logger.warning(f"Analysis get mismatch for item {item_id}: {differences}")

            return match

        except Exception as e:
            logger.error(f"Error in analysis get comparison: {e}")
            comparison["error"] = str(e)
            with self.lock:
                self.comparisons.append(comparison)
                self.stats["errors"] += 1
            return False

    def compare_aggregation_query(self,
                                 query_type: str,
                                 filters: Dict[str, Any],
                                 legacy_result: Any,
                                 repo_result: Any) -> bool:
        """
        Compare legacy aggregation queries with repository aggregations.

        Args:
            query_type: Type of aggregation (sentiment_counts, impact_stats, etc.)
            filters: Query filters applied
            legacy_result: Result from legacy SQL aggregation
            repo_result: Result from repository aggregation

        Returns:
            True if results match, False otherwise
        """
        if not self.should_sample():
            return True

        comparison = {
            "timestamp": datetime.now().isoformat(),
            "operation": f"aggregation_{query_type}",
            "filters_hash": self._hash_dict(filters),
            "legacy_result": self._serialize_result(legacy_result),
            "repo_result": self._serialize_result(repo_result),
            "match": False,
            "differences": []
        }

        try:
            # Compare the results
            match, differences = self._compare_aggregation_results(legacy_result, repo_result)

            comparison["match"] = match
            comparison["differences"] = differences

            with self.lock:
                self.comparisons.append(comparison)
                self.stats["total_comparisons"] += 1
                if match:
                    self.stats["matches"] += 1
                else:
                    self.stats["mismatches"] += 1
                    logger.warning(f"Aggregation {query_type} mismatch: {differences}")

            return match

        except Exception as e:
            logger.error(f"Error in aggregation comparison: {e}")
            comparison["error"] = str(e)
            with self.lock:
                self.comparisons.append(comparison)
                self.stats["errors"] += 1
            return False

    def _compare_upsert_results(self, legacy: Any, repo: Any) -> Tuple[bool, List[str]]:
        """Compare upsert operation results."""
        differences = []

        # For upserts, we mainly care that both succeeded or both failed
        legacy_success = legacy is not None
        repo_success = repo is not None

        if legacy_success != repo_success:
            differences.append(f"Success mismatch: legacy={legacy_success}, repo={repo_success}")

        # If both succeeded, compare the returned data if available
        if legacy_success and repo_success:
            if hasattr(legacy, '_asdict') and hasattr(repo, '_asdict'):
                legacy_dict = legacy._asdict()
                repo_dict = repo._asdict()

                for key in legacy_dict:
                    if key in repo_dict:
                        if legacy_dict[key] != repo_dict[key]:
                            differences.append(f"Field {key}: legacy={legacy_dict[key]}, repo={repo_dict[key]}")
                    else:
                        differences.append(f"Missing field in repo: {key}")

        return len(differences) == 0, differences

    def _compare_get_results(self, legacy: Any, repo: Any) -> Tuple[bool, List[str]]:
        """Compare get operation results."""
        differences = []

        # Handle None cases
        if legacy is None and repo is None:
            return True, []

        if (legacy is None) != (repo is None):
            differences.append(f"Null mismatch: legacy={legacy}, repo={repo}")
            return False, differences

        # Compare actual data
        if hasattr(legacy, '_asdict') and hasattr(repo, '_asdict'):
            legacy_dict = legacy._asdict()
            repo_dict = repo._asdict()

            # Compare key fields
            key_fields = ['item_id', 'sentiment_label', 'sentiment_score', 'impact_score']
            for field in key_fields:
                if field in legacy_dict and field in repo_dict:
                    legacy_val = legacy_dict[field]
                    repo_val = repo_dict[field]

                    # Handle float comparisons with tolerance
                    if isinstance(legacy_val, float) and isinstance(repo_val, float):
                        if abs(legacy_val - repo_val) > 0.001:
                            differences.append(f"Field {field}: legacy={legacy_val}, repo={repo_val}")
                    elif legacy_val != repo_val:
                        differences.append(f"Field {field}: legacy={legacy_val}, repo={repo_val}")

        return len(differences) == 0, differences

    def _compare_aggregation_results(self, legacy: Any, repo: Any) -> Tuple[bool, List[str]]:
        """Compare aggregation query results."""
        differences = []

        # Convert to comparable format
        legacy_data = self._normalize_aggregation_result(legacy)
        repo_data = self._normalize_aggregation_result(repo)

        # Compare counts with tolerance
        for key in legacy_data:
            if key in repo_data:
                legacy_val = legacy_data[key]
                repo_val = repo_data[key]

                if isinstance(legacy_val, (int, float)) and isinstance(repo_val, (int, float)):
                    # Allow small differences in aggregations due to timing
                    tolerance = max(1, abs(legacy_val) * 0.01)  # 1% tolerance or 1, whichever is larger
                    if abs(legacy_val - repo_val) > tolerance:
                        differences.append(f"Count {key}: legacy={legacy_val}, repo={repo_val}")
                else:
                    if legacy_val != repo_val:
                        differences.append(f"Value {key}: legacy={legacy_val}, repo={repo_val}")
            else:
                differences.append(f"Missing key in repo: {key}")

        return len(differences) == 0, differences

    def _normalize_aggregation_result(self, result: Any) -> Dict[str, Any]:
        """Normalize aggregation result to comparable dict."""
        if result is None:
            return {}

        if isinstance(result, dict):
            return result

        if hasattr(result, '_asdict'):
            return result._asdict()

        if hasattr(result, '__dict__'):
            return result.__dict__

        # Handle list of results
        if isinstance(result, list):
            normalized = {}
            for i, item in enumerate(result):
                if hasattr(item, '_asdict'):
                    item_dict = item._asdict()
                    # Use first column as key if possible
                    if len(item_dict) >= 2:
                        keys = list(item_dict.keys())
                        normalized[item_dict[keys[0]]] = item_dict[keys[1]]
                    else:
                        normalized[f"item_{i}"] = item_dict
                else:
                    normalized[f"item_{i}"] = item
            return normalized

        return {"value": result}

    def _hash_dict(self, data: Dict[str, Any]) -> str:
        """Create hash of dictionary for comparison purposes."""
        try:
            serialized = json.dumps(data, sort_keys=True, default=str)
            return hashlib.md5(serialized.encode()).hexdigest()
        except Exception:
            return "hash_error"

    def _serialize_result(self, result: Any) -> Any:
        """Serialize result for storage and comparison."""
        if result is None:
            return None

        if hasattr(result, '_asdict'):
            return result._asdict()

        if hasattr(result, '__dict__'):
            return {k: v for k, v in result.__dict__.items() if not k.startswith('_')}

        if isinstance(result, (list, tuple)):
            return [self._serialize_result(item) for item in result]

        if isinstance(result, (str, int, float, bool)):
            return result

        return str(result)

    def get_comparison_stats(self) -> Dict[str, Any]:
        """Get current comparison statistics."""
        with self.lock:
            total = self.stats["total_comparisons"]
            matches = self.stats["matches"]
            mismatches = self.stats["mismatches"]
            errors = self.stats["errors"]

            match_rate = matches / total if total > 0 else 0

            return {
                "enabled": self.enabled,
                "sample_rate": self.sample_rate,
                "total_comparisons": total,
                "matches": matches,
                "mismatches": mismatches,
                "errors": errors,
                "match_rate": round(match_rate, 4),
                "recent_comparisons": len([c for c in self.comparisons if
                                         datetime.fromisoformat(c["timestamp"]) > datetime.now() - timedelta(hours=1)])
            }

    def get_recent_mismatches(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get recent mismatches for debugging."""
        cutoff = datetime.now() - timedelta(hours=hours)

        with self.lock:
            return [c for c in self.comparisons
                   if not c.get("match", True) and
                   datetime.fromisoformat(c["timestamp"]) > cutoff]

    def reset_metrics(self):
        """Reset all comparison metrics."""
        with self.lock:
            self.comparisons.clear()
            self.stats.clear()
        logger.info("Analysis shadow comparison metrics reset")

    def export_comparison_data(self, hours: int = 24) -> Dict[str, Any]:
        """Export comparison data for analysis."""
        cutoff = datetime.now() - timedelta(hours=hours)

        with self.lock:
            recent_comparisons = [c for c in self.comparisons
                                if datetime.fromisoformat(c["timestamp"]) > cutoff]

            return {
                "export_timestamp": datetime.now().isoformat(),
                "export_period_hours": hours,
                "total_comparisons": len(recent_comparisons),
                "summary_stats": self.get_comparison_stats(),
                "comparisons": recent_comparisons
            }


# Global instance
analysis_shadow_comparer = AnalysisShadowComparer()