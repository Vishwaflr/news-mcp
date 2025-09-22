"""Feature flag system for safe repository migration."""

import os
import json
import logging
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FeatureFlagStatus(Enum):
    OFF = "off"
    CANARY = "canary"  # Small percentage
    ON = "on"
    EMERGENCY_OFF = "emergency_off"  # Auto-disabled due to errors


class FeatureFlag:
    """Individual feature flag configuration."""

    def __init__(
        self,
        name: str,
        status: FeatureFlagStatus = FeatureFlagStatus.OFF,
        rollout_percentage: int = 0,
        emergency_threshold: float = 0.05,  # 5% error rate triggers emergency off
        emergency_latency_multiplier: float = 1.5  # 50% latency increase triggers emergency off
    ):
        self.name = name
        self.status = status
        self.rollout_percentage = rollout_percentage
        self.emergency_threshold = emergency_threshold
        self.emergency_latency_multiplier = emergency_latency_multiplier
        self.error_count = 0
        self.success_count = 0
        self.emergency_disabled_at: Optional[datetime] = None
        self.baseline_latency: Optional[float] = None
        self.current_latency: Optional[float] = None

    def is_enabled(self, user_id: Optional[str] = None) -> bool:
        """Check if flag is enabled for given context."""
        if self.status == FeatureFlagStatus.EMERGENCY_OFF:
            return False

        if self.status == FeatureFlagStatus.OFF:
            return False

        if self.status == FeatureFlagStatus.ON:
            return True

        if self.status == FeatureFlagStatus.CANARY:
            # Use deterministic hash for consistent user experience
            if user_id:
                import hashlib
                hash_val = int(hashlib.md5(f"{self.name}:{user_id}".encode()).hexdigest()[:8], 16)
                return (hash_val % 100) < self.rollout_percentage
            else:
                # Random rollout for anonymous users
                import random
                return random.randint(1, 100) <= self.rollout_percentage

        return False

    def record_success(self, latency_ms: Optional[float] = None):
        """Record successful execution."""
        self.success_count += 1
        if latency_ms:
            self.current_latency = latency_ms

    def record_error(self):
        """Record error and check emergency thresholds."""
        self.error_count += 1
        self._check_emergency_conditions()

    def _check_emergency_conditions(self):
        """Check if emergency disable conditions are met."""
        total_requests = self.success_count + self.error_count

        if total_requests >= 100:  # Minimum sample size
            error_rate = self.error_count / total_requests

            # Check error rate threshold
            if error_rate > self.emergency_threshold:
                logger.error(
                    f"Emergency disabling flag {self.name}: "
                    f"error rate {error_rate:.2%} > threshold {self.emergency_threshold:.2%}"
                )
                self._emergency_disable("high_error_rate")

            # Check latency threshold
            if (self.baseline_latency and self.current_latency and
                self.current_latency > self.baseline_latency * self.emergency_latency_multiplier):
                logger.error(
                    f"Emergency disabling flag {self.name}: "
                    f"latency {self.current_latency:.1f}ms > {self.baseline_latency * self.emergency_latency_multiplier:.1f}ms"
                )
                self._emergency_disable("high_latency")

    def _emergency_disable(self, reason: str):
        """Emergency disable the flag."""
        self.status = FeatureFlagStatus.EMERGENCY_OFF
        self.emergency_disabled_at = datetime.utcnow()
        logger.critical(f"Feature flag {self.name} emergency disabled: {reason}")

    def reset_metrics(self):
        """Reset error/success counters."""
        self.error_count = 0
        self.success_count = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "status": self.status.value,
            "rollout_percentage": self.rollout_percentage,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "emergency_disabled_at": self.emergency_disabled_at.isoformat() if self.emergency_disabled_at else None,
            "baseline_latency": self.baseline_latency,
            "current_latency": self.current_latency
        }


