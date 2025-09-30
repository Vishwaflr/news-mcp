"""
Auto-Analysis Configuration Manager

Centralized configuration for auto-analysis system with persistence
"""

import json
import os
from typing import Dict, Any
from app.core.logging_config import get_logger

logger = get_logger(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "../../config/auto_analysis_config.json")
DEFAULT_CONFIG = {
    "max_runs_per_day": 50,  # Increased from 10
    "max_items_per_run": 100,  # Increased from 50
    "ai_model": "gpt-4.1-nano",
    "check_interval": 60,
    "rate_per_second": 2.0
}


class AutoAnalysisConfig:
    """Singleton configuration manager for auto-analysis settings"""

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.load_config()
        return cls._instance

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        try:
            # Try to load from file
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    self._config = json.load(f)
                logger.info(f"Loaded auto-analysis config from {CONFIG_FILE}")
            else:
                # Use defaults and save them
                self._config = DEFAULT_CONFIG.copy()
                self.save_config()
                logger.info("Created default auto-analysis config")
        except Exception as e:
            logger.error(f"Error loading config: {e}, using defaults")
            self._config = DEFAULT_CONFIG.copy()

        return self._config

    def save_config(self) -> bool:
        """Save current configuration to file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

            with open(CONFIG_FILE, 'w') as f:
                json.dump(self._config, f, indent=2)

            logger.info(f"Saved auto-analysis config to {CONFIG_FILE}")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        if self._config is None:
            self.load_config()
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        if self._config is None:
            self.load_config()
        self._config[key] = value

    def update(self, updates: Dict[str, Any]) -> bool:
        """Update multiple configuration values and save"""
        if self._config is None:
            self.load_config()

        self._config.update(updates)
        return self.save_config()

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        if self._config is None:
            self.load_config()
        return self._config.copy()

    @property
    def max_daily_runs(self) -> int:
        """Get max daily runs per feed"""
        return self.get("max_runs_per_day", DEFAULT_CONFIG["max_runs_per_day"])

    @property
    def max_items_per_run(self) -> int:
        """Get max items per run"""
        return self.get("max_items_per_run", DEFAULT_CONFIG["max_items_per_run"])

    @property
    def ai_model(self) -> str:
        """Get AI model for auto-analysis"""
        return self.get("ai_model", DEFAULT_CONFIG["ai_model"])

    @property
    def check_interval(self) -> int:
        """Get check interval in seconds"""
        return self.get("check_interval", DEFAULT_CONFIG["check_interval"])

    @property
    def rate_per_second(self) -> float:
        """Get rate limit per second"""
        return self.get("rate_per_second", DEFAULT_CONFIG["rate_per_second"])


# Global instance
auto_analysis_config = AutoAnalysisConfig()