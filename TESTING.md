# Testing Guide

This document outlines testing strategies and procedures for the News MCP system, including repository migration testing and performance validation.

## 🧪 Testing Strategy

### Testing Layers

1. **Unit Tests**: Individual components and functions
2. **Integration Tests**: Repository pattern vs. legacy comparison
3. **Performance Tests**: Database query optimization and SLO validation
4. **Shadow Testing**: A/B comparison between implementations
5. **End-to-End Tests**: Complete user workflows

## 🔄 Repository Migration Testing

### 🆕 Enhanced Feature Flag Testing (2025-09-22)

The repository migration uses feature flags with **circuit breaker protection** for safe rollout. Test at different rollout percentages with automatic emergency disable:

#### Repository Coverage
- **ItemsRepo**: Timeline & search operations
- **FeedsRepo**: Feed management with feeds-specific shadow comparison
- **AnalysisRepo**: Worker-based analysis processing with OpenAI integration
- **Shadow Compare**: A/B testing framework (10% sampling active)

```bash
# Test current flag status
curl "http://localhost:8000/api/admin/feature-flags/items_repo"

# Start with 5% rollout
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -H "Content-Type: application/json" \
  -d '{"status": "canary", "rollout_percentage": 5}'

# Test repository path (include user header to trigger feature flag)
curl "http://localhost:8000/api/items?limit=10" \
  -H "X-User-ID: test-user-repo"

# Test legacy path (no user header)
curl "http://localhost:8000/api/items?limit=10"
```

### 🔍 Enhanced Shadow Comparison Testing

🆕 **Repository-Specific Shadow Comparison**: Monitor A/B testing between old and new implementations with specialized comparison logic.

#### 1. **FeedsRepo Shadow Testing** (`app/utils/feeds_shadow_compare.py`)
```python
# Enable feeds-specific shadow comparison
from app.utils.feeds_shadow_compare import feeds_shadow_comparer
feeds_shadow_comparer.enable(sample_rate=0.1)  # 10% sampling

# Test different feed operations
feeds_shadow_comparer.compare_feed_list(filters, legacy_result, repo_result)
feeds_shadow_comparer.compare_feed_details(feed_id, legacy_result, repo_result)
feeds_shadow_comparer.compare_feed_health(feed_id, legacy_result, repo_result)
feeds_shadow_comparer.compare_feed_crud("create", feed_data, legacy_result, repo_result)

# Check results
stats = feeds_shadow_comparer.get_comparison_stats()
mismatches = feeds_shadow_comparer.get_recent_mismatches(hours=1)
```

#### 2. **AnalysisRepo Worker Testing**
```bash
# Start analysis worker with verbose logging
./scripts/start-worker.sh --verbose

# Test analysis run
curl -X POST "http://localhost:8000/api/analysis/start/26"

# Monitor worker processing
tail -f logs/worker.log | grep -E "(processed|ERROR|OpenAI)"

# Check worker performance
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db -c "
SELECT state, COUNT(*) FROM analysis_run_items WHERE run_id = 26 GROUP BY state;"
```

#### 3. **General Shadow Comparison Testing

```bash
# Enable shadow comparison
curl -X POST "http://localhost:8000/api/admin/feature-flags/shadow_compare" \
  -H "Content-Type: application/json" \
  -d '{"status": "on", "rollout_percentage": 20}'

# View comparison results
curl "http://localhost:8000/api/admin/feature-flags/metrics/shadow-comparison"

# Expected output:
{
  "total_comparisons": 150,
  "match_rate": 0.98,
  "mismatch_count": 3,
  "error_count": 0,
  "performance": {
    "old_avg_ms": 45.2,
    "new_avg_ms": 32.1,
    "improvement_percent": 29.0
  }
}
```

## ⚡ Performance Testing

### Database Performance Validation

Run the index reality check to validate query performance:

```bash
# Basic performance check
python scripts/index_check.py

# Create missing indexes if needed
python scripts/index_check.py --create-missing
```

**Expected SLOs:**
- Global timeline queries: <100ms
- Feed-specific queries: <50ms
- Sentiment filtering: <200ms
- Complex multi-filter queries: <300ms
- Search queries: <500ms
- Count queries: <50ms

### Load Testing

Test system performance under load:

```bash
# Install testing tools
pip install locust

# Basic load test
locust -f tests/load_test.py --host http://localhost:8000
```

Example load test file (`tests/load_test.py`):

```python
from locust import HttpUser, task, between

class NewsAPIUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Test with repository enabled
        self.client.headers.update({"X-User-ID": "load-test-user"})

    @task(3)
    def get_items_list(self):
        self.client.get("/api/items?limit=20")

    @task(2)
    def get_feeds(self):
        self.client.get("/api/feeds")

    @task(1)
    def get_health(self):
        self.client.get("/api/health")

    @task(1)
    def htmx_items(self):
        self.client.get("/htmx/items-list?limit=10")
```

## 🧪 Manual Testing Procedures

### 1. Basic Functionality Test

```bash
# Start services
uvicorn app.main:app --reload &
python jobs/scheduler_manager.py start --debug &

# Add test feed
curl -X POST "http://localhost:8000/api/feeds" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://feeds.bbci.co.uk/news/rss.xml",
    "title": "BBC News Test Feed"
  }'

# Wait for fetch (or trigger manually)
sleep 60

# Test items retrieval
curl "http://localhost:8000/api/items?limit=5"

# Run available test scripts
python test_mcp_server.py          # MCP server functionality
python test_repo_manual.py         # Repository pattern tests
python test_simple_repo.py         # Simple repository tests
python test_monitoring.py          # Monitoring system tests
python test_system_status.py       # System status tests

# Run pytest test suite
python -m pytest tests/ -v
```

