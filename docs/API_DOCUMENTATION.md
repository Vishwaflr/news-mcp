# News MCP API Documentation

Generated: 2025-09-26 19:00:20

## Overview

Base URL: `http://localhost:8000`

OpenAPI Version: 3.1.0


## Other

### GET /
**Root**

**Responses:**

- `200`: Successful Response

### GET /admin
**Admin Dashboard**

**Responses:**

- `200`: Successful Response

### GET /admin/analysis
**Admin Analysis**

**Responses:**

- `200`: Successful Response

### GET /admin/database
**Admin Database**

**Responses:**

- `200`: Successful Response

### GET /admin/feeds
**Admin Feeds**

**Responses:**

- `200`: Successful Response

### GET /admin/health
**Admin Health**

**Responses:**

- `200`: Successful Response

### GET /admin/items
**Admin Items**

**Responses:**

- `200`: Successful Response

### GET /admin/processors
**Admin Processors**

**Responses:**

- `200`: Successful Response

### GET /admin/statistics
**Admin Statistics**

**Responses:**

- `200`: Successful Response

### GET /admin/templates
**Templates Page**

Template management page

**Responses:**

- `200`: Successful Response

### POST /htmx/feeds/{feed_id}/template/{template_id}
**Assign Template To Feed**

Assign a template to a feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |
| template_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### DELETE /htmx/feeds/{feed_id}/template/{template_id}
**Unassign Template From Feed**

Unassign a template from a feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |
| template_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/template-details/{template_id}
**Get Template Details**

Get template details for editing

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| template_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /htmx/templates
**Create Template**

Create a new template

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/templates-list
**Templates List**

Get list of all templates with their assignments

**Responses:**

- `200`: Successful Response

### POST /htmx/templates/auto-assign
**Auto Assign Templates**

Auto-assign templates to feeds based on URL patterns

**Responses:**

- `200`: Successful Response

### PUT /htmx/templates/{template_id}
**Update Template**

Update an existing template

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| template_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### DELETE /htmx/templates/{template_id}
**Delete Template**

Delete a template

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| template_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error


## admin

### GET /api/admin/feature-flags/
**Get All Flags**

Get status of all feature flags.

**Responses:**

- `200`: Successful Response

### POST /api/admin/feature-flags/analysis-shadow-comparison/reset
**Reset Analysis Shadow Comparison**

Reset analysis shadow comparison metrics.

**Responses:**

- `200`: Successful Response

### POST /api/admin/feature-flags/analysis-shadow/{action}
**Control Analysis Shadow**

Control analysis shadow comparison (enable/disable).

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| action | path | True |  |
| sample_rate | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/admin/feature-flags/health
**Health Check**

Health check for feature flag system.

**Responses:**

- `200`: Successful Response

### GET /api/admin/feature-flags/metrics/analysis-shadow-comparison
**Get Analysis Shadow Comparison Metrics**

Get analysis shadow comparison statistics.

**Responses:**

- `200`: Successful Response

### GET /api/admin/feature-flags/metrics/dashboard
**Get Metrics Dashboard**

Get comprehensive metrics dashboard.

**Responses:**

- `200`: Successful Response

### GET /api/admin/feature-flags/metrics/performance
**Get Performance Metrics**

Get performance metrics for repository operations.

**Responses:**

- `200`: Successful Response

### GET /api/admin/feature-flags/metrics/shadow-comparison
**Get Shadow Comparison Metrics**

Get shadow comparison statistics.

**Responses:**

- `200`: Successful Response

### POST /api/admin/feature-flags/shadow-comparison/reset
**Reset Shadow Comparison**

Reset shadow comparison metrics.

**Responses:**

- `200`: Successful Response

### GET /api/admin/feature-flags/{flag_name}
**Get Flag Status**

Get status of specific feature flag.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| flag_name | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/admin/feature-flags/{flag_name}
**Update Flag**

Update feature flag configuration.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| flag_name | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/admin/feature-flags/{flag_name}/reset-metrics
**Reset Flag Metrics**

Reset metrics for a specific flag.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| flag_name | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error


## analysis-control

### GET /api/analysis/articles
**Get Available Articles**

Get available articles for selection

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| page | query | False |  |
| limit | query | False |  |
| feed_id | query | False |  |
| unanalyzed_only | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/analysis/budget
**Get Budget Recommendations**

