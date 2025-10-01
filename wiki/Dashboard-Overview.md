# Dashboards & Web UI Overview

News MCP provides **11 powerful web dashboards** for comprehensive system monitoring and management.

---

## 📊 Quick Access Dashboard Directory

| Dashboard | URL | Port | Purpose | Status |
|-----------|-----|------|---------|--------|
| 🏠 **Main Dashboard** | `/` | 8000 | System overview & quick access | ✅ Active |
| 🎯 **Analysis Cockpit v4** | `/admin/analysis` | 8000 | Manual analysis interface (Alpine.js) | ✅ Active |
| 🤖 **Auto-Analysis** | `/admin/auto-analysis` | 8000 | Automatic analysis monitoring | ✅ Active |
| 🎛️ **Manager Control** | `/admin/manager` | 8000 | Analysis control center (Dark Mode) | ✅ Active |
| 📡 **Feed Management** | `/admin/feeds` | 8000 | RSS feed CRUD operations | ✅ Active |
| 📰 **Articles/Items** | `/admin/items` | 8000 | Article browsing & filtering | ✅ Active |
| 📊 **Statistics** | `/admin/statistics` | 8000 | System statistics & charts | ✅ Active |
| 📈 **Metrics** | `/admin/metrics` | 8000 | Performance metrics & monitoring | ✅ Active |
| 🗄️ **Database Browser** | `/admin/database` | 8000 | SQL query interface with templates | ✅ Active |
| ❤️ **Health Monitor** | `/admin/health` | 8000 | System health diagnostics | ✅ Active |
| ⚙️ **Processors** | `/admin/processors` | 8000 | Content processor management | ✅ Active |

---

## 🏠 Main Dashboard

**URL:** `http://localhost:8000/`

### Purpose
Central hub providing system overview and quick access to all features.

### Features
- System status overview
- Quick statistics (feeds, items, runs)
- Navigation to all admin dashboards
- Real-time system health indicators
- Recent activity timeline

### Use Cases
- First point of access after installation
- Daily system health check
- Quick navigation to specialized dashboards

### Template
`templates/index.html`

---

## 🎯 Analysis Cockpit v4

**URL:** `http://localhost:8000/admin/analysis`
**[Detailed Guide →](Analysis-Cockpit)**

### Purpose
Main interface for **manual AI-powered analysis** of feed items.

### Key Features
- **Target Selection**
  - Feed-based filtering
  - Category-based filtering
  - Date range selection
  - Scope limits (max items to analyze)
- **Preview System**
  - See selection before analysis
  - Item count validation
  - Cost estimation
- **Run Management**
  - Start/stop analysis runs
  - Real-time progress tracking
  - Queue status monitoring
- **Live Updates**
  - Alpine.js state management
  - HTMX partial updates
  - WebSocket progress events

### Technology Stack
- Alpine.js v3 for reactive UI
- HTMX for server-side rendering
- Bootstrap 5 Dark Mode
- WebSocket for real-time updates

### Use Cases
- Manual analysis of specific feeds/categories
- On-demand sentiment analysis
- Targeted date range analysis
- Quality control for auto-analysis

### Template
`templates/analysis_cockpit_v4.html`

---

## 🤖 Auto-Analysis Dashboard

**URL:** `http://localhost:8000/admin/auto-analysis`
**[Detailed Guide →](Auto-Analysis-Dashboard)**

### Purpose
Monitor and control **automatic AI analysis** for feeds.

### Key Features
- **Feed Configuration**
  - Enable/disable auto-analysis per feed
  - Set analysis intervals
  - Configure batch sizes
- **Queue Management**
  - View pending items queue
  - Monitor queue depth
  - See processing statistics
- **Active Run Monitoring**
  - Current runs status
  - Progress tracking
  - Rate limiting info
- **History Timeline**
  - Past auto-analysis runs
  - Success/failure statistics
  - Performance metrics

### Configuration
Controlled via `.env` settings:
```bash
MAX_DAILY_AUTO_RUNS=500
AUTO_ANALYSIS_RATE_PER_SECOND=3.0
MAX_CONCURRENT_RUNS=5
```

### Use Cases
- Enable auto-analysis for new feeds
- Monitor auto-analysis queue
- Track daily usage limits
- Troubleshoot failed runs

### Template
`templates/auto_analysis.html`

---

## 🎛️ Manager Control Center

**URL:** `http://localhost:8000/admin/manager`
**[Detailed Guide →](Manager-Control-Center)**

