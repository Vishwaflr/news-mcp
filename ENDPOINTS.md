# 📋 News MCP API Endpoints Documentation

> **Konsolidierte Übersicht aller FastAPI- und MCP-Tool-Endpunkte**
> Stand: 2025-09-24 | Version: Job-based Analysis System

## 🚀 **Analysis Control & Job System**

### **🔥 NEW: Job-based Analysis API**
```http
POST   /api/analysis/jobs/preview          # Create preview job with estimates
GET    /api/analysis/jobs/{job_id}         # Get specific job
POST   /api/analysis/jobs/{job_id}/refresh # Refresh job estimates
GET    /api/analysis/jobs/                 # List active jobs
POST   /api/analysis/jobs/{job_id}/confirm # Confirm job for execution
POST   /api/analysis/jobs/preview/legacy   # Legacy job format support
```

### **Analysis Control Center**
```http
POST   /api/analysis/preview               # Preview analysis run
POST   /api/analysis/start                 # Start analysis run
POST   /api/analysis/runs                  # Create run (alias for start)
GET    /api/analysis/runs                  # List analysis runs
POST   /api/analysis/pause/{run_id}        # Pause specific run
POST   /api/analysis/start/{run_id}        # Resume specific run
POST   /api/analysis/cancel/{run_id}       # Cancel specific run
GET    /api/analysis/status/{run_id}       # Get run status
GET    /api/analysis/status                # Get system status
GET    /api/analysis/history               # Get run history
```

### **Analysis Presets & Config**
```http
POST   /api/analysis/presets               # Save analysis preset
GET    /api/analysis/presets               # List presets
DELETE /api/analysis/presets/{preset_id}   # Delete preset
GET    /api/analysis/quick-actions         # Get quick action buttons
GET    /api/analysis/articles              # Get articles for selection
GET    /api/analysis/feeds                 # Get feeds for analysis
GET    /api/analysis/stats                 # Get analysis statistics
```

### **Cost & Model Management**
```http
GET    /api/analysis/cost/{model}          # Get model cost information
GET    /api/analysis/models/compare        # Compare model costs
GET    /api/analysis/budget                # Get budget information
```

## 🔧 **Analysis Management & Worker**

### **Analysis Worker Control**
```http
GET    /api/worker/status                  # Worker status and metrics
POST   /api/worker/control                 # Control worker (start/stop/pause)
GET    /api/stats                          # Worker statistics
POST   /api/test-deferred                  # Test deferred processing
```

### **Analysis Management**
```http
GET    /manager/status                     # Analysis manager status
POST   /manager/emergency-stop             # Emergency stop all analysis
POST   /manager/resume                     # Resume analysis operations
GET    /manager/limits                     # Get current limits
GET    /manager/queue                      # Get run queue status
POST   /manager/queue/process              # Process queued run
DELETE /manager/queue/{queued_run_id}      # Remove from queue
GET    /health                             # Analysis system health
```

## 📡 **Feeds Management**

### **Feed Operations**
```http
GET    /api/feeds/                         # List all feeds
GET    /api/feeds/{feed_id}                # Get specific feed
POST   /api/feeds/json                     # Create feed from JSON
POST   /api/feeds/                         # Create new feed
PUT    /api/feeds/{feed_id}                # Update feed
PUT    /api/feeds/{feed_id}/form           # Update feed via form
POST   /api/feeds/{feed_id}/fetch          # Manual feed fetch
DELETE /api/feeds/{feed_id}                # Delete feed
```

### **Feed Health & Monitoring**
```http
GET    /api/health/feeds                   # All feeds health status
GET    /api/health/feeds/{feed_id}         # Specific feed health
GET    /api/health/logs/{feed_id}          # Feed fetch logs
GET    /api/health/status                  # Overall health status
```

### **Feed Limits & Control**
```http
GET    /feed-limits/feeds/{feed_id}        # Get feed limits
POST   /feed-limits/feeds/{feed_id}        # Set feed limits
DELETE /feed-limits/feeds/{feed_id}        # Remove feed limits
POST   /feed-limits/feeds/{feed_id}/check  # Check limit violations
POST   /feed-limits/feeds/{feed_id}/enable # Enable feed after limit
GET    /feed-limits/feeds/{feed_id}/violations # Get violations
GET    /feed-limits/violations/summary     # Global violations summary
POST   /feed-limits/feeds/{feed_id}/emergency-stop # Emergency stop feed
GET    /feed-limits/presets                # Get limit presets
```

## 📄 **Items & Content Management**

### **Item Operations**
```http
GET    /api/items/                         # List items (paginated)
GET    /api/items/analyzed                 # List analyzed items
GET    /api/items/analysis/stats           # Analysis statistics
GET    /api/items/{item_id}                # Get specific item
GET    /api/items/{item_id}/analysis       # Get item analysis
```

