# Feature Flags Documentation

## Overview

The News MCP system uses feature flags for safe, gradual rollout of new features and repository migrations.

## Current Feature Flags

### Repository Migration Flags

| Flag Name | Description | Current Status | Rollout % |
|-----------|-------------|----------------|----------|
| `use_repository_pattern` | Enable new repository pattern | Enabled | 100% |
| `enable_shadow_comparison` | A/B testing old vs new code | Enabled | 100% |
| `use_feeds_repo` | Use new feeds repository | Enabled | 95% |
| `use_items_repo` | Use new items repository | Enabled | 95% |
| `use_analysis_repo` | Use new analysis repository | Enabled | 95% |
| `use_categories_repo` | Use new categories repository | Enabled | 90% |
| `use_sources_repo` | Use new sources repository | Enabled | 90% |

### Performance Monitoring Flags

| Flag Name | Description | Current Status |
|-----------|-------------|----------------|
| `enable_performance_monitoring` | Track P50/P95/P99 metrics | Enabled |
| `enable_circuit_breaker` | Auto-disable on high error rate | Enabled |
| `enable_trace_logging` | Detailed trace logging | Disabled |
| `enable_query_optimization` | Automatic query optimization | Enabled |

### Feature Rollout Flags

| Flag Name | Description | Current Status |
|-----------|-------------|----------------|
| `enable_ai_analysis` | AI-powered content analysis | Enabled |
| `enable_dynamic_templates` | Hot-reload feed templates | Enabled |
| `enable_feed_limits` | Rate limiting per feed | Enabled |
| `enable_htmx_ui` | Modern HTMX interface | Enabled |
| `enable_mcp_server` | MCP protocol support | Enabled |

## Configuration

### Environment Variables

```bash
# Feature flag configuration
FEATURE_FLAG_ROLLOUT_PERCENTAGE=95
FEATURE_FLAG_SHADOW_MODE=true
FEATURE_FLAG_CIRCUIT_BREAKER_THRESHOLD=5
FEATURE_FLAG_LATENCY_THRESHOLD_MS=300
```

### Programmatic Access

```python
from app.utils.feature_flags import FeatureFlags

# Check if a feature is enabled
if FeatureFlags.is_enabled('use_repository_pattern'):
    # Use new repository pattern
    result = feeds_repo.get_all_feeds()
else:
    # Fallback to old implementation
    result = legacy_get_feeds()

# Check rollout percentage
rollout = FeatureFlags.get_rollout_percentage('use_feeds_repo')
print(f"Feeds repository rollout: {rollout}%")
```

## Admin Interface

### Viewing Feature Flags

1. Navigate to `/admin/feature-flags`
2. View all flags with current status
3. Monitor performance metrics per flag

### Modifying Feature Flags

```bash
# Via API
curl -X PUT http://localhost:8000/api/feature-flags/use_feeds_repo \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "rollout_percentage": 100}'

# Via CLI
python -m app.utils.feature_flags set use_feeds_repo --enabled --rollout 100
```

## Circuit Breaker Rules

### Automatic Disabling

Features are automatically disabled when:
- Error rate exceeds 5% over 5 minutes
- P95 latency increases by >30% over baseline
- Database connection pool exhaustion
- Memory usage exceeds 90%

### Manual Override

```python
# Force enable (use with caution)
FeatureFlags.force_enable('use_feeds_repo')

# Emergency disable
FeatureFlags.emergency_disable('use_feeds_repo')
```

## Monitoring

### Metrics Tracked

- **Success Rate**: Percentage of successful operations
- **Latency**: P50, P95, P99 response times
- **Error Rate**: Failures per minute
- **Rollback Count**: Number of automatic rollbacks
- **Shadow Comparison**: Divergence between old/new implementations

### Dashboards

- Feature Flag Status: `/admin/manager`
- Performance Metrics: `/api/metrics/feature-flags`
- Shadow Comparison Results: `/api/metrics/shadow-comparison`

## Rollout Strategy

### Gradual Rollout Process

1. **Stage 1: Shadow Mode (0%)**
   - New code runs in parallel
   - Results compared but not used
   - Metrics collected

2. **Stage 2: Canary (5-10%)**
   - Small percentage of traffic
   - Monitor for errors
   - Quick rollback if needed

3. **Stage 3: Progressive (25-50-75%)**
   - Gradual increase
   - Monitor performance
   - Validate at each step

4. **Stage 4: Full Rollout (95-100%)**
   - Nearly complete migration
   - Keep fallback ready
   - Final validation

5. **Stage 5: Cleanup**
   - Remove old code
   - Archive feature flag
   - Document completion

## Best Practices

1. **Always use feature flags for**:
   - Database schema changes
   - API breaking changes
   - Algorithm replacements
   - Third-party integrations

2. **Monitor before increasing rollout**:
   - Check error rates
   - Verify performance metrics
   - Review user feedback
   - Validate data consistency

3. **Have rollback plan**:
   - Test rollback procedure
   - Document dependencies
   - Keep old code for 30 days
   - Maintain database compatibility

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Feature not working | Check flag status in admin panel |
| High error rate | Review circuit breaker logs |
| Slow performance | Check shadow comparison metrics |
| Inconsistent behavior | Verify rollout percentage |

### Debug Commands

```bash
# Check all flags status
python -m app.utils.feature_flags status

# View flag history
python -m app.utils.feature_flags history use_feeds_repo

# Reset to defaults
python -m app.utils.feature_flags reset

# Export configuration
python -m app.utils.feature_flags export > flags.json
```

## Related Documentation

- [Repository Pattern Migration](./REPOSITORY_MIGRATION.md)
- [Performance Monitoring](./MONITORING.md)
- [Testing Strategy](./TESTING.md)
- [API Documentation](./API_DOCUMENTATION.md)