### Purpose
**System control center** with emergency controls and deep system monitoring.

### Key Features
- **Emergency Controls**
  - Emergency Stop button (halt all analysis)
  - Resume operations button
  - Process queue manually
- **System Overview**
  - Active runs count
  - Queue depth
  - Worker status
  - Rate limit status
- **Live Monitoring**
  - 5-second auto-refresh
  - HTMX live updates
  - Real-time statistics
- **Configuration Display**
  - Current limits (daily, hourly, concurrent)
  - OpenAI rate limits
  - System capacity

### Design
- Bootstrap Dark Mode
- Responsive layout
- Color-coded status indicators
- Large, accessible control buttons

### Use Cases
- Emergency system shutdown
- Manual queue processing
- Deep system monitoring
- Performance troubleshooting

### Template
`templates/admin/analysis_manager.html`

---

## 📡 Feed Management Dashboard

**URL:** `http://localhost:8000/admin/feeds`

### Purpose
Complete **RSS feed CRUD** operations and configuration.

### Key Features
- **Feed List**
  - All feeds with status
  - Health indicators
  - Last fetch timestamp
  - Item counts
- **CRUD Operations**
  - Add new feeds (URL + metadata)
  - Edit feed configuration
  - Delete feeds (with confirmation)
  - Test feed URL before adding
- **Feed Actions**
  - Manual fetch trigger
  - Enable/disable feed
  - Toggle auto-analysis
  - View feed logs
- **Bulk Operations**
  - Select multiple feeds
  - Batch enable/disable
  - Mass fetch operations

### Use Cases
- Adding new RSS feeds
- Managing existing feeds
- Troubleshooting feed issues
- Configuring auto-analysis

### Template
`templates/admin/feeds.html`

---

## 📰 Articles/Items Dashboard

**URL:** `http://localhost:8000/admin/items`

### Purpose
Browse, search, and filter **news articles/items**.

### Key Features
- **Article List**
  - Paginated article view
  - Title, description, published date
  - Source feed information
  - Analysis status indicators
- **Filtering**
  - By feed
  - By date range
  - By analysis status (analyzed/unanalyzed)
  - By sentiment (if analyzed)
- **Search**
  - Full-text search
  - Title/description search
  - URL search
- **Article Details**
  - Full content view
  - Analysis results (if available)
  - Metadata display
  - Original URL link

### Use Cases
- Finding specific articles
- Verifying analysis results
- Content browsing
- Quality assurance

### Template
`templates/admin/items.html`

---

## 📊 Statistics Dashboard

**URL:** `http://localhost:8000/admin/statistics`

### Purpose
**System-wide statistics** and performance metrics.

### Key Features
- **Feed Statistics**
  - Total feeds, active/inactive counts
  - Feeds by category
  - Average fetch interval
  - Success rates
- **Item Statistics**
  - Total items count
  - Items per day (7-day trend)
  - Items by feed
  - Analysis coverage percentage
- **Analysis Statistics**
  - Total runs completed
  - Success/failure rates
  - Average run duration
  - Items analyzed per day
- **Charts & Visualizations**
  - Timeline graphs
  - Pie charts for distributions
  - Bar charts for comparisons

### Use Cases
- System performance overview
- Trend analysis
- Capacity planning
- Reporting

### Template
`templates/admin/statistics.html`

---

## 📈 Metrics Dashboard

**URL:** `http://localhost:8000/admin/metrics`

### Purpose
**Performance metrics** and technical monitoring.

### Key Features
- **API Metrics**
  - Request counts per endpoint
  - Response times (P50, P95, P99)
  - Error rates
- **Worker Metrics**
  - Analysis worker status
  - Queue depth
  - Processing rate
  - OpenAI API usage
- **Database Metrics**
  - Connection pool status
  - Query performance
  - Table sizes
- **System Metrics**
  - Memory usage
  - CPU usage (if available)
  - Disk usage

### Use Cases
- Performance monitoring
- Bottleneck identification
- SLA compliance checking
- Infrastructure planning

### Template
`templates/admin/metrics.html`

---

## 🗄️ Database Browser

**URL:** `http://localhost:8000/admin/database`

### Purpose
**SQL query interface** with safety controls and predefined templates.

### Key Features
- **Query Interface**
  - SQL editor with syntax highlighting
  - Read-only queries enforced
  - Query templates library
  - Results table view
- **Predefined Queries**
  - Common system queries
  - Diagnostic queries
  - Statistics queries
  - Health check queries