class FeatureFlagManager:
    """Central feature flag manager."""

    def __init__(self):
        self.flags: Dict[str, FeatureFlag] = {}
        self._load_flags()

    def _load_flags(self):
        """Load flags from environment or config file."""
        # Try to load from environment variable
        flags_json = os.getenv("FEATURE_FLAGS_JSON")
        if flags_json:
            try:
                config = json.loads(flags_json)
                self._load_from_config(config)
                return
            except json.JSONDecodeError:
                logger.error("Invalid FEATURE_FLAGS_JSON format")

        # Load default flags
        self._load_defaults()

    def _load_defaults(self):
        """Load default feature flags."""
        self.flags = {
            "items_repo": FeatureFlag(
                name="items_repo",
                status=FeatureFlagStatus.OFF,
                rollout_percentage=10,
                emergency_threshold=0.05,
                emergency_latency_multiplier=1.3
            ),
            "feeds_repo": FeatureFlag(
                name="feeds_repo",
                status=FeatureFlagStatus.OFF,
                rollout_percentage=5
            ),
            "analysis_repo": FeatureFlag(
                name="analysis_repo",
                status=FeatureFlagStatus.OFF,
                rollout_percentage=15
            ),
            "shadow_compare": FeatureFlag(
                name="shadow_compare",
                status=FeatureFlagStatus.CANARY,
                rollout_percentage=10
            )
        }

    def _load_from_config(self, config: Dict[str, Any]):
        """Load flags from configuration dictionary."""
        for flag_name, flag_config in config.items():
            status = FeatureFlagStatus(flag_config.get("status", "off"))
            self.flags[flag_name] = FeatureFlag(
                name=flag_name,
                status=status,
                rollout_percentage=flag_config.get("rollout_percentage", 0),
                emergency_threshold=flag_config.get("emergency_threshold", 0.05),
                emergency_latency_multiplier=flag_config.get("emergency_latency_multiplier", 1.5)
            )

    def is_enabled(self, flag_name: str, user_id: Optional[str] = None) -> bool:
        """Check if a feature flag is enabled."""
        flag = self.flags.get(flag_name)
        if not flag:
            logger.warning(f"Unknown feature flag: {flag_name}")
            return False

        return flag.is_enabled(user_id)

    def record_success(self, flag_name: str, latency_ms: Optional[float] = None):
        """Record successful execution for a flag."""
        flag = self.flags.get(flag_name)
        if flag:
            flag.record_success(latency_ms)

    def record_error(self, flag_name: str):
        """Record error for a flag."""
        flag = self.flags.get(flag_name)
        if flag:
            flag.record_error()

    def set_flag_status(self, flag_name: str, status: FeatureFlagStatus, rollout_percentage: Optional[int] = None):
        """Manually set flag status (for admin control)."""
        flag = self.flags.get(flag_name)
        if flag:
            flag.status = status
            if rollout_percentage is not None:
                flag.rollout_percentage = rollout_percentage
            logger.info(f"Flag {flag_name} set to {status.value} with {rollout_percentage or flag.rollout_percentage}% rollout")

    def set_baseline_latency(self, flag_name: str, latency_ms: float):
        """Set baseline latency for emergency detection."""
        flag = self.flags.get(flag_name)
        if flag:
            flag.baseline_latency = latency_ms

    def get_flag_status(self, flag_name: str) -> Optional[Dict[str, Any]]:
        """Get current flag status and metrics."""
        flag = self.flags.get(flag_name)
        return flag.to_dict() if flag else None

    def get_all_flags(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all flags."""
        return {name: flag.to_dict() for name, flag in self.flags.items()}

    def reset_flag_metrics(self, flag_name: str):
        """Reset metrics for a specific flag."""
        flag = self.flags.get(flag_name)
        if flag:
            flag.reset_metrics()


# Global feature flag manager
feature_flags = FeatureFlagManager()


def is_feature_enabled(flag_name: str, user_id: Optional[str] = None) -> bool:
    """Convenience function to check if feature is enabled."""
    return feature_flags.is_enabled(flag_name, user_id)


def record_feature_success(flag_name: str, latency_ms: Optional[float] = None):
    """Convenience function to record feature success."""
    feature_flags.record_success(flag_name, latency_ms)


def record_feature_error(flag_name: str):
    """Convenience function to record feature error."""
    feature_flags.record_error(flag_name)