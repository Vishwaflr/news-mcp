"""Models package for the News MCP application."""

# Import base classes and enums
from .base import (
    BaseModel,
    BaseTableModel,
    SourceType,
    FeedStatus,
    ProcessorType,
    ProcessingStatus,
)

# Import core models
from .core import (
    Feed,
    Item,
    FetchLog,
)

# Import feed-related models
from .feeds import (
    Source,
    Category,
    FeedType,
    FeedCategory,
    FeedHealth,
)

# Import content-related models
from .content import (
    ItemTag,
    ContentProcessingLog,
)

# Import processor-related models
from .processors import (
    FeedProcessorConfig,
    ProcessorTemplate,
    DynamicFeedTemplate,
)

# Import configuration-related models
from .configuration import (
    FeedTemplateAssignment,
    FeedConfigurationChange,
    FeedSchedulerState,
)

# Import user-related models
from .user import (
    UserSettings,
)

# Export all models
__all__ = [
    # Base classes and enums
    "BaseModel",
    "BaseTableModel",
    "SourceType",
    "FeedStatus",
    "ProcessorType",
    "ProcessingStatus",

    # Core models
    "Feed",
    "FetchLog",
    "Item",

    # Feed models
    "Source",
    "Category",
    "FeedType",
    "FeedCategory",
    "FeedHealth",

    # Content models
    "ItemTag",
    "ContentProcessingLog",

    # Processor models
    "FeedProcessorConfig",
    "ProcessorTemplate",
    "DynamicFeedTemplate",

    # Configuration models
    "FeedTemplateAssignment",
    "FeedConfigurationChange",
    "FeedSchedulerState",

    # User models
    "UserSettings",
]