Get recommendations for article analysis within budget

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| budget_usd | query | True |  |
| model | query | True |  |
| avg_article_length | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/analysis/cancel/{run_id}
**Cancel Run**

Cancel an analysis run

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| run_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/analysis/cost/{model}
**Get Cost Estimate**

Get cost estimation for analyzing articles with specified model

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| model | path | True |  |
| article_count | query | True |  |
| avg_article_length | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/analysis/feeds
**Get Available Feeds**

Get available feeds for selection

**Responses:**

- `200`: Successful Response

### GET /api/analysis/history
**Get Analysis History**

Get analysis run history with pagination and filtering

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| limit | query | False |  |
| offset | query | False |  |
| status | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/analysis/models/compare
**Compare Model Costs**

Compare costs across all available analysis models

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| article_count | query | True |  |
| avg_article_length | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/analysis/pause/{run_id}
**Pause Run**

Pause an active analysis run

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| run_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/analysis/presets
**Get Presets**

Get all saved presets

**Responses:**

- `200`: Successful Response

### POST /api/analysis/presets
**Save Preset**

Save an analysis preset

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### DELETE /api/analysis/presets/{preset_id}
**Delete Preset**

Delete an analysis preset

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| preset_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/analysis/preview
**Preview Run**

Preview what a run would analyze - supports both new and legacy formats

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/analysis/quick-actions
**Get Quick Actions**

Quick actions have been removed

**Responses:**

- `200`: Successful Response

### POST /api/analysis/runs
**Create Run**

Create a new analysis run (alias for /start for frontend compatibility)

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/analysis/runs
**List Runs**

List analysis runs (active by default, or all recent runs)

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| active_only | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/analysis/start
**Start Run**

Start a new analysis run (supports both direct and job-based starts)

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/analysis/start/{run_id}
**Resume Run**

Resume/start a paused or pending analysis run

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| run_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/analysis/stats
**Get Analysis Stats**

Get overall analysis statistics

**Responses:**

- `200`: Successful Response

### GET /api/analysis/status
**Get Active Runs**

Get status of all active runs

**Responses:**

- `200`: Successful Response

### GET /api/analysis/status/{run_id}
**Get Run Status**

Get current status of an analysis run

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| run_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error


## analysis-jobs

### GET /api/analysis/jobs/
**List Active Jobs**

List all active preview jobs

**Responses:**

- `200`: Successful Response

### POST /api/analysis/jobs/preview
**Create Preview Job**

Create a preview job for analysis estimation

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/analysis/jobs/preview/legacy
**Create Preview Job Legacy**

Create a preview job using full job configuration (legacy compatibility)

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/analysis/jobs/{job_id}
**Get Job**

Get a specific job by ID

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| job_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/analysis/jobs/{job_id}/cancel
**Cancel Job**

Cancel a job and any associated analysis run

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| job_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/analysis/jobs/{job_id}/confirm
**Confirm Job For Execution**

Mark a job as confirmed and ready for execution

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| job_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/analysis/jobs/{job_id}/refresh
**Refresh Job Estimates**

Refresh estimates for an existing job

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| job_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error


## analysis-management

### GET /api/analysis/health
**Health Check**

Health check for analysis system

**Responses:**

- `200`: Successful Response

### POST /api/analysis/manager/emergency-stop
**Emergency Stop**

Emergency stop all analysis processing.

This will:
- Stop accepting new runs
- Clear the run queue
- Signal running processes to stop

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| reason | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/analysis/manager/limits
**Get Limits**

Get current system limits and their status

**Responses:**

- `200`: Successful Response

### GET /api/analysis/manager/queue
**Get Queue Status**

Get current queue status and list of queued runs

**Responses:**

- `200`: Successful Response

### POST /api/analysis/manager/queue/process
**Process Queue**

Manually trigger queue processing (for testing)

**Responses:**

- `200`: Successful Response

### DELETE /api/analysis/manager/queue/{queued_run_id}
**Cancel Queued Run**

Cancel a specific queued run

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| queued_run_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/analysis/manager/resume
**Resume Operations**

Resume operations after emergency stop.

**Responses:**

- `200`: Successful Response

### GET /api/analysis/manager/status
**Get Manager Status**

Get current RunManager status and limits

**Responses:**

- `200`: Successful Response


## categories