- **Safety Features**
  - No write operations allowed
  - Query timeout protection
  - Result limit enforcement
  - SQL injection prevention
- **Schema Browser**
  - Table list with descriptions
  - Column information
  - Relationship diagrams

### Common Query Templates
- List all feeds with item counts
- Find articles by date range
- Analysis success rates
- Feed health diagnostics
- Queue status check

### Use Cases
- Custom data analysis
- Debugging issues
- Ad-hoc reporting
- Schema exploration

### Template
`templates/admin/database.html`

---

## ❤️ Health Monitor

**URL:** `http://localhost:8000/admin/health`

### Purpose
**System health diagnostics** and monitoring.

### Key Features
- **System Health**
  - Overall system status (healthy/degraded/down)
  - Component status (web, worker, scheduler, DB)
  - Uptime information
- **Feed Health**
  - Feeds with consecutive failures
  - Stale feeds (not updated recently)
  - Average fetch success rate
- **Database Health**
  - Connection status
  - Pool statistics
  - Table health checks
- **Worker Health**
  - Worker process status
  - Queue depth
  - Processing rate
- **Alerts**
  - Critical issues highlighted
  - Warning conditions
  - Recommendations

### Health Indicators
- 🟢 Green: Healthy
- 🟡 Yellow: Warning
- 🔴 Red: Critical

### Use Cases
- Daily health check
- Incident diagnosis
- Proactive monitoring
- Pre-deployment verification

### Template
`templates/admin/health.html`

---

## ⚙️ Processors Dashboard

**URL:** `http://localhost:8000/admin/processors`

### Purpose
Manage **content processors** and processing rules.

### Key Features
- **Processor List**
  - All registered processors
  - Status (enabled/disabled)
  - Processing statistics
- **Processor Configuration**
  - Configure processor parameters
  - Enable/disable processors
  - Set processing priorities
- **Processing Logs**
  - Recent processing activity
  - Success/failure rates
  - Error logs
- **Processor Templates**
  - Predefined processing rules
  - Custom processor creation
  - Template management

### Use Cases
- Configure content processing
- Manage processor pipeline
- Troubleshoot processing issues
- Add custom processors

### Template
`templates/admin/processors.html`

---

## 🎨 Common UI Features

All dashboards share these common features:

### Navigation
- **Top Navigation Bar**
  - Logo & branding
  - Main menu links
  - User settings (if auth enabled)
  - Logout button (if auth enabled)
- **Sidebar Navigation**
  - Dashboard quick links
  - Section grouping
  - Active page highlighting

### Theme
- **Dark Mode** (default)
  - Bootstrap Dark theme
  - Consistent color scheme
  - High contrast for readability
- **Light Mode** (optional)
  - Toggle in settings
  - Preserved across sessions

### Responsive Design
- Mobile-friendly layouts
- Tablet optimization
- Desktop full-screen support

### Real-time Updates
- HTMX for partial page updates
- WebSocket for live data
- Auto-refresh options (configurable intervals)

### Accessibility
- ARIA labels
  - Keyboard navigation
- Screen reader support
- High contrast mode

---

## 🔧 Dashboard Configuration

### Environment Variables

```bash
# Dashboard settings (optional)
DASHBOARD_REFRESH_INTERVAL=5000  # milliseconds
ENABLE_DARK_MODE=true
ENABLE_AUTO_REFRESH=true
```

### Access Control

Dashboards are accessible without authentication by default. For production:

```bash
# Enable authentication (future feature)
REQUIRE_AUTH=true
AUTH_SECRET_KEY=your_secret_key
```

---

## 📱 Mobile Access

All dashboards are mobile-responsive:

- **Mobile URL:** `http://<your-ip>:8000/admin/<dashboard>`
- **Tablet optimized:** Yes
- **Touch-friendly:** Yes
- **Responsive tables:** Horizontal scroll on small screens

---

## 🔗 Related Documentation

- **[Analysis Cockpit v4 Guide](Analysis-Cockpit)** - Detailed manual analysis guide
- **[Auto-Analysis Dashboard Guide](Auto-Analysis-Dashboard)** - Auto-analysis setup
- **[Manager Control Center Guide](Manager-Control-Center)** - System controls
- **[API Documentation](API-Overview)** - Programmatic access to all features
- **[Architecture](Architecture)** - System design details

---

**Last Updated:** 2025-10-01
**Dashboard Count:** 11
**Total Features:** 100+
