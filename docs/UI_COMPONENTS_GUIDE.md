# UI Components Guide - News MCP

**Version:** 3.3 - Dark Mode Integration & Live Updates
**Last Updated:** September 2025
**Framework:** Bootstrap 5 + Alpine.js + HTMX + Dark Mode Optimization

## Overview

This guide documents the UI component patterns and design system used throughout the News MCP application, with a focus on the recent Analysis Control Interface redesign that establishes new patterns for the entire application.

## Component Architecture

### Technology Stack
- **Bootstrap 5:** Base styling and responsive grid
- **Alpine.js:** Reactive state management and interactions
- **HTMX:** Server-side rendering with partial updates
- **Custom CSS:** NMC design system extensions

### Design Principles
1. **Component Reusability:** Modular design for consistency
2. **Progressive Enhancement:** Works without JavaScript
3. **Accessibility First:** WCAG AA compliance
4. **Mobile Responsive:** Mobile-first design approach
5. **Dark Mode First:** Optimized for dark theme with proper contrast
6. **Live Updates:** HTMX-powered real-time UI refreshes

## Core Component Patterns

### 1. Statistics Cards

#### Dark Mode Implementation
```html
<div class="card bg-dark border-info text-center">
    <div class="card-body py-3">
        <h4 class="text-info mb-1">7,421</h4>
        <small class="text-light">Total Items</small>
    </div>
</div>
```

#### CSS Classes (Dark Mode Optimized)
- `bg-dark`: Dark background for consistent theming
- `border-info`: Colored borders for visual hierarchy
- `text-center`: Center-aligned content
- `text-info`/`text-success`/`text-warning`: Semantic colors for values
- `text-light`: High contrast white text for labels (NOT text-muted)
- `py-3`: Vertical padding for proper spacing

#### Variants & Dark Mode Best Practices
```html
<!-- Success State -->
<div class="card bg-dark border-success text-center">
    <div class="card-body py-3">
        <h4 class="text-success mb-1">2,674</h4>
        <small class="text-light">Analyzed</small>
    </div>
</div>

<!-- Warning State -->
<div class="card bg-dark border-warning text-center">
    <div class="card-body py-3">
        <h4 class="text-warning mb-1">4,747</h4>
        <small class="text-light">Pending</small>
    </div>
</div>
```

#### Critical Dark Mode Rules
- **NEVER use `text-muted`** - it's unreadable on dark backgrounds
- **ALWAYS use `text-light`** for secondary text/labels
- **Use semantic colors** for values: `text-info`, `text-success`, `text-warning`, `text-primary`
- **Container must be `bg-dark`** with appropriate border colors

### 2. HTMX Live Update Components

#### Live Articles List
```html
<div id="articles-live"
     hx-get="/htmx/analysis/articles-live"
     hx-trigger="load"
     hx-swap="innerHTML">
    <!-- Loading state -->
    <div class="spinner-border text-primary" role="status"></div>
</div>
```

#### Statistics with Auto-Refresh
```html
<div id="stats-horizontal"
     hx-get="/htmx/analysis/stats-horizontal"
     hx-trigger="load, every 30s"
     hx-swap="innerHTML">
    <!-- Auto-refreshes every 30 seconds -->
</div>
```

#### SET Button Integration
```html
<button class="btn btn-success btn-sm"
        onclick="updateLiveArticles('latest', 50)">
    SET Latest 50
</button>
```
<div class="text-muted">Pending</div>

<!-- Danger State -->
<div class="text-danger">45</div>
<div class="text-muted">Failed</div>
```

#### Usage Guidelines
- **Consistent Sizing:** Use same font-size values across cards
- **Color Coding:** Match colors to semantic meaning
- **Grid Layout:** Use Bootstrap grid for responsive arrangement
- **Real-time Updates:** HTMX endpoints for dynamic content

### 2. Exclusive Selection Pattern

#### Radio Button Groups with SET Buttons
```html
<div class="mb-md" :class="selectionMode === 'latest' ? 'bg-light p-sm rounded' : ''">
    <div class="d-flex align-items-center gap-md">
        <div class="form-check">
            <input class="form-check-input" type="radio" name="selectionMode"
                   value="latest" x-model="selectionMode" id="modeLatest">
            <label class="form-check-label fw-bold" for="modeLatest">
                Latest N Articles
            </label>
        </div>
        <input type="number" class="form-control" style="width: 100px;"
               x-model="latestCount" :disabled="selectionMode !== 'latest'"
               placeholder="50" min="1" max="1000" value="50">
        <button type="button" class="btn btn-success btn-sm"
                :disabled="selectionMode !== 'latest'"
                @click="setLatestSelection()">
            <i class="bi bi-check"></i> SET
        </button>
    </div>