### GET /api/categories/
**List Categories**

**Responses:**

- `200`: Successful Response

### POST /api/categories/
**Create Category**

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| category | query | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/categories/{category_id}
**Get Category**

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| category_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### DELETE /api/categories/{category_id}
**Delete Category**

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| category_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error


## database

### POST /api/database/query
**Execute Query**

Execute a read-only SQL query

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/database/quick-queries
**Get Quick Queries**

Get predefined quick queries

**Responses:**

- `200`: Successful Response

### GET /api/database/schema/{table_name}
**Get Table Schema**

Get table schema information

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| table_name | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/database/tables
**List Tables**

Get list of available tables

**Responses:**

- `200`: Successful Response


## feature-flags

### GET /api/admin/feature-flags/
**Get All Flags**

Get status of all feature flags.

**Responses:**

- `200`: Successful Response

### POST /api/admin/feature-flags/analysis-shadow-comparison/reset
**Reset Analysis Shadow Comparison**

Reset analysis shadow comparison metrics.

**Responses:**

- `200`: Successful Response

### POST /api/admin/feature-flags/analysis-shadow/{action}
**Control Analysis Shadow**

Control analysis shadow comparison (enable/disable).

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| action | path | True |  |
| sample_rate | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/admin/feature-flags/health
**Health Check**

Health check for feature flag system.

**Responses:**

- `200`: Successful Response

### GET /api/admin/feature-flags/metrics/analysis-shadow-comparison
**Get Analysis Shadow Comparison Metrics**

Get analysis shadow comparison statistics.

**Responses:**

- `200`: Successful Response

### GET /api/admin/feature-flags/metrics/dashboard
**Get Metrics Dashboard**

Get comprehensive metrics dashboard.

**Responses:**

- `200`: Successful Response

### GET /api/admin/feature-flags/metrics/performance
**Get Performance Metrics**

Get performance metrics for repository operations.

**Responses:**

- `200`: Successful Response

### GET /api/admin/feature-flags/metrics/shadow-comparison
**Get Shadow Comparison Metrics**

Get shadow comparison statistics.

**Responses:**

- `200`: Successful Response

### POST /api/admin/feature-flags/shadow-comparison/reset
**Reset Shadow Comparison**

Reset shadow comparison metrics.

**Responses:**

- `200`: Successful Response

### GET /api/admin/feature-flags/{flag_name}
**Get Flag Status**

Get status of specific feature flag.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| flag_name | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/admin/feature-flags/{flag_name}
**Update Flag**

Update feature flag configuration.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| flag_name | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/admin/feature-flags/{flag_name}/reset-metrics
**Reset Flag Metrics**

Reset metrics for a specific flag.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| flag_name | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error


## feed-limits

### GET /api/feed-limits/feeds/{feed_id}
**Get Feed Limits**

Get limits configuration for a specific feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/feed-limits/feeds/{feed_id}
**Set Feed Limits**

Set or update limits for a specific feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### DELETE /api/feed-limits/feeds/{feed_id}
**Remove Feed Limits**

Remove limits for a specific feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/feed-limits/feeds/{feed_id}/check
**Check Analysis Allowed**

Check if an analysis is allowed for a feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |
| items_count | query | False | Number of items to process |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/feed-limits/feeds/{feed_id}/emergency-stop
**Emergency Stop Feed**

Emergency stop for a feed - immediately disable all processing

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/feed-limits/feeds/{feed_id}/enable
**Enable Feed**

Enable a disabled feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/feed-limits/feeds/{feed_id}/violations
**Get Feed Violations**

Get recent violations for a specific feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |
| days | query | False | Number of days to include |
| violation_type | query | False | Filter by violation type |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/feed-limits/presets
**Get Limit Presets**

Get predefined limit presets for common use cases

**Responses:**

- `200`: Successful Response

### GET /api/feed-limits/violations/summary
**Get Violations Summary**

Get system-wide violations summary

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| days | query | False | Number of days to include |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error


## feeds

### GET /api/feeds/
**List Feeds**

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| skip | query | False |  |
| limit | query | False |  |
| category_id | query | False |  |
| status | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/feeds/
**Create Feed**

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/feeds/json
**Create Feed Json**

