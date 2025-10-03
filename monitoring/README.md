# News-MCP Monitoring Stack

**Sprint 1 Day 4:** Grafana + Prometheus monitoring setup for production observability.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│ Analysis Worker │────▶│   Prometheus     │────▶│   Grafana   │
│   Port 9090     │     │   Port 9091      │     │  Port 3000  │
└─────────────────┘     └──────────────────┘     └─────────────┘
        │                        │
        │                        │
┌─────────────────┐              │
│  API Server     │──────────────┘
│   Port 8000     │
└─────────────────┘
```

## Quick Start

### 1. Start Monitoring Stack

```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

### 2. Access Dashboards

- **Grafana UI:** http://localhost:3000
  - Username: `admin`
  - Password: `admin`
- **Prometheus UI:** http://localhost:9091

### 3. Verify Metrics Collection

Check Prometheus targets are healthy:
```bash
curl http://localhost:9091/targets
```

Check Worker metrics endpoint:
```bash
curl http://localhost:9090/metrics | head -20
```

## Dashboard Panels

The **News-MCP Sprint 1** dashboard includes:

### Performance Metrics
- **Analysis Throughput:** Items processed per minute (auto vs manual)
- **Error Rate:** Percentage of failed items
- **Analysis Duration:** p50, p95, p99 latencies
- **API Request Duration:** Per-model latency breakdown

### Queue & Backpressure
- **Queue Depth:** Number of items waiting
- **Active Items:** Currently processing
- **Utilization %:** Queue capacity usage

### Reliability
- **Circuit Breaker State:** CLOSED / HALF_OPEN / OPEN
- **Current Rate Limit:** Active req/sec throttling
- **Circuit Breaker Changes:** State transitions in 24h

### 24-Hour Stats
- Total Items Processed
- Total API Calls
- Total Errors
- Circuit Breaker Events

### Detailed Views
- **Errors by Component:** Orchestrator, Processor, etc.
- **Batch Size Distribution:** p50, p95 batch sizes

## Alerting Rules

Configure alerts in Grafana for SLO violations:

### Critical Alerts
- Error rate > 10% for 5 minutes
- Circuit breaker OPEN for 1 minute
- Queue utilization > 90% for 5 minutes

### Warning Alerts
- Error rate > 5% for 5 minutes
- Analysis p95 latency > 10s
- No items processed for 15 minutes (worker down)

## Metrics Reference

### Counters
- `analysis_items_processed_total{status, triggered_by}`
- `analysis_errors_total{error_type, component}`
- `analysis_api_calls_total{model, status}`
- `circuit_breaker_state_changes_total{from_state, to_state}`

### Gauges
- `analysis_queue_depth`
- `analysis_active_items`
- `analysis_queue_utilization_percent`
- `circuit_breaker_state{component}` (0=CLOSED, 1=HALF_OPEN, 2=OPEN)
- `rate_limiter_current_rate`

### Histograms
- `analysis_duration_seconds`
- `api_request_duration_seconds{model}`
- `queue_wait_time_seconds`
- `analysis_batch_size`

## Troubleshooting

### Prometheus Can't Reach Targets

If running in Docker and targets show as DOWN:

1. **macOS/Windows:** Ensure `host.docker.internal` works
2. **Linux:** Replace `host.docker.internal` with `172.17.0.1` in `prometheus.yml`

```yaml
# For Linux hosts
static_configs:
  - targets: ['172.17.0.1:9090']  # Worker
  - targets: ['172.17.0.1:8000']  # API
```

### Worker Metrics Not Showing

Check worker logs for metrics server startup:
```bash
tail -f /tmp/worker.log | grep "metrics server"
```

Should see:
```
Worker metrics server started on port 9090
```

### Dashboard Shows No Data

1. Check Prometheus is scraping:
   ```bash
   curl http://localhost:9091/api/v1/targets
   ```

2. Verify metrics exist:
   ```bash
   curl http://localhost:9091/api/v1/query?query=analysis_queue_depth
   ```

3. Trigger some analysis activity:
   ```bash
   curl -X POST http://localhost:8000/api/analysis/start -H "Content-Type: application/json" -d '{...}'
   ```

## Production Deployment

### Resource Requirements
- **Prometheus:** 512MB RAM, 10GB disk (7 days retention)
- **Grafana:** 256MB RAM

### Retention Policy

Edit `prometheus.yml`:
```yaml
global:
  scrape_interval: 15s
  retention.time: 7d  # Keep 7 days of data
```

### Backup Dashboards

Export dashboard JSON:
```bash
curl http://localhost:3000/api/dashboards/db/news-mcp-sprint1 > backup.json
```

## Next Steps

- Configure alerting channels (Slack, email, PagerDuty)
- Add custom annotations for deployments
- Create dashboards for feed-specific metrics
- Set up long-term storage (Thanos, Cortex)