## 🏷️ **Categories & Sources**

### **Categories**
```http
GET    /api/categories/                    # List categories
GET    /api/categories/{category_id}       # Get specific category
POST   /api/categories/                    # Create category
DELETE /api/categories/{category_id}       # Delete category
```

### **Sources**
```http
GET    /api/sources/                       # List sources
GET    /api/sources/{source_id}            # Get specific source
POST   /api/sources/                       # Create source
DELETE /api/sources/{source_id}            # Delete source
```

## 🛠️ **Content Processors**

### **Processor Management**
```http
GET    /api/processors/types               # Available processor types
GET    /api/processors/config/{feed_id}    # Get feed processor config
POST   /api/processors/config/{feed_id}    # Set feed processor config
DELETE /api/processors/config/{feed_id}    # Delete processor config
GET    /api/processors/stats               # Processor statistics
POST   /api/processors/reprocess/feed/{feed_id}   # Reprocess feed
POST   /api/processors/reprocess/item/{item_id}   # Reprocess item
GET    /api/processors/health              # Processor health
POST   /api/processors/validate-config     # Validate processor config
```

### **Processor Templates**
```http
GET    /api/processors/templates           # List processor templates
POST   /api/processors/templates           # Create template
PUT    /api/processors/templates/{template_id} # Update template
DELETE /api/processors/templates/{template_id} # Delete template
```

## 📊 **Analytics & Metrics**

### **System Metrics**
```http
GET    /metrics/                           # Basic metrics overview
GET    /metrics/prometheus                 # Prometheus format metrics
GET    /metrics/{metric_name}              # Specific metric data
POST   /metrics/reset                      # Reset metrics
```

### **Business Metrics**
```http
GET    /api/metrics/system/overview        # System overview metrics
GET    /api/metrics/feeds/{feed_id}        # Feed-specific metrics
GET    /api/metrics/feeds/{feed_id}/summary # Feed metrics summary
GET    /api/metrics/costs/breakdown        # Cost breakdown analysis
GET    /api/metrics/performance/queue      # Queue performance metrics
GET    /api/metrics/feeds                  # All feeds metrics
POST   /api/metrics/test/record            # Record test metrics
```

### **Statistics & Reports**
```http
GET    /dashboard                          # Main dashboard data
GET    /api/statistics/feed/{feed_id}      # Feed statistics
GET    /api/statistics/export/csv          # Export statistics to CSV
```

## 🗄️ **Database & Admin**

### **Database Operations**
```http
GET    /api/database/tables                # List database tables
GET    /api/database/schema/{table_name}   # Get table schema
POST   /api/database/query                 # Execute database query
GET    /api/database/quick-queries         # Get quick query templates
```

## ⚙️ **System Configuration**

### **User Settings**
```http
GET    /api/user-settings/default-params   # Get default analysis params
POST   /api/user-settings/default-params   # Set default analysis params
```

### **Feature Flags**
```http
GET    /feature-flags/                     # List all feature flags
GET    /feature-flags/{flag_name}          # Get specific flag
POST   /feature-flags/{flag_name}          # Update flag value
POST   /feature-flags/{flag_name}/reset-metrics # Reset flag metrics
GET    /feature-flags/metrics/shadow-comparison # Shadow comparison metrics
GET    /feature-flags/metrics/analysis-shadow-comparison # Analysis shadow metrics
GET    /feature-flags/metrics/performance  # Performance metrics
GET    /feature-flags/metrics/dashboard    # Metrics dashboard
POST   /feature-flags/shadow-comparison/reset # Reset shadow comparison
POST   /feature-flags/analysis-shadow-comparison/reset # Reset analysis shadow
POST   /feature-flags/analysis-shadow/{action} # Shadow analysis action
GET    /feature-flags/health               # Feature flags health
```

### **Scheduler Control**
```http
GET    /api/scheduler/status               # Scheduler status
POST   /api/scheduler/interval             # Set global fetch interval
POST   /api/scheduler/interval/{feed_id}   # Set feed-specific interval
POST   /api/scheduler/pause                # Pause scheduler
POST   /api/scheduler/resume               # Resume scheduler
GET    /api/scheduler/heartbeat            # Scheduler heartbeat
```

## 🩺 **Health & Monitoring**

### **Health Checks**
```http
GET    /health/                            # Basic health check
GET    /health/detailed                    # Detailed health report
GET    /health/check/{check_name}          # Specific health check
GET    /health/ready                       # Readiness probe
GET    /health/live                        # Liveness probe
```

### **Circuit Breakers**
```http
GET    /circuit-breakers                   # List circuit breakers
GET    /circuit-breakers/{name}            # Get breaker status
POST   /circuit-breakers/{name}/reset      # Reset circuit breaker
```