Create a new feed via JSON API

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/feeds/{feed_id}
**Get Feed**

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### PUT /api/feeds/{feed_id}
**Update Feed**

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### DELETE /api/feeds/{feed_id}
**Delete Feed**

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/feeds/{feed_id}/fetch
**Fetch Feed Now**

Manually trigger an immediate fetch for a specific feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### PUT /api/feeds/{feed_id}/form
**Update Feed Form**

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error


## feeds-simple

### GET /api/feeds-simple/list
**Get Feeds List**

Get simple list of active feeds for UI dropdowns

**Responses:**

- `200`: Successful Response


## health

### GET /api/health/feeds
**Get All Feed Health**

**Responses:**

- `200`: Successful Response

### GET /api/health/feeds/{feed_id}
**Get Feed Health**

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/health/logs/{feed_id}
**Get Feed Logs**

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |
| limit | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/health/status
**Get System Status**

**Responses:**

- `200`: Successful Response

### GET /health/
**Health Check**

Basic health check endpoint.

**Responses:**

- `200`: Successful Response

### GET /health/check/{check_name}
**Single Health Check**

Run a single health check.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| check_name | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /health/detailed
**Detailed Health Check**

Detailed health check with all registered checks.

**Responses:**

- `200`: Successful Response

### GET /health/live
**Liveness Check**

Kubernetes liveness probe endpoint.

**Responses:**

- `200`: Successful Response

### GET /health/ready
**Readiness Check**

Kubernetes readiness probe endpoint.

**Responses:**

- `200`: Successful Response


## htmx

### GET /htmx/analysis/active-runs
**Get Active Runs Partial**

Render active analysis runs with dark mode styling

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/articles-live
**Get Articles Live**

Get live articles for analysis preview

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| mode | query | False | Selection mode: latest, oldest, random, unanalyzed, time_range |
| count | query | False |  |
| feed_id | query | False | Optional feed filter |
| date_from | query | False | Date filter from (YYYY-MM-DD) |
| date_to | query | False | Date filter to (YYYY-MM-DD) |
| hours | query | False | For time_range mode: hours to look back |
| unanalyzed_only | query | False | Show only unanalyzed items |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/analysis/feeds
**Get Feeds Partial**

Render feed selection checkboxes

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/feeds-list-options
**Get Feeds List Options**

Render feed options for select dropdown

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/history
**Get History Partial**

Render analysis run history with dark mode styling

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| limit | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/analysis/monitoring
**Get Monitoring Dashboard**

Render monitoring dashboard with system limits and health

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/presets
**Get Presets Partial**

Render analysis presets

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/preview-start
**Get Preview Start**

Get preview and start information for analysis

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| mode | query | False | Selection mode: latest, oldest, random |
| count | query | False |  |
| feed_id | query | False | Optional feed filter |
| date_from | query | False | Date filter from (YYYY-MM-DD) |
| date_to | query | False | Date filter to (YYYY-MM-DD) |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/analysis/quick-actions
**Get Quick Actions Partial**

Quick actions have been removed - returns empty content

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/runs/active
**Get Active Runs**

Get active analysis runs - clean implementation

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/runs/history
**Get Runs History**

Get analysis run history - clean implementation

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| page | query | False |  |
| limit | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/analysis/settings/form
**Get Settings Form**

Get analysis settings form

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/settings/slo
**Get Settings Slo**

Get SLO (Service Level Objectives) settings

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/stats
**Get Stats Partial**

Render overall statistics

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/stats-horizontal
**Get Stats Horizontal**

Get horizontal statistics display

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/status
**Get Status Partial**

Render current analysis status

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/target-selection
**Get Target Selection**

Get target selection panel with article selection options

**Responses:**

- `200`: Successful Response

### GET /htmx/categories-options
**Get Categories Options**

Get HTML options for category select dropdown.

**Responses:**

- `200`: Successful Response

### GET /htmx/feed-edit-form/{feed_id}
**Get Feed Edit Form**

Get feed edit form for modal display.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /htmx/feed-fetch-now/{feed_id}
**Fetch Feed Now Htmx**

HTMX endpoint to fetch a feed immediately and return status.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/feed-health/{feed_id}
**Get Feed Health**

Get feed health information for modal display.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/feed-types-options
**Get Feed Types Options**

Get HTML options for feed type select dropdown.

**Responses:**

- `200`: Successful Response

### POST /htmx/feed-url-test
**Test Feed Url**