</div>
```

#### Key Features
- **Visual Highlighting:** Active selection gets `bg-light` background
- **Input Enablement:** Only active mode inputs are editable
- **SET Button Pattern:** Explicit confirmation required
- **Alpine.js Integration:** Reactive state management

#### State Management
```javascript
// Alpine.js data structure
{
    selectionMode: 'timeRange', // Current selected mode
    latestCount: 50,           // Parameters for each mode
    timeRangeDays: 7,
    timeRangeHours: 0,
    activeSelection: {         // Confirmed selection
        mode: null,
        params: {},
        description: ''
    }
}
```

### 3. HTMX Dynamic Loading

#### Feed Dropdown with Dynamic Options
```html
<select class="form-select form-select-sm" x-model="filters.feed_id"
        hx-get="/htmx/analysis/feeds-list-options"
        hx-trigger="load"
        hx-target="this">
    <option value="">Select Feed</option>
    <!-- Options loaded via HTMX -->
</select>
```

#### Server Response Pattern
```python
def get_feeds_list_options() -> str:
    """Return feed options for select dropdown"""
    try:
        feeds = session.exec(select(Feed).where(Feed.status == "active")).all()
        html = '<option value="">Select Feed</option>'
        for feed in feeds:
            display_title = feed.title or f"Feed {feed.id}"
            if len(display_title) > 40:
                display_title = display_title[:37] + "..."
            html += f'<option value="{feed.id}">{display_title}</option>'
        return html
    except Exception as e:
        logger.error(f"Failed to get feeds: {e}")
        return '<option value="">Select Feed</option>'
```

#### Key Patterns
- **Load Trigger:** Content loads automatically on element creation
- **Target Self:** Replace the select element's contents
- **Error Handling:** Graceful fallback on server errors
- **Title Truncation:** Smart text handling for long titles

### 4. Progressive Enhancement Alert System

#### Active Selection Display
```html
<div class="alert alert-info mb-lg" x-show="activeSelection.description">
    <div class="d-flex justify-content-between align-items-start">
        <div>
            <strong>Active Selection:</strong>
            <span x-text="activeSelection.description"></span>
            <br>
            <div class="row mt-sm">
                <div class="col-md-4">
                    <small class="text-muted">
                        Total items: <strong x-text="preview.total_items || '...'"></strong>
                    </small>
                </div>
                <div class="col-md-4">
                    <small class="text-success">
                        Already analyzed: <strong x-text="preview.analyzed_items || '...'"></strong>
                    </small>
                </div>
                <div class="col-md-4">
                    <small class="text-warning">
                        To analyze: <strong x-text="preview.item_count || '...'"></strong>
                    </small>
                </div>
            </div>
        </div>
        <button type="button" class="btn btn-outline-danger btn-sm" @click="clearSelection()">
            <i class="bi bi-x-circle"></i> Clear
        </button>
    </div>
</div>
```

#### Features
- **Conditional Display:** Only shown when selection is active
- **Rich Information:** Multi-column data display
- **Action Buttons:** Clear functionality integrated
- **Semantic Colors:** Color-coded information types

### 5. Skeleton Loading Pattern

#### Loading States
```html
<div class="nmc-skeleton-card">
    <div class="nmc-skeleton-lines">
        <div class="nmc-skeleton skeleton-text"></div>
        <div class="nmc-skeleton skeleton-text"></div>
        <div class="nmc-skeleton skeleton-text"></div>
    </div>
</div>
```

#### CSS Implementation
```css
.nmc-skeleton {
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: loading 1.5s infinite;
}

.skeleton-text {
    height: 1rem;
    border-radius: 4px;
    margin-bottom: 0.5rem;
}

@keyframes loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
```

### 6. Responsive Card System

#### NMC Card Structure
```html
<div class="nmc-card mb-lg">
    <div class="card-body py-lg px-lg">
        <h6 class="mb-lg">Card Title</h6>
        <!-- Card content -->
    </div>
</div>
```

#### Spacing System
- `py-lg`, `px-lg`: Large padding for content areas
- `mb-lg`: Large bottom margins for sections
- `gap-md`: Medium gaps between elements
- `mb-sm`: Small margins for tight groupings

#### Responsive Breakpoints
```html
<div class="row gap-xl">
    <div class="col-lg-7"><!-- Main content --></div>
    <div class="col-lg-4"><!-- Sidebar --></div>
</div>
```

## Advanced Patterns

### 1. Tab-Based Navigation

#### Bootstrap 5 Tabs Integration
```html
<ul class="nav nav-tabs" id="analysisControlTabs" role="tablist">
    <li class="nav-item" role="presentation">
        <button class="nav-link active px-lg py-md" id="start-tab"
                data-bs-toggle="tab" data-bs-target="#start-panel"
                type="button" role="tab">
            <i class="bi bi-play-circle me-sm"></i> Start Analysis
        </button>
    </li>
</ul>

<div class="tab-content" id="analysisControlTabContent">
    <div class="tab-pane fade show active p-xl" id="start-panel" role="tabpanel">
        <!-- Tab content -->
    </div>
</div>
```

#### Accessibility Features
- **Role Attributes:** Proper ARIA roles for screen readers
- **Focus Management:** Keyboard navigation support
- **Tab State:** Clear active/inactive visual states

### 2. Real-time Updates with HTMX

#### Auto-refreshing Content
```html
<div id="overview-stats"
     hx-get="/htmx/analysis/stats"
     hx-trigger="load, every 30s">
    <!-- Initial loading skeleton -->
