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

# Import analysis-related models (for metadata registration)
from .analysis import (
    ItemAnalysis,
    AnalysisRun,
    AnalysisRunItem,
    AnalysisPreset,
)

# Import auto-analysis models
from .auto_analysis import (
    PendingAutoAnalysis,
)

# Import content distribution models
from .content_distribution import (
    SpecialReport,
    GeneratedContent,
    DistributionChannel,
    DistributionLog,
    PendingContentGeneration,
)

# Import queue models
from .run_queue import (
    QueuedRun,
)

# Import feed limits and metrics
from .feed_limits import (
    FeedLimit,
    FeedViolation,
)

from .feed_metrics import (
    FeedMetrics,
    QueueMetrics,
)

# Import research models
from .research import (
    ResearchTemplate,
    ResearchRun,
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

    # Analysis models
    "ItemAnalysis",
    "AnalysisRun",
    "AnalysisRunItem",
    "AnalysisPreset",

    # Auto-analysis models
    "PendingAutoAnalysis",

    # Content distribution models
    "SpecialReport",
    "GeneratedContent",
    "DistributionChannel",
    "DistributionLog",
    "PendingContentGeneration",

    # Queue models
    "QueuedRun",
    "QueueMetrics",

    # Feed limits and metrics
    "FeedLimit",
    "FeedViolation",
    "FeedMetrics",

    # Research models
    "ResearchTemplate",
    "ResearchRun",
]