Test a feed URL and return detection results.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| url | query | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/feeds-list
**Get Feeds List**

Get filtered HTML list of feeds.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| category_id | query | False |  |
| status | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/feeds-options
**Get Feeds Options**

Get HTML options for feed select dropdown.

**Responses:**

- `200`: Successful Response

### GET /htmx/items-list
**Get Items List**

Get filtered HTML list of items.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| category_id | query | False |  |
| feed_id | query | False |  |
| search | query | False |  |
| since_hours | query | False |  |
| skip | query | False |  |
| limit | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/processor-configs
**Get Processor Configs**

Get feed processor configurations table.

**Responses:**

- `200`: Successful Response

### GET /htmx/processor-health-details
**Get Processor Health Details**

Get detailed processor health monitoring dashboard.

**Responses:**

- `200`: Successful Response

### GET /htmx/processor-stats
**Get Processor Stats**

Get detailed processor statistics dashboard.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| days | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/processor-templates
**Get Processor Templates**

Get processor templates list.

**Responses:**

- `200`: Successful Response

### GET /htmx/reprocessing-status
**Get Reprocessing Status**

Get reprocessing status and history.

**Responses:**

- `200`: Successful Response

### GET /htmx/sources-options
**Get Sources Options**

Get HTML options for source select dropdown.

**Responses:**

- `200`: Successful Response

### GET /htmx/system-status
**Get System Status**

Get system status overview with key metrics.

**Responses:**

- `200`: Successful Response


## htmx-analysis-control

### GET /htmx/analysis/active-runs
**Get Active Runs Partial**

Render active analysis runs with dark mode styling

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/feeds
**Get Feeds Partial**

Render feed selection checkboxes

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/feeds-list-options
**Get Feeds List Options**

Render feed options for select dropdown

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/history
**Get History Partial**

Render analysis run history with dark mode styling

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| limit | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/analysis/monitoring
**Get Monitoring Dashboard**

Render monitoring dashboard with system limits and health

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/presets
**Get Presets Partial**

Render analysis presets

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/quick-actions
**Get Quick Actions Partial**

Quick actions have been removed - returns empty content

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/stats
**Get Stats Partial**

Render overall statistics

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/status
**Get Status Partial**

Render current analysis status

**Responses:**

- `200`: Successful Response


## htmx-analysis-feeds

### GET /htmx/analysis/feeds
**Get Feeds Partial**

Render feed selection checkboxes

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/feeds-list-options
**Get Feeds List Options**

Render feed options for select dropdown

**Responses:**

- `200`: Successful Response


## htmx-analysis-monitoring

### GET /htmx/analysis/monitoring
**Get Monitoring Dashboard**

Render monitoring dashboard with system limits and health

**Responses:**

- `200`: Successful Response


## htmx-analysis-presets

### GET /htmx/analysis/presets
**Get Presets Partial**

Render analysis presets

**Responses:**

- `200`: Successful Response


## htmx-analysis-runs

### GET /htmx/analysis/active-runs
**Get Active Runs Partial**

Render active analysis runs with dark mode styling

**Responses:**

- `200`: Successful Response

### GET /htmx/analysis/history
**Get History Partial**

Render analysis run history with dark mode styling

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| limit | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/analysis/status
**Get Status Partial**

Render current analysis status

**Responses:**

- `200`: Successful Response


## htmx-analysis-stats

### GET /htmx/analysis/stats
**Get Stats Partial**

Render overall statistics

**Responses:**

- `200`: Successful Response


## htmx-feeds

### GET /htmx/categories-options
**Get Categories Options**

Get HTML options for category select dropdown.

**Responses:**

- `200`: Successful Response

### GET /htmx/feed-edit-form/{feed_id}
**Get Feed Edit Form**

Get feed edit form for modal display.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /htmx/feed-fetch-now/{feed_id}
**Fetch Feed Now Htmx**

HTMX endpoint to fetch a feed immediately and return status.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/feed-health/{feed_id}
**Get Feed Health**

Get feed health information for modal display.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/feed-types-options
**Get Feed Types Options**

Get HTML options for feed type select dropdown.

**Responses:**

- `200`: Successful Response

### POST /htmx/feed-url-test
**Test Feed Url**

Test a feed URL and return detection results.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| url | query | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/feeds-list
**Get Feeds List**