### **Performance Monitoring**
```http
GET    /requests/active                    # Active requests
GET    /requests/{request_id}              # Request details
GET    /performance                        # Performance metrics
GET    /slow-requests                      # Slow requests analysis
```

## 🌐 **HTMX Web Interface**

### **Analysis UI Components**
```http
GET    /htmx/analysis/model-params         # Model parameters form
GET    /htmx/analysis/target-selection     # Target selection UI
POST   /htmx/analysis/preview-update       # Update preview
GET    /htmx/analysis/preview-start        # Preview & start component
GET    /htmx/analysis/articles-live        # Live articles display
GET    /htmx/analysis/stats-horizontal     # Horizontal stats
GET    /htmx/analysis/runs/active          # Active runs display
GET    /htmx/analysis/runs/history         # Run history
GET    /htmx/analysis/settings/form        # Settings form
GET    /htmx/analysis/settings/slo         # SLO settings
```

### **Item & Feed Components**
```http
GET    /htmx/items-list                    # Items list component
GET    /htmx/feeds-options                 # Feeds dropdown options
POST   /htmx/feed-fetch-now/{feed_id}      # Trigger feed fetch
GET    /htmx/feeds-list                    # Feeds list component
GET    /htmx/feed-health/{feed_id}         # Feed health component
GET    /htmx/feed-types-options            # Feed types dropdown
POST   /htmx/feed-url-test                 # Test feed URL
GET    /htmx/feed-edit-form/{feed_id}      # Feed edit form
```

### **System Components**
```http
GET    /htmx/sources-options               # Sources dropdown
GET    /htmx/categories-options            # Categories dropdown
GET    /htmx/system-status                 # System status component
GET    /htmx/processor-configs             # Processor configs display
GET    /htmx/processor-templates           # Processor templates
GET    /htmx/processor-stats               # Processor statistics
GET    /htmx/reprocessing-status           # Reprocessing status
GET    /htmx/processor-health-details      # Processor health details
```

## 🎨 **Template Management**

### **Dynamic Templates**
```http
GET    /admin/templates                    # Templates admin interface
GET    /htmx/templates-list                # Templates list component
POST   /htmx/templates                     # Create template
PUT    /htmx/templates/{template_id}       # Update template
DELETE /htmx/templates/{template_id}       # Delete template
GET    /htmx/template-details/{template_id} # Template details
POST   /htmx/feeds/{feed_id}/template/{template_id} # Assign template to feed
DELETE /htmx/feeds/{feed_id}/template/{template_id} # Remove template from feed
POST   /htmx/templates/auto-assign         # Auto-assign templates
```

### **Template API**
```http
GET    /api/templates/                     # List templates
POST   /api/templates/create               # Create template
PUT    /api/templates/{template_id}        # Update template
POST   /api/templates/{template_id}/test   # Test template
POST   /api/templates/{template_id}/assign # Assign to feed
DELETE /api/templates/{template_id}/assign/{feed_id} # Remove assignment
DELETE /api/templates/{template_id}        # Delete template
```

---

## 📝 **Request/Response Examples**

### **Job-based Analysis (NEW)**
```bash
# Create preview job
curl -X POST /api/analysis/jobs/preview \
  -H "Content-Type: application/json" \
  -d '{
    "selection": {"mode": "latest", "count": 5},
    "parameters": {"model_tag": "gpt-4.1-nano"},
    "filters": {"unanalyzed_only": true}
  }'

# Response
{
  "success": true,
  "job_id": "abc12345",
  "estimates": {
    "item_count": 5,
    "estimated_cost_usd": 0.0025,
    "estimated_duration_minutes": 2
  }
}
```

### **Legacy Analysis**
```bash
# Start analysis run
curl -X POST /api/analysis/start \
  -H "Content-Type: application/json" \
  -d '{
    "scope": {"type": "global", "unanalyzed_only": true},
    "params": {"limit": 5, "model_tag": "gpt-4.1-nano"}
  }'
```

---

## 🏷️ **API Tags & Categories**

- **🔥 analysis-jobs** - Job-based analysis system (NEW)
- **📊 analysis** - Legacy analysis control
- **📡 feeds** - RSS feed management
- **📄 items** - Article/content management
- **🛠️ processors** - Content processing
- **📈 metrics** - Analytics and monitoring
- **🏷️ admin** - Administrative operations
- **🌐 htmx** - Web interface components
- **🩺 health** - Health checks and monitoring
- **⚙️ feature-flags** - Feature flag management

---

**🚀 Migration Notice:** The new Job-based Analysis API (`/api/analysis/jobs/*`) provides improved state management and data consistency compared to the legacy direct analysis endpoints.