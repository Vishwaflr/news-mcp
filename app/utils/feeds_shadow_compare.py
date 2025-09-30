"""Shadow comparison for Feeds operations during repository migration."""

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


class FeedsShadowComparer:
    """
    Compares legacy feeds operations with repository-based ones.
    Used during the FeedsRepo cutover to validate consistency.
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
        logger.info(f"Feeds shadow comparison enabled with {sample_rate*100}% sample rate")

    def disable(self):
        """Disable shadow comparison."""
        self.enabled = False
        logger.info("Feeds shadow comparison disabled")

    def should_sample(self) -> bool:
        """Determine if this operation should be sampled."""
        if not self.enabled:
            return False
        return hash(time.time()) % 100 < (self.sample_rate * 100)

    def compare_feed_list(self,
                         filters: Dict[str, Any],
                         legacy_result: List[Any],
                         repo_result: List[Any]) -> bool:
        """
        Compare legacy feed list with repository feed list.

        Args:
            filters: Query filters applied (active, limit, etc.)
            legacy_result: List of feeds from legacy SQL
            repo_result: List of feeds from repository

        Returns:
            True if results match, False otherwise
        """
        if not self.should_sample():
            return True

        comparison = {
            "timestamp": datetime.now().isoformat(),
            "operation": "feed_list",
            "filters_hash": self._hash_dict(filters),
            "legacy_count": len(legacy_result) if legacy_result else 0,
            "repo_count": len(repo_result) if repo_result else 0,
            "legacy_result": self._serialize_feed_list(legacy_result),
            "repo_result": self._serialize_feed_list(repo_result),
            "match": False,
            "differences": []
        }

        try:
            # Compare the results
            match, differences = self._compare_feed_lists(legacy_result, repo_result)

            comparison["match"] = match
            comparison["differences"] = differences

            with self.lock:
                self.comparisons.append(comparison)
                self.stats["total_comparisons"] += 1
                if match:
                    self.stats["matches"] += 1
                else:
                    self.stats["mismatches"] += 1
                    logger.warning(f"Feed list mismatch: {differences}")

            return match

        except Exception as e:
            logger.error(f"Error in feed list comparison: {e}")
            comparison["error"] = str(e)
            with self.lock:
                self.comparisons.append(comparison)
                self.stats["errors"] += 1
            return False

    def compare_feed_details(self,
                           feed_id: int,
                           legacy_result: Any,
                           repo_result: Any) -> bool:
        """
        Compare legacy feed details with repository feed details.

        Args:
            feed_id: The feed ID being queried
            legacy_result: Feed details from legacy SQL
            repo_result: Feed details from repository

        Returns:
            True if results match, False otherwise
        """
        if not self.should_sample():
            return True

        comparison = {
            "timestamp": datetime.now().isoformat(),
            "operation": "feed_details",
            "feed_id": feed_id,
            "legacy_result": self._serialize_result(legacy_result),
            "repo_result": self._serialize_result(repo_result),
            "match": False,
            "differences": []
        }

        try:
            # Compare the results
            match, differences = self._compare_feed_details(legacy_result, repo_result)

            comparison["match"] = match
            comparison["differences"] = differences

            with self.lock:
                self.comparisons.append(comparison)
                self.stats["total_comparisons"] += 1
                if match:
                    self.stats["matches"] += 1
                else:
                    self.stats["mismatches"] += 1
                    logger.warning(f"Feed details mismatch for feed {feed_id}: {differences}")

            return match

        except Exception as e:
            logger.error(f"Error in feed details comparison: {e}")
            comparison["error"] = str(e)
            with self.lock:
                self.comparisons.append(comparison)
                self.stats["errors"] += 1
            return False

    def compare_feed_health(self,
                          feed_id: int,
                          legacy_result: Any,
                          repo_result: Any) -> bool:
        """
        Compare legacy feed health with repository feed health.

        Args:
            feed_id: The feed ID being queried
            legacy_result: Health data from legacy SQL
            repo_result: Health data from repository

        Returns:
            True if results match, False otherwise
        """
        if not self.should_sample():
            return True

        comparison = {
            "timestamp": datetime.now().isoformat(),
            "operation": "feed_health",
            "feed_id": feed_id,
            "legacy_result": self._serialize_result(legacy_result),
            "repo_result": self._serialize_result(repo_result),
            "match": False,
            "differences": []
        }

        try:
            # Compare the results
            match, differences = self._compare_health_results(legacy_result, repo_result)

            comparison["match"] = match
            comparison["differences"] = differences

            with self.lock:
                self.comparisons.append(comparison)
                self.stats["total_comparisons"] += 1
                if match:
                    self.stats["matches"] += 1
                else:
                    self.stats["mismatches"] += 1
                    logger.warning(f"Feed health mismatch for feed {feed_id}: {differences}")

            return match

        except Exception as e:
            logger.error(f"Error in feed health comparison: {e}")
            comparison["error"] = str(e)
            with self.lock:
                self.comparisons.append(comparison)
                self.stats["errors"] += 1
            return False

    def compare_feed_crud(self,
                         operation: str,
                         feed_data: Dict[str, Any],
                         legacy_result: Any,
                         repo_result: Any) -> bool:
        """
        Compare legacy CRUD operations with repository CRUD operations.

        Args:
            operation: CRUD operation (create, update, delete)
            feed_data: Feed data being operated on
            legacy_result: Result from legacy SQL operation
            repo_result: Result from repository operation

        Returns:
            True if results match, False otherwise
        """
        if not self.should_sample():
            return True

        comparison = {
            "timestamp": datetime.now().isoformat(),
            "operation": f"feed_crud_{operation}",
            "feed_data_hash": self._hash_dict(feed_data),
            "legacy_result": self._serialize_result(legacy_result),
            "repo_result": self._serialize_result(repo_result),
            "match": False,
            "differences": []
        }

        try:
            # Compare the results
            match, differences = self._compare_crud_results(operation, legacy_result, repo_result)

            comparison["match"] = match
            comparison["differences"] = differences

            with self.lock:
                self.comparisons.append(comparison)
                self.stats["total_comparisons"] += 1
                if match:
                    self.stats["matches"] += 1
                else:
                    self.stats["mismatches"] += 1
                    logger.warning(f"Feed CRUD {operation} mismatch: {differences}")

            return match

        except Exception as e:
            logger.error(f"Error in feed CRUD comparison: {e}")
            comparison["error"] = str(e)
            with self.lock:
                self.comparisons.append(comparison)
                self.stats["errors"] += 1
            return False

    def _compare_feed_lists(self, legacy: List[Any], repo: List[Any]) -> Tuple[bool, List[str]]:
        """Compare feed list results."""
        differences = []

        # Compare counts
        if len(legacy) != len(repo):
            differences.append(f"Count mismatch: legacy={len(legacy)}, repo={len(repo)}")

        # Compare individual feeds (up to first 10 for performance)
        min_length = min(len(legacy), len(repo), 10)
        for i in range(min_length):
            legacy_feed = legacy[i]
            repo_feed = repo[i]

            # Compare key fields
            legacy_dict = self._serialize_result(legacy_feed)
            repo_dict = self._serialize_result(repo_feed)

            key_fields = ['id', 'url', 'title', 'active', 'fetch_interval_minutes']
            for field in key_fields:
                if field in legacy_dict and field in repo_dict:
                    if legacy_dict[field] != repo_dict[field]:
                        differences.append(f"Feed {i} field {field}: legacy={legacy_dict[field]}, repo={repo_dict[field]}")

        return len(differences) == 0, differences

    def _compare_feed_details(self, legacy: Any, repo: Any) -> Tuple[bool, List[str]]:
        """Compare feed details results."""
        differences = []

        # Handle None cases
        if legacy is None and repo is None:
            return True, []

        if (legacy is None) != (repo is None):
            differences.append(f"Null mismatch: legacy={legacy}, repo={repo}")
            return False, differences

        # Compare feed data
        legacy_dict = self._serialize_result(legacy)
        repo_dict = self._serialize_result(repo)

        # Compare all important fields
        key_fields = ['id', 'url', 'title', 'description', 'active', 'fetch_interval_minutes',
                     'created_at', 'updated_at', 'last_fetch_at', 'last_fetch_status']

        for field in key_fields:
            if field in legacy_dict and field in repo_dict:
                legacy_val = legacy_dict[field]
                repo_val = repo_dict[field]

                # Handle datetime comparisons (allow small differences)
                if field.endswith('_at') and legacy_val and repo_val:
                    try:
                        if isinstance(legacy_val, str):
                            legacy_dt = datetime.fromisoformat(legacy_val.replace('Z', '+00:00'))
                        else:
                            legacy_dt = legacy_val

                        if isinstance(repo_val, str):
                            repo_dt = datetime.fromisoformat(repo_val.replace('Z', '+00:00'))
                        else:
                            repo_dt = repo_val

                        # Allow 1 second difference for datetime fields
                        if abs((legacy_dt - repo_dt).total_seconds()) > 1:
                            differences.append(f"Field {field}: legacy={legacy_val}, repo={repo_val}")
                    except (ValueError, AttributeError, TypeError) as e:
                        # If datetime parsing fails, compare as strings
                        if str(legacy_val) != str(repo_val):
                            differences.append(f"Field {field}: legacy={legacy_val}, repo={repo_val}")
                else:
                    if legacy_val != repo_val:
                        differences.append(f"Field {field}: legacy={legacy_val}, repo={repo_val}")

        return len(differences) == 0, differences

    def _compare_health_results(self, legacy: Any, repo: Any) -> Tuple[bool, List[str]]:
        """Compare health query results."""
        differences = []

        # Handle None cases
        if legacy is None and repo is None:
            return True, []

        if (legacy is None) != (repo is None):
            differences.append(f"Null mismatch: legacy={legacy}, repo={repo}")
            return False, differences

        # Compare health data
        legacy_dict = self._serialize_result(legacy)
        repo_dict = self._serialize_result(repo)

        # Compare key health fields
        key_fields = ['status', 'success_rate', 'last_success_at', 'last_failure_at',
                     'total_fetches', 'successful_fetches', 'failed_fetches']

        for field in key_fields:
            if field in legacy_dict and field in repo_dict:
                legacy_val = legacy_dict[field]
                repo_val = repo_dict[field]

                # Handle numeric fields with tolerance
                if field in ['success_rate'] and isinstance(legacy_val, (int, float)) and isinstance(repo_val, (int, float)):
                    if abs(legacy_val - repo_val) > 0.01:  # 1% tolerance
                        differences.append(f"Field {field}: legacy={legacy_val}, repo={repo_val}")
                elif field.endswith('_fetches') and isinstance(legacy_val, int) and isinstance(repo_val, int):
                    # Allow small differences in counts due to timing
                    if abs(legacy_val - repo_val) > 1:
                        differences.append(f"Field {field}: legacy={legacy_val}, repo={repo_val}")
                else:
                    if legacy_val != repo_val:
                        differences.append(f"Field {field}: legacy={legacy_val}, repo={repo_val}")

        return len(differences) == 0, differences

    def _compare_crud_results(self, operation: str, legacy: Any, repo: Any) -> Tuple[bool, List[str]]:
        """Compare CRUD operation results."""
        differences = []

        if operation == "create":
            # For create operations, both should return the created feed
            if legacy is None or repo is None:
                differences.append(f"Create failed: legacy={legacy}, repo={repo}")
            else:
                # Compare created feed IDs and key fields
                legacy_dict = self._serialize_result(legacy)
                repo_dict = self._serialize_result(repo)

                # ID might be different, but other fields should match
                compare_fields = ['url', 'title', 'description', 'active', 'fetch_interval_minutes']
                for field in compare_fields:
                    if field in legacy_dict and field in repo_dict:
                        if legacy_dict[field] != repo_dict[field]:
                            differences.append(f"Created feed {field}: legacy={legacy_dict[field]}, repo={repo_dict[field]}")

        elif operation == "update":
            # For updates, compare the updated result
            if (legacy is None) != (repo is None):
                differences.append(f"Update result mismatch: legacy={legacy}, repo={repo}")
            elif legacy is not None and repo is not None:
                # Compare updated fields
                match, field_diffs = self._compare_feed_details(legacy, repo)
                differences.extend(field_diffs)

        elif operation == "delete":
            # For deletes, both should return success/failure indication
            legacy_success = legacy is not None
            repo_success = repo is not None

            if legacy_success != repo_success:
                differences.append(f"Delete success mismatch: legacy={legacy_success}, repo={repo_success}")

        return len(differences) == 0, differences

    def _serialize_feed_list(self, feed_list: List[Any]) -> List[Dict[str, Any]]:
        """Serialize feed list for comparison."""
        if not feed_list:
            return []

        return [self._serialize_result(feed) for feed in feed_list[:10]]  # Limit to first 10

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

        # Handle datetime objects
        if hasattr(result, 'isoformat'):
            return result.isoformat()

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
        logger.info("Feeds shadow comparison metrics reset")

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
feeds_shadow_comparer = FeedsShadowComparer()