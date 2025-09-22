# Monitoring & Feature Flags Guide

This guide covers the comprehensive monitoring system and feature flag infrastructure for the News MCP repository migration.

## 🎛️ Feature Flag System

### Overview

The feature flag system enables safe, gradual migration from Raw SQL to Repository Pattern with automatic fallback capabilities. The system features circuit breaker protection, emergency auto-disable, and real-time monitoring.

### Core Components

1. **Feature Flags Manager** (`app/utils/feature_flags.py`)
   - ✅ **NEW**: Enhanced with circuit breaker emergency disable
   - ✅ **NEW**: Error rate and latency threshold monitoring
   - ✅ **NEW**: Deterministic user-based rollout hashing
2. **Shadow Comparison Framework** (`app/utils/shadow_compare.py`)
   - ✅ **NEW**: Feeds-specific shadow comparison (`app/utils/feeds_shadow_compare.py`)
   - ✅ **NEW**: Thread-safe comparison tracking
   - ✅ **NEW**: Detailed mismatch analysis and export
3. **Performance Monitoring** (`app/utils/monitoring.py`)
4. **Admin API** (`app/api/feature_flags_admin.py`)

### 🆕 Latest Enhancements (2025-09-22)

#### Emergency Auto-Disable
```python
# Circuit breaker triggers on:
error_rate > 0.05           # 5% error rate
latency > baseline * 1.5    # 50% latency increase
consecutive_failures > 3    # 3 consecutive failures
```

#### Repository-Specific Shadow Comparison
- **ItemsRepo**: General shadow comparison (`app/utils/shadow_compare.py`)
- **FeedsRepo**: Specialized feeds comparison (`app/utils/feeds_shadow_compare.py`)
- **AnalysisRepo**: Worker-based validation with analysis queue

### Feature Flag Configuration

#### Environment Setup

```env
# Feature flags in JSON format
FEATURE_FLAGS_JSON={"items_repo":{"status":"canary","rollout_percentage":5,"emergency_threshold":0.05}}
```

#### API Configuration

```bash
# Check current flags
curl "http://localhost:8000/api/admin/feature-flags/"

# Update flag
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "canary",
    "rollout_percentage": 25
  }'
```

### Flag States

| Status | Description | Rollout % | Auto-Fallback | Emergency Trigger |
|--------|-------------|-----------|---------------|-------------------|
| `off` | Feature disabled | 0% | No | Manual |
| `canary` | Gradual rollout | 5-95% | Yes | Auto + Manual |
| `on` | Fully enabled | 100% | Yes | Auto + Manual |
| `emergency_off` | ⚠️ Emergency disabled | 0% | No | **Auto-triggered** |

### 🆕 Current Repository Flags

```bash
# Default repository configurations (app/utils/feature_flags.py)
items_repo: OFF (10% rollout, 5% error threshold, 30% latency threshold)
feeds_repo: OFF (5% rollout)
analysis_repo: OFF (15% rollout)
shadow_compare: CANARY (10% rollout)
```

### Circuit Breaker Mechanism

Automatic emergency disable triggers when:
- **Error Rate** > 5% over 10 requests
- **Latency Increase** > 30% compared to baseline
- **Consecutive Failures** > 3

```python
# Emergency conditions
if error_rate > 0.05:
    flag.emergency_disable("high_error_rate")
if new_latency > baseline_latency * 1.3:
    flag.emergency_disable("performance_regression")
```

## 📊 Shadow Comparison System

### Purpose

Compare old (Raw SQL) vs new (Repository) implementations in real-time without affecting users.

### 🆕 Repository-Specific Comparisons

#### 1. **FeedsRepo Shadow Comparison** (`app/utils/feeds_shadow_compare.py`)
```python
# Specialized for feeds operations
- compare_feed_list()      # Feed listing with filters
- compare_feed_details()   # Individual feed details
- compare_feed_health()    # Feed health metrics
- compare_feed_crud()      # Create/Update/Delete operations

# Features:
- Thread-safe comparison tracking
- Datetime tolerance (1 second)
- Numeric tolerance (1% for rates)
- Field-by-field difference analysis
```

#### 2. **ItemsRepo Shadow Comparison** (`app/utils/shadow_compare.py`)
```python
# General purpose comparison framework
- Deep content comparison
- Performance comparison (latency, resource usage)
- Error rate tracking
- HTML/DOM comparison for HTMX endpoints
```

#### 3. **AnalysisRepo Validation**
```python
# Worker-based validation
- Queue processing comparison
- OpenAI API response consistency
- Analysis result accuracy
- Worker performance metrics
```

### Configuration