</div>
```

#### Manual Refresh Buttons
```html
<button class="btn btn-outline-primary btn-sm"
        hx-get="/htmx/analysis/stats"
        hx-target="#overview-stats"
        hx-trigger="click">
    <i class="bi bi-arrow-clockwise me-sm"></i> Refresh
</button>
```

### 3. Form State Management

#### Alpine.js Form Binding
```javascript
// Reactive form data
params: {
    model_tag: 'gpt-4.1-nano',
    rate_per_second: 1.0,
    limit: 200
},

// Two-way binding
x-model="params.model_tag"
x-model="params.rate_per_second"
```

#### Validation and Submission
```javascript
async startRun() {
    const query = this.buildQuery();
    if (!query) {
        alert('Please select a target article selection first by clicking a SET button.');
        return;
    }
    // Submit logic
}
```

## Icon System

### Bootstrap Icons Integration
```html
<!-- Standard icons -->
<i class="bi bi-play-circle"></i>    <!-- Play/Start -->
<i class="bi bi-arrow-clockwise"></i> <!-- Refresh -->
<i class="bi bi-check"></i>          <!-- Confirm/Success -->
<i class="bi bi-x-circle"></i>       <!-- Clear/Cancel -->
<i class="bi bi-gear"></i>           <!-- Settings -->
<i class="bi bi-list-task"></i>      <!-- Tasks/Runs -->

<!-- Consistent spacing -->
<i class="bi bi-play-circle me-sm"></i> Text
```

### Icon Guidelines
- **Semantic Usage:** Icons match their meaning
- **Consistent Spacing:** Use `me-sm` for text spacing
- **Color Coordination:** Icons inherit text colors
- **Accessibility:** Always include text labels

## Responsive Design

### Breakpoint Strategy
```html
<!-- Mobile-first responsive design -->
<div class="col-12 col-md-6 col-lg-4">
    <!-- Responsive column -->
</div>

<!-- Responsive gap system -->
<div class="row gap-sm gap-md-md gap-lg-xl">
    <!-- Responsive spacing -->
</div>
```

### Mobile Optimizations
- **Touch Targets:** Minimum 44px button sizes
- **Readable Text:** Appropriate font sizes
- **Simplified Layout:** Reduced complexity on mobile
- **Gesture Support:** Swipe and tap interactions

## Performance Considerations

### HTMX Optimization
```html
<!-- Efficient targeting -->
hx-target="#specific-element"  <!-- Not body -->

<!-- Smart triggers -->
hx-trigger="load, every 30s"   <!-- Not every 1s -->

<!-- Minimal payloads -->
<!-- Return only HTML fragments, not full pages -->
```

### Alpine.js Performance
```javascript
// Computed properties for expensive operations
get estimatedCost() {
    return this.preview.item_count * 0.0003;
}

// Debounced updates
@input.debounce.500ms="updatePreview()"
```

### CSS Performance
```css
/* Use efficient selectors */
.nmc-card { /* Class selector */ }

/* Avoid expensive operations */
/* box-shadow: ... (use sparingly) */

/* Optimize animations */
.nmc-skeleton {
    will-change: background-position; /* GPU acceleration */
}
```

## Testing Guidelines

### Component Testing
```javascript
// Test Alpine.js components
test('Selection mode changes enable correct inputs', () => {
    // Component state testing
});

// Test HTMX interactions
test('Stats refresh updates display', async () => {
    // Server response testing
});
```

### Accessibility Testing
```bash
# Use axe-core for automated testing
npm install @axe-core/cli
axe-core http://localhost:8000/analysis-control
```

### Browser Testing Matrix
- **Chrome 90+:** Primary development target
- **Firefox 88+:** Secondary target
- **Safari 14+:** iOS compatibility
- **Edge 90+:** Windows compatibility

## Migration Guidelines

### Legacy Component Updates
1. **Identify Pattern:** Match new design patterns
2. **Update HTML:** Use new component structure
3. **Add Alpine.js:** For interactive components
4. **HTMX Integration:** For dynamic content
5. **Test Accessibility:** Ensure compliance

### Code Quality Standards
```html
<!-- ✅ Good: Semantic, accessible, consistent -->
<div class="nmc-card mb-lg">
    <div class="card-body py-lg px-lg">
        <h6 class="mb-lg">Statistics</h6>
        <div class="row">
            <div class="col-6">
                <div class="card border-0 bg-light">
                    <div class="card-body p-2 text-center">
                        <div class="text-primary fw-bold">1,234</div>
                        <div class="text-muted small">Items</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- ❌ Avoid: Inline styles, non-semantic markup -->
<div style="background: #f8f9fa; padding: 20px;">
    <span style="font-size: 24px;">1234</span>
    <div>Items</div>
</div>
```

---

*This UI Components Guide serves as the definitive reference for implementing consistent, accessible, and performant user interface components throughout the News MCP application.*