### 2. Repository vs Legacy Comparison

```bash
# Test repository implementation
time curl "http://localhost:8000/api/items?limit=50" \
  -H "X-User-ID: repo-test" > repo_output.json

# Test legacy implementation
time curl "http://localhost:8000/api/items?limit=50" > legacy_output.json

# Compare results (should be functionally identical)
diff <(jq 'sort_by(.id)' repo_output.json) <(jq 'sort_by(.id)' legacy_output.json)
```

### 3. Feature Flag Rollout Test

```bash
# Start with 10% rollout
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -d '{"status": "canary", "rollout_percentage": 10}'

# Test 100 requests to verify distribution
for i in {1..100}; do
  curl -s "http://localhost:8000/api/items?limit=1" \
    -H "X-User-ID: user-$i" >> test_results.log
done

# Analyze distribution (should be ~10% repository, 90% legacy)
grep -c "repository" test_results.log
```

### 4. Error Handling Test

```bash
# Test circuit breaker (force errors)
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -d '{"status": "canary", "rollout_percentage": 100}'

# Simulate database issues (requires test environment)
# Stop PostgreSQL temporarily to trigger fallback

# Verify emergency disable activated
curl "http://localhost:8000/api/admin/feature-flags/items_repo"
# Should show status: "emergency_off"
```

## 🔍 Debugging Tests

### Performance Debugging

```bash
# Monitor real-time performance
python monitoring_dashboard.py --mode check

# Start live monitoring dashboard
python monitoring_dashboard.py

# Check query execution plans
PGPASSWORD=news_password psql -h localhost -U news_user -d news_db \
  -c "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM items ORDER BY created_at DESC LIMIT 50;"
```

### Feature Flag Debugging

```bash
# View detailed metrics
curl "http://localhost:8000/api/admin/feature-flags/metrics/dashboard" | jq

# Reset metrics for clean test
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo/reset-metrics"

# Check shadow comparison logs
curl "http://localhost:8000/api/admin/feature-flags/metrics/shadow-comparison" | jq
```

## 📊 Test Data Management

### Setting Up Test Data

```bash
# Add multiple test feeds
feeds=(
  "https://feeds.bbci.co.uk/news/rss.xml"
  "https://rss.cnn.com/rss/edition.rss"
  "https://feeds.reuters.com/reuters/topNews"
)

for feed in "${feeds[@]}"; do
  curl -X POST "http://localhost:8000/api/feeds" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"$feed\", \"title\": \"Test Feed\"}"
done

# Trigger immediate fetch
curl -X POST "http://localhost:8000/api/admin/fetch-all-feeds"
```

### Cleaning Test Data

```bash
# Remove test feeds
curl -X DELETE "http://localhost:8000/api/feeds/{feed_id}"

# Clear metrics
curl -X POST "http://localhost:8000/api/admin/feature-flags/shadow-comparison/reset"
```

## 🚨 Critical Test Scenarios

### 1. Emergency Rollback Test

```bash
# Set high error rate scenario
# (This would be done in test environment)

# Verify automatic emergency disable
curl "http://localhost:8000/api/admin/feature-flags/health"

# Manual emergency disable
curl -X POST "http://localhost:8000/api/admin/feature-flags/items_repo" \
  -d '{"status": "emergency_off"}'
```

### 2. Data Consistency Test

```bash
# Run shadow comparison with high sampling
curl -X POST "http://localhost:8000/api/admin/feature-flags/shadow_compare" \
  -d '{"status": "on", "rollout_percentage": 100}'

# Generate traffic
for i in {1..50}; do
  curl "http://localhost:8000/api/items?limit=20&page=$((i % 5))" \
    -H "X-User-ID: consistency-test-$i" &
done
wait

# Check for mismatches (should be 0%)
curl "http://localhost:8000/api/admin/feature-flags/metrics/shadow-comparison" | \
  jq '.mismatch_count, .match_rate'
```

### 3. Performance Regression Test

```bash
# Baseline legacy performance
for i in {1..20}; do
  time curl -s "http://localhost:8000/api/items?limit=50" > /dev/null
done

# Test repository performance
for i in {1..20}; do
  time curl -s "http://localhost:8000/api/items?limit=50" \
    -H "X-User-ID: perf-test-$i" > /dev/null
done

# Should show improvement or at least no regression
```

## 📋 Test Checklist

### Pre-Migration Testing

- [ ] Database indexes exist and perform within SLO
- [ ] Feature flag system operational
- [ ] Shadow comparison system working
- [ ] Monitoring dashboard functional
- [ ] Emergency rollback procedure tested

### During Migration Testing

- [ ] Shadow comparison shows >95% match rate
- [ ] Performance improved or maintained
- [ ] Error rate <5%
- [ ] No data inconsistencies
- [ ] Circuit breaker functioning

### Post-Migration Testing

- [ ] All endpoints functional with repository pattern
- [ ] Performance meets or exceeds baseline
- [ ] Legacy code can be safely removed
- [ ] Documentation updated
- [ ] Monitoring adapted for new architecture

## 🎯 Success Criteria

### Repository Migration Success

1. **Functionality**: 100% feature parity with legacy implementation
2. **Performance**: <100ms for 95% of queries
3. **Reliability**: <1% error rate under normal load
4. **Data Integrity**: 100% consistency in shadow comparisons
5. **Rollback**: <30 seconds emergency rollback time

### Quality Gates

- All performance tests pass SLO requirements
- Shadow comparison shows >98% match rate
- Load testing shows system handles 10x normal traffic
- Zero data loss or corruption
- Complete monitoring coverage

---

🎯 **Remember**: The goal is zero-downtime migration with the ability to instantly rollback if any issues arise.