```bash
# Enable general shadow comparison (10% sampling)
curl -X POST "http://localhost:8000/api/admin/feature-flags/shadow_compare" \
  -d '{"status": "on", "rollout_percentage": 10}'

# Enable feeds-specific shadow comparison
feeds_shadow_comparer.enable(sample_rate=0.1)  # 10% sampling

# Check shadow comparison status
curl "http://localhost:8000/api/admin/feature-flags/metrics/shadow-comparison"
```

### Comparison Metrics

```json
{
  "total_comparisons": 1547,
  "match_rate": 0.987,
  "mismatch_count": 20,
  "error_count": 3,
  "performance": {
    "old_avg_ms": 45.2,
    "new_avg_ms": 32.1,
    "p95_old_ms": 89.3,
    "p95_new_ms": 67.8,
    "improvement_percent": 29.0
  },
  "mismatches": [
    {
      "timestamp": "2025-01-01T12:00:00Z",
      "endpoint": "/api/items",
      "parameters": {"limit": 20, "feed_id": 5},
      "difference": "item_count_mismatch",
      "old_count": 18,
      "new_count": 20
    }
  ]
}
```

### Analysis Types

1. **Content Comparison**: Deep comparison of response data
2. **Performance Comparison**: Latency and resource usage
3. **Error Rate Comparison**: Success/failure rates
4. **HTML Comparison**: For HTMX endpoints, parse and compare DOM

## ⚡ Performance Monitoring

### Real-time Dashboard

```bash
# Start monitoring dashboard
python monitoring_dashboard.py

# Single status check
python monitoring_dashboard.py --mode check

# Use curses interface (if available)
python monitoring_dashboard.py --mode curses
```

Output:
```
🎛️  REPOSITORY CUTOVER DASHBOARD
==================================================

📊 Feature Flags:
  items_repo: canary (25% rollout)
    Success: 1,245, Errors: 12 (0.9% error rate)
  shadow_compare: on (10% rollout)
    Success: 156, Errors: 0 (0.0% error rate)

🔍 Shadow Comparison:
  Total comparisons: 156
  Match rate: 98.7%
  Mismatches: 2
  Errors: 0
  Performance: 45.2ms → 32.1ms (+29.0%)

⏱️  Performance Summary:
  items.list: 32.1ms avg, 67.8ms p95 (99.2% success)
  items.count: 15.4ms avg, 28.9ms p95 (100.0% success)
  items.search: 89.3ms avg, 156.7ms p95 (98.8% success)
```

### Metrics Collection

```python
# Custom metrics in code
from app.utils.monitoring import repo_monitor

# Monitor repository queries
with repo_monitor.monitor_query("items", "list", {"has_filters": True}):
    result = await items_repo.query(query)

# Record query results
repo_monitor.record_query_result("items", "list", len(result))
```

### Performance SLOs

| Operation | Target P95 | Alert Threshold |
|-----------|------------|-----------------|
| Timeline queries | <100ms | >150ms |
| Feed queries | <50ms | >75ms |
| Search queries | <500ms | >750ms |
| Count queries | <50ms | >75ms |
| Complex filters | <300ms | >450ms |

### Alerting

Automatic alerts trigger on:
- P95 latency exceeds SLO by 50%
- Error rate > 1% over 50 requests
- Shadow comparison mismatch rate > 5%
- Emergency flag disable events

### Testing Monitoring System

```bash
# Test monitoring infrastructure
python test_monitoring.py

# Verify metrics collection
python monitoring_dashboard.py --mode check
```

## 🔍 Index Performance Monitoring

### Database Reality Check

```bash
# Run comprehensive index analysis
python scripts/index_check.py

# Auto-create missing indexes
python scripts/index_check.py --create-missing
```

### Expected Output

```markdown
# Index Reality Check Report
Generated: 2025-01-01T12:00:00.000000

## Index Status
✅ Existing indexes: 7
❌ Missing indexes: 0

## Performance Test Results
✅ Passed: 6
❌ Failed: 0

### Performance Summary
| Test | Duration (ms) | Target (ms) | Status | Rows |
|------|---------------|-------------|--------|------|
| Global timeline (no filters) | 45.2 | 100 | ✅ | 50 |
| Feed timeline | 23.1 | 50 | ✅ | 50 |
| Sentiment filter | 156.7 | 200 | ✅ | 50 |
| Complex filter | 234.8 | 300 | ✅ | 50 |
| Search query | 445.3 | 500 | ✅ | 50 |
| Count query | 12.4 | 50 | ✅ | 5400 |
```

### Required Indexes

