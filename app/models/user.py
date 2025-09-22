"""User-related models for the News MCP application."""

from typing import Optional, Dict, Any

from .base import BaseTableModel


class UserSettings(BaseTableModel, table=True):
    """User settings for analysis parameters."""
    __tablename__ = "user_settings"

    # Analysis parameters
    default_limit: int = BaseTableModel.Field(default=200)
    default_rate_per_second: float = BaseTableModel.Field(default=1.0)
    default_model_tag: str = BaseTableModel.Field(default="gpt-4.1-nano")
    default_dry_run: bool = BaseTableModel.Field(default=False)
    default_override_existing: bool = BaseTableModel.Field(default=False)

    # Additional settings as JSON
    extra_settings: Optional[Dict[str, Any]] = BaseTableModel.Field(
        default=None,
        sa_column=BaseTableModel.Column(BaseTableModel.JSON)
    )

    # Single row constraint (only one settings record)
    user_id: str = BaseTableModel.Field(default="default", unique=True, index=True)