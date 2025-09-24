# Analysis Control Interface Documentation

**Version:** 3.3 - Articles Integration & Dark Mode
**Last Updated:** September 2025
**Status:** ✅ Production Ready with Live Article Integration

## Overview

The Analysis Control Interface serves as the central command center for managing AI-powered sentiment and impact analysis across the News MCP application. This interface has undergone a complete redesign implementing modern UI patterns and improved user experience.

## Recent Major Changes (v3.3)

### 🔄 Articles Integration & Live Updates

#### Complete Interface Integration
- **Revolutionary Change:** Combined Articles and Analysis interfaces into single integrated experience
- **Layout:** Horizontal statistics above two-column layout (Target Selection + Live Articles)
- **Real-time Updates:** Article list updates instantly when analysis targets change
- **Benefits:** Seamless workflow from target selection to content analysis

#### Live Article Selection System
- **Target Selection:** Radio-based selection with SET buttons for immediate activation
- **Live Updates:** Articles panel refreshes automatically when targets change
- **Options Available:**
  - **Latest Articles:** Configurable count (1-500) with instant article display
  - **All Articles:** Shows complete unanalyzed article set
  - **Feed Selection:** Dynamic dropdown with live feed counts
  - **Date Range:** Precise date filtering with article preview
- **Clear Selection:** Reset button returns to showing all articles

#### Horizontal Statistics Dashboard
- **Compact Layout:** Six metric cards displayed horizontally above content
- **Auto-refresh:** Statistics update every 30 seconds automatically
- **Dark Mode Optimized:** All text now properly visible with `text-light` labels
- **Metrics:** Total Items, Analyzed, Pending, Active Feeds, 24h New, Coverage percentage

#### Model Selection with Pricing
- **Complete Model List:** All available GPT models with real-time pricing
- **Featured Models:** GPT-4.1-nano ($0.20/$0.80), GPT-4o-mini ($0.25/$1.00), GPT-5-mini ($0.45/$3.60)
- **Default Selection:** GPT-4.1-nano selected for cost optimization
- **Price Display:** Input/output costs shown directly in dropdown options

#### Navigation Integration
- **Main Navbar:** Analysis accessible via brain icon in main navigation
- **Consistent UI:** Analysis page now includes full site navigation
- **Mobile Support:** Responsive navigation with hamburger menu
- **Smart Display:** Truncated titles for better UX
- **Item Counts:** Shows analyzed vs unanalyzed items per feed

#### Preview System
- **Real-time Calculation:** Updates automatically based on selection
- **Comprehensive Display:**
  - Total items in selection
  - Already analyzed items
  - Items to be analyzed
  - Estimated cost and duration
- **Smart Logic:** Respects existing analysis and override settings

## Technical Implementation

### Architecture Stack

#### Frontend Technologies
- **Alpine.js**: Reactive state management for dynamic UI components
- **HTMX**: Server-side rendering with partial updates
- **Bootstrap 5**: Modern card-based layout system
- **Custom CSS**: NMC design system integration

#### Backend Integration
- **FastAPI Router**: `/htmx/analysis` endpoint group
- **Templating**: Jinja2 with inheritance from base templates
- **Repository Pattern**: Clean separation from direct database access
- **Session Management**: SQLModel session handling

### Key Components

#### 1. Statistics Cards (`/htmx/analysis/stats`)
```python
# Real-time statistics with Bootstrap card layout
def get_stats_partial() -> str:
    stats = AnalysisRepo.get_analysis_stats()
    pending_count = AnalysisRepo.count_pending_analysis()
    # Returns HTML with individual metric cards
```

**Features:**
- Individual cards for each metric
- Color-coded values (success, warning, danger)
- Responsive grid layout
- Auto-refresh capability

#### 2. Feed Dropdown (`/htmx/analysis/feeds-list-options`)
```python
# Dynamic feed loading with item counts
def get_feeds_list_options() -> str:
    feeds = session.exec(select(Feed).where(Feed.status == "active"))
    # Returns option elements with truncated titles
```

**Features:**
- Active feeds only
- Title truncation for long names
- Error handling for database issues

#### 3. Selection State Management
```javascript
// Alpine.js reactive state
selectionMode: 'timeRange', // 'latest', 'timeRange', 'unanalyzed'
activeSelection: {
    mode: null,
    params: {},
    description: ''
}
```

**Benefits:**
- Single source of truth for UI state
- Automatic preview updates
- Clear selection workflow

### User Experience Flow

#### 1. Selection Process
1. **Choose Mode:** User selects radio button for desired selection type
2. **Configure Parameters:** Input fields become active for selected mode
3. **Activate Selection:** User clicks SET button to confirm choice
4. **Preview Updates:** Automatic calculation of items and costs
5. **Analysis Start:** Green start button becomes enabled

#### 2. Visual Feedback
- **Active Selection Highlighting:** Selected mode gets light background
- **Parameter Enablement:** Only active mode inputs are editable
- **Button States:** SET buttons disabled for inactive modes
- **Alert Display:** Active selection shown in info alert box

#### 3. Filter System
```javascript
// Additive filters that refine base selection
filters: {
    useFeedFilter: false,     // Limit to specific feed
    feed_id: '',              // Selected feed ID
    unanalyzed_only: false,   // Skip analyzed items
    override_existing: false  // Re-analyze existing
}
```