```sql
-- Timeline performance
CREATE INDEX CONCURRENTLY items_feed_timeline_idx ON items (feed_id, created_at DESC);
CREATE INDEX CONCURRENTLY items_published_idx ON items (published DESC NULLS LAST);

-- Duplicate detection
CREATE UNIQUE INDEX CONCURRENTLY items_content_hash_idx ON items (content_hash);

-- Analysis joins
CREATE INDEX CONCURRENTLY item_analysis_item_id_idx ON item_analysis (item_id);
CREATE INDEX CONCURRENTLY item_analysis_sentiment_idx ON item_analysis (sentiment_label);

-- Category filtering
CREATE INDEX CONCURRENTLY feed_categories_feed_id_idx ON feed_categories (feed_id);
CREATE INDEX CONCURRENTLY feed_categories_category_id_idx ON feed_categories (category_id);
```

## 🚨 Emergency Procedures

### Immediate Rollback

```bash
# Emergency disable all new features
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -d '{"status": "emergency_off"}'

# Verify rollback
curl "http://localhost:8000/api/admin/feature-flags/health"
```

### Performance Issues

```bash
# Check current performance
curl "http://localhost:8000/api/admin/feature-flags/metrics/performance"

# Reset metrics for clean slate
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo/reset-metrics"

# Re-enable cautiously
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -d '{"status": "canary", "rollout_percentage": 5}'
```

### Data Consistency Issues

```bash
# Check shadow comparison for mismatches
curl "http://localhost:8000/api/admin/feature-flags/metrics/shadow-comparison"

# If mismatches > 5%, investigate:
# 1. Check database synchronization
python scripts/index_check.py

# 2. Verify repository implementation
# Review app/repositories/items_repo.py

# 3. Emergency disable if critical
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -d '{"status": "emergency_off"}'
```

## 📈 Rollout Strategy

### Phase 1: Canary (5% rollout)
```bash
# Enable with minimal traffic
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -d '{"status": "canary", "rollout_percentage": 5}'

# Monitor for 24 hours
# Success criteria: <1% error rate, <5% mismatches
```

### Phase 2: Limited (25% rollout)
```bash
# Increase rollout if Phase 1 successful
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -d '{"status": "canary", "rollout_percentage": 25}'

# Monitor for 12 hours
# Success criteria: <0.5% error rate, <2% mismatches
```

### Phase 3: Majority (75% rollout)
```bash
# Major rollout
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -d '{"status": "canary", "rollout_percentage": 75}'

# Monitor for 6 hours
# Success criteria: <0.1% error rate, <1% mismatches
```

### Phase 4: Full Deployment (100%)
```bash
# Complete migration
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -d '{"status": "on", "rollout_percentage": 100}'

# Monitor for 48 hours before removing legacy code
```

## 🔧 Advanced Configuration

### Custom User Routing

```python
# Route specific users to repository
def get_user_routing(user_id: str) -> bool:
    # VIP users get new implementation first
    if user_id.startswith("admin-"):
        return True
    # Test users for extended testing
    if user_id.startswith("test-"):
        return True
    # Normal feature flag logic
    return is_feature_enabled("items_repo", user_id)
```

### Weighted Rollout

```python
# Different weights for different endpoints
ENDPOINT_WEIGHTS = {
    "/api/items": 0.25,        # 25% rollout for main endpoint
    "/htmx/items-list": 0.50,  # 50% rollout for HTMX
    "/api/items/search": 0.10, # 10% rollout for search
}
```

### Performance Thresholds

```python
# Custom thresholds per operation
PERFORMANCE_THRESHOLDS = {
    "items.list": {"p95_ms": 100, "error_rate": 0.01},
    "items.search": {"p95_ms": 500, "error_rate": 0.02},
    "items.count": {"p95_ms": 50, "error_rate": 0.005},
}
```

## 📊 Monitoring Best Practices

### 1. Start Small
- Begin with 5% rollout
- Monitor continuously for 24 hours
- Look for error patterns

### 2. Monitor Key Metrics
- Error rates (< 1%)
- Latency (P95 < target + 50%)
- Data consistency (>95% match rate)
- Resource usage

### 3. Automate Decisions
- Let circuit breaker handle emergencies
- Use shadow comparison for validation
- Trust the metrics over intuition

### 4. Communication
- Alert stakeholders on flag changes
- Document rollout decisions
- Share metrics regularly

### 5. Rollback Plan
- Always have emergency rollback ready
- Test rollback procedures regularly
- Keep legacy code until 100% confidence

## 🎯 Success Criteria

### Technical Metrics
- ✅ Error rate < 0.5%
- ✅ P95 latency meets SLOs
- ✅ Shadow comparison >98% match rate
- ✅ Zero data loss or corruption
- ✅ Circuit breaker never triggers

### Business Metrics
- ✅ No user-reported issues
- ✅ Performance improved or maintained
- ✅ System stability maintained
- ✅ Monitoring coverage complete

---

🎛️ **Remember**: The goal is risk-free migration with the ability to instantly rollback if any issues arise. Trust the monitoring, respect the metrics, and migrate gradually.