Get filtered HTML list of feeds.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| category_id | query | False |  |
| status | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/feeds-options
**Get Feeds Options**

Get HTML options for feed select dropdown.

**Responses:**

- `200`: Successful Response

### GET /htmx/sources-options
**Get Sources Options**

Get HTML options for source select dropdown.

**Responses:**

- `200`: Successful Response


## htmx-items

### GET /htmx/items-list
**Get Items List**

Get filtered HTML list of items.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| category_id | query | False |  |
| feed_id | query | False |  |
| search | query | False |  |
| since_hours | query | False |  |
| skip | query | False |  |
| limit | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error


## htmx-processors

### GET /htmx/processor-configs
**Get Processor Configs**

Get feed processor configurations table.

**Responses:**

- `200`: Successful Response

### GET /htmx/processor-health-details
**Get Processor Health Details**

Get detailed processor health monitoring dashboard.

**Responses:**

- `200`: Successful Response

### GET /htmx/processor-stats
**Get Processor Stats**

Get detailed processor statistics dashboard.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| days | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /htmx/processor-templates
**Get Processor Templates**

Get processor templates list.

**Responses:**

- `200`: Successful Response

### GET /htmx/reprocessing-status
**Get Reprocessing Status**

Get reprocessing status and history.

**Responses:**

- `200`: Successful Response


## htmx-system

### GET /htmx/system-status
**Get System Status**

Get system status overview with key metrics.

**Responses:**

- `200`: Successful Response


## items

### GET /api/items/
**List Items**

List items with optional filtering.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| skip | query | False |  |
| limit | query | False |  |
| category_id | query | False |  |
| feed_id | query | False |  |
| since_hours | query | False |  |
| search | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/items/analysis/stats
**Get Analysis Stats**

Get analysis statistics

**Responses:**

- `200`: Successful Response

### GET /api/items/analyzed
**List Analyzed Items**

Get items with analysis data, optionally filtered by impact, sentiment, or urgency

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| impact_min | query | False | Minimum impact score (0-1) |
| sentiment | query | False | Sentiment filter |
| urgency_min | query | False | Minimum urgency score (0-1) |
| limit | query | False | Maximum items to return |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/items/{item_id}
**Get Item**

Get a single item by ID.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| item_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/items/{item_id}/analysis
**Get Item Analysis**

Get analysis data for a specific item

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| item_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error


## metrics

### GET /api/metrics/costs/breakdown
**Get Cost Breakdown**

Get cost breakdown by feed and model

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| days | query | False | Number of days to include |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/metrics/feeds
**Get All Feeds Summary**

Get summary metrics for all feeds

**Responses:**

- `200`: Successful Response

### GET /api/metrics/feeds/{feed_id}
**Get Feed Metrics**

Get metrics for a specific feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |
| days | query | False | Number of days to include |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/metrics/feeds/{feed_id}/summary
**Get Feed Summary**

Get summary metrics for a feed (today + last 7 days)

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/metrics/performance/queue
**Get Queue Performance**

Get queue processing performance metrics

**Responses:**

- `200`: Successful Response

### GET /api/metrics/system/overview
**Get System Overview**

Get system-wide metrics overview

**Responses:**

- `200`: Successful Response

### POST /api/metrics/test/record
**Record Test Metrics**

Test endpoint to record sample metrics

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | query | True |  |
| items_processed | query | False |  |
| cost_usd | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error


## processors

### GET /api/processors/config/{feed_id}
**Get Feed Processor Config**

Get processor configuration for a specific feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/processors/config/{feed_id}
**Create Or Update Feed Processor Config**

Create or update processor configuration for a feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |
| processor_type | query | True |  |
| is_active | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### DELETE /api/processors/config/{feed_id}
**Delete Feed Processor Config**

Delete processor configuration for a feed (revert to default)

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/processors/health
**Get Processor Health**

Get overall processor health metrics

**Responses:**

- `200`: Successful Response

### POST /api/processors/reprocess/feed/{feed_id}
**Reprocess Feed Items**

Reprocess items from a specific feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |
| limit | query | False |  |
| force_all | query | False | Reprocess all items, not just failed ones |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/processors/reprocess/item/{item_id}
**Reprocess Single Item**

Reprocess a single item

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| item_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/processors/stats
**Get Processing Statistics**

Get processing statistics

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | query | False |  |
| days | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/processors/templates
**Get Processor Templates**

Get all processor templates

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| skip | query | False |  |
| limit | query | False |  |
| is_active | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/processors/templates
**Create Processor Template**

Create a new processor template

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | query | True |  |
| processor_type | query | True |  |
| description | query | False |  |
| is_active | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### PUT /api/processors/templates/{template_id}
**Update Processor Template**

Update a processor template

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| template_id | path | True |  |
| name | query | False |  |
| processor_type | query | False |  |
| is_active | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### DELETE /api/processors/templates/{template_id}
**Delete Processor Template**

Delete a processor template

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| template_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/processors/types
**Get Processor Types**

Get all available processor types

**Responses:**

- `200`: Successful Response

### POST /api/processors/validate-config
**Validate Processor Config**

Validate a processor configuration without saving it

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| processor_type | query | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error


## scheduler

### GET /api/scheduler/heartbeat
**Get Scheduler Heartbeat**

Get scheduler heartbeat and health metrics

**Responses:**

- `200`: Successful Response

### POST /api/scheduler/interval
**Set Global Interval**

Set global fetch interval for all active feeds

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/scheduler/interval/{feed_id}
**Set Feed Interval**

Set fetch interval for a specific feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/scheduler/pause
**Pause Scheduler**

Pause scheduler for all feeds or specific feed

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/scheduler/resume
**Resume Scheduler**

Resume scheduler for all feeds or specific feed

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/scheduler/status
**Get Scheduler Status**

Get current scheduler status and configuration

**Responses:**

- `200`: Successful Response


## sources

### GET /api/sources/
**List Sources**

**Responses:**

- `200`: Successful Response

### POST /api/sources/
**Create Source**

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| source | query | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/sources/{source_id}
**Get Source**

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| source_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### DELETE /api/sources/{source_id}
**Delete Source**

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| source_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error


## statistics

### GET /api/statistics/dashboard
**Get Dashboard Stats**

Get comprehensive dashboard statistics

**Responses:**

- `200`: Successful Response

### GET /api/statistics/export/csv
**Export Statistics Csv**

Export statistics as CSV

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| table | query | True | Table to export (feeds, items, etc.) |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/statistics/feed/{feed_id}
**Get Feed Details**

Get detailed statistics for a specific feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error


## system

### GET /api/system/dependencies/{service_id}
**Get service dependencies**

Get dependency information for a specific service

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| service_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/system/health
**System health check**

Run health checks on all services

**Responses:**

- `200`: Successful Response

### GET /api/system/registry
**Get service registry configuration**

Get service registry configuration and dependency information

**Responses:**

- `200`: Successful Response

### GET /api/system/services
**Get all service status**

Get status of all News MCP services

**Responses:**

- `200`: Successful Response

### POST /api/system/services/start
**Start all services**

Start all services or specific services

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/system/services/stop
**Stop all services**

Stop all services

**Responses:**

- `200`: Successful Response

### POST /api/system/services/{service_id}/restart
**Restart specific service**

Restart a specific service

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| service_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### GET /api/system/services/{service_id}/status
**Get specific service status**

Get status of a specific service

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| service_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error


## templates

### GET /api/templates/
**List Templates**

List dynamic feed templates with optional filtering

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| assigned_to_feed_id | query | False |  |
| active_only | query | False |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/templates/create
**Create Template**

Create a new dynamic feed template

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### PUT /api/templates/{template_id}
**Update Template**

Update an existing template

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| template_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### DELETE /api/templates/{template_id}
**Delete Template**

Delete a template (if not builtin)

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| template_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/templates/{template_id}/assign
**Assign Template**

Assign a template to a feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| template_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### DELETE /api/templates/{template_id}/assign/{feed_id}
**Unassign Template**

Unassign a template from a feed

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| template_id | path | True |  |
| feed_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

### POST /api/templates/{template_id}/test
**Test Template**

Test a template against sample content

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| template_id | path | True |  |

**Responses:**

- `200`: Successful Response
- `422`: Validation Error


## user-settings

### GET /api/user-settings/default-params
**Get Default Params**

Get default analysis parameters from database

**Responses:**

- `200`: Successful Response

### POST /api/user-settings/default-params
**Save Default Params**

Save default analysis parameters to database

**Responses:**

- `200`: Successful Response
- `422`: Validation Error