## API Endpoints

### Core Analysis Control Endpoints

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/htmx/analysis/stats` | GET | Statistics cards HTML | HTML |
| `/htmx/analysis/feeds-list-options` | GET | Feed dropdown options | HTML |
| `/htmx/analysis/quick-actions` | GET | Quick actions (deprecated) | Empty |
| `/htmx/analysis/status` | GET | Overall status cards | HTML |
| `/htmx/analysis/active-runs` | GET | Active runs display | HTML |
| `/htmx/analysis/history` | GET | Completed runs table | HTML |

### Data Flow

#### Statistics Retrieval
```python
# Repository pattern for clean data access
stats = AnalysisRepo.get_analysis_stats()
pending_count = AnalysisRepo.count_pending_analysis()

# Coverage calculation
total_items = stats.get("total_analyzed", 0) + pending_count
coverage = stats.get("total_analyzed", 0) / max(total_items, 1)
```

#### Feed Data Loading
```python
# Active feeds with item counts
results = session.execute(text("""
    SELECT f.id, f.title, f.url, COUNT(i.id) as item_count,
           COUNT(CASE WHEN a.item_id IS NULL THEN 1 END) as unanalyzed_count
    FROM feeds f
    LEFT JOIN items i ON i.feed_id = f.id
    LEFT JOIN item_analysis a ON a.item_id = i.id
    GROUP BY f.id, f.title, f.url
    ORDER BY f.title ASC
"""))
```

## Configuration and Settings

### Default Parameters
- **Model:** GPT-4.1 Nano (recommended)
- **Processing Rate:** 1.0 requests/second
- **Time Range Default:** 7 days
- **Latest Count Default:** 50 items

### Customization Options
- **AI Model Selection:** Multiple GPT model options
- **Rate Limiting:** Configurable processing speed
- **Filter Combinations:** Multiple additive filters
- **Preview Threshold:** Automatic cost and time estimation

## Integration Points

### Worker System Integration
- **Analysis Queue:** Interfaces with background worker system
- **Status Tracking:** Real-time run progress monitoring
- **Cost Management:** Budget tracking and estimation

### Database Integration
- **Repository Pattern:** Clean abstraction over database operations
- **Session Management:** Proper connection handling
- **Query Optimization:** Efficient aggregation queries

### Frontend Framework Integration
- **Template Inheritance:** Extends base layout system
- **Component Reuse:** Shared UI components
- **State Management:** Alpine.js reactive patterns

## Performance Considerations

### Frontend Optimization
- **Lazy Loading:** HTMX loads content on demand
- **Automatic Refresh:** Smart polling for active content
- **Skeleton Loading:** Visual feedback during data fetching

### Backend Optimization
- **Query Efficiency:** Optimized aggregation queries
- **Caching Strategy:** Session-based feed data caching
- **Error Handling:** Graceful degradation on failures

### Network Optimization
- **Partial Updates:** Only changed content re-rendered
- **Minimal Payloads:** HTML fragments instead of full pages
- **Progressive Enhancement:** Works without JavaScript

## Error Handling

### User-Facing Errors
```html
<!-- Graceful error display -->
<div class="alert alert-danger">Failed to load statistics</div>
<div class="alert alert-danger">Failed to load feeds</div>
```

### Backend Error Handling
```python
# Comprehensive error logging and user feedback
try:
    stats = AnalysisRepo.get_analysis_stats()
except Exception as e:
    logger.error(f"Failed to get stats: {e}")
    return '<div class="alert alert-danger">Failed to load statistics</div>'
```

## Future Enhancements

### Planned Improvements
- **Real-time WebSocket Updates:** Live progress streaming
- **Advanced Filtering:** More granular selection options
- **Preset Management:** Save and load analysis configurations
- **Cost Tracking Dashboard:** Detailed spending analytics

### Technical Debt
- **Schema Import Issues:** Currently using `Any` type stubs (see Schema Workaround section)
- **JavaScript Modularity:** Alpine.js code could be split into modules
- **Testing Coverage:** Need comprehensive UI testing

## Browser Compatibility

### Supported Browsers
- **Chrome:** 90+ ✅
- **Firefox:** 88+ ✅
- **Safari:** 14+ ✅
- **Edge:** 90+ ✅

### Required Features
- **ES6 Support:** Arrow functions, template literals
- **Fetch API:** For HTMX requests
- **CSS Grid:** For responsive layouts
- **Alpine.js:** Reactive framework

## Accessibility

### Standards Compliance
- **ARIA Labels:** Proper form labeling
- **Keyboard Navigation:** Full keyboard support
- **Screen Reader:** Compatible markup structure
- **Color Contrast:** WCAG AA compliant

### Best Practices
- **Semantic HTML:** Proper element usage
- **Focus Management:** Clear focus indicators
- **Alt Text:** All images have descriptions
- **Error Announcements:** Screen reader notifications

---

*This documentation covers the complete Analysis Control Interface redesign implemented in News MCP v3.2. For technical implementation details, see the source files in `/app/web/views/analysis_control.py` and `/templates/analysis_control.html`.*