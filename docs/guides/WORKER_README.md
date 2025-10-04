# News Analysis Worker

**Last Updated:** 2025-10-03
**Status:** Production - Running (PID 291349)
**Performance:** 1,523 runs completed, 8,591 items analyzed, >95% success rate

Ein persistent laufender Worker-Service, der Analysis Runs und Items aus der Queue abarbeitet und LLM-basierte Sentiment- und Impact-Analysen durchführt.

## Überblick

Der Analysis Worker implementiert das Producer-Consumer Pattern:
- **Producer**: Analysis Control Center erstellt runs und queued items
- **Consumer**: Analysis Worker verarbeitet items mit LLM-Calls und speichert Ergebnisse

## Komponenten

### Core Files

- **`app/worker/analysis_worker.py`**: Haupt-Worker-Loop mit Signal-Handling
- **`app/services/analysis_orchestrator.py`**: Service-Layer für Run-Management
- **`app/repositories/analysis_queue.py`**: Repository mit SKIP LOCKED für concurrent processing
- **`scripts/start-worker.sh`**: Startup-Script mit Environment-Loading
- **`systemd/news-analysis-worker.service`**: Systemd Service Definition

### Configuration

- **`.env.worker`**: Environment-Variablen für Worker-Konfiguration
- **`WORKER_CHUNK_SIZE`**: Anzahl Items pro Batch (default: 10)
- **`WORKER_SLEEP_INTERVAL`**: Sleep zwischen Cycles (default: 5.0s)
- **`WORKER_MIN_REQUEST_INTERVAL`**: Rate limiting zwischen API-Calls (default: 0.5s)

## Features

### Queue Processing
- **FOR UPDATE SKIP LOCKED**: Verhindert Race Conditions bei concurrent workers
- **Item State Transitions**: queued → processing → completed/failed/skipped
- **Atomic Claims**: Items werden atomar für Processing reserviert

### Error Handling
- **Error Classification**: E429, E5xx, EPARSE, ETIMEOUT, EAUTH, EUNKNOWN
- **Fallback Results**: Bei API-Fehlern werden neutrale Fallback-Analysen gespeichert
- **Graceful Recovery**: Worker läuft weiter auch bei einzelnen Item-Fehlern

### Rate Limiting
- **Configurable RPS**: Per-Run Konfiguration der Requests/Sekunde
- **Throttling**: Automatische Delays zwischen API-Calls
- **Model-Aware**: Unterstützt verschiedene OpenAI-Modelle (gpt-4o-mini, gpt-5-nano, etc.)

### Monitoring & Maintenance
- **Heartbeat Updates**: Run status wird regelmäßig aktualisiert
- **Stale Item Reset**: Items im "processing" State werden nach Timeout zurückgesetzt
- **Structured Logging**: Ausführliche Logs für Monitoring und Debugging
- **Metrics Tracking**: Token usage, costs, success/error rates

## Usage

### Manual Start
```bash
# Standard start (recommended)
./scripts/start-worker.sh

# With verbose logging
python -B app/worker/analysis_worker.py --verbose

# Check status
ps aux | grep analysis_worker
cat /tmp/news-mcp-worker.pid

# Stop worker
./scripts/stop-all.sh  # Stops all services
# or kill specific worker:
kill $(cat /tmp/news-mcp-worker.pid)
```

### Systemd Service
```bash
# Service installieren
sudo cp systemd/news-analysis-worker.service /etc/systemd/system/
sudo systemctl daemon-reload

# Service starten
sudo systemctl start news-analysis-worker
sudo systemctl enable news-analysis-worker

# Status prüfen
sudo systemctl status news-analysis-worker
sudo journalctl -u news-analysis-worker -f
```

## Architecture

### Database Schema
```sql
-- Analysis runs (created by Control Center)
analysis_runs (id, scope_json, params_json, status, created_at, updated_at)

-- Queued items (created by Control Center, processed by Worker)
analysis_run_items (id, run_id, item_id, state, started_at, completed_at, cost_usd)

-- News items (source data)
items (id, title, description, content, link, created_at)

-- Analysis results (created by Worker)
item_analysis (item_id, sentiment_json, impact_json, model_tag, created_at)
```

### Process Flow
1. **User**: Selects articles in Control Center UI, clicks "Start Analysis"
2. **Control Center**: Creates `analysis_run` and `analysis_run_items` in "queued" state
3. **Worker**: Claims items with SKIP LOCKED, processes with LLM, saves results
4. **Control Center**: Shows live progress and final results

### Concurrency Safety
- **SKIP LOCKED**: Multiple workers können parallel laufen ohne Konflikte
- **Atomic Claims**: Items werden atomar von queued → processing transitioned
- **Heartbeats**: Verhindert dass runs als "stale" markiert werden
- **Stale Recovery**: Crashed workers hinterlassen keine "processing" items

## Model Support

### Supported Models
- **gpt-4o-mini**: Standard-Modell mit temperature=0.1, max_tokens=500
- **gpt-5-nano**: Neues Modell mit max_completion_tokens=500 (kein custom temperature)
- **gpt-5, gpt-5-mini**: Neue Modelle mit max_completion_tokens
- **o3, o4-mini**: Reasoning-Modelle mit max_completion_tokens

### API Parameters
Worker passt automatisch API-Parameter basierend auf Modell an:
```python
if self.model.startswith(('gpt-5', 'o3', 'o4')):
    params["max_completion_tokens"] = 500
    # No custom temperature for newer models
else:
    params["max_tokens"] = 500
    params["temperature"] = 0.1
```

## Monitoring

### Log Levels
- **INFO**: Worker start/stop, run completion, item processing counts
- **DEBUG**: Einzelne item processing, API request details
- **ERROR**: API failures, JSON parse errors, database errors

### Metrics
Worker tracked automatisch:
- **Items processed per run**: Completion counts
- **Token usage**: Estimated tokens per item
- **API costs**: Calculated based on model pricing
- **Error rates**: Failed vs successful item processing
- **Processing times**: Run duration, API response times

### Health Checks
```bash
# Check if worker is processing
sudo journalctl -u news-analysis-worker -n 20

# Monitor active runs
curl -s http://localhost:8000/analysis/status | jq

# Check database queue status
psql -d news_db -c "SELECT status, COUNT(*) FROM analysis_runs GROUP BY status;"
```

## Troubleshooting

### Common Issues

**Worker nicht starting**:
- Check DATABASE_URL und OPENAI_API_KEY in .env.worker
- Verify virtual environment: `source venv/bin/activate`
- Check PostgreSQL connection: `psql $DATABASE_URL`

**API Errors**:
- **400 Bad Request**: Model parameter incompatibility (fixed in current version)
- **401 Unauthorized**: Invalid OPENAI_API_KEY
- **429 Rate Limit**: Reduce WORKER_MIN_REQUEST_INTERVAL or model rate_per_second

**Items stuck in processing**:
- Worker restart resettet automatically stale items
- Manual reset: Run `UPDATE analysis_run_items SET state='queued' WHERE state='processing';`

**No progress on runs**:
- Check if runs are in "pending" state: Worker starts them automatically
- Verify items are in "queued" state, not already "completed"
- Check worker logs for error messages

### Performance Tuning

**Higher Throughput**:
- Increase `WORKER_CHUNK_SIZE` (default: 10)
- Decrease `WORKER_MIN_REQUEST_INTERVAL` (but watch for rate limits)
- Run multiple worker instances (safe due to SKIP LOCKED)

**Lower API Costs**:
- Use cheaper models (gpt-5-nano vs gpt-4o-mini)
- Reduce `max_completion_tokens` for shorter responses
- Implement smarter batching strategies

**Resource Management**:
- Set systemd MemoryMax and CPUQuota limits
- Monitor with `htop`, `iotop` for CPU/memory usage
- Use log rotation for /var/log/news-analysis-worker.log

## Development

### Adding New Models
1. Update `MODEL_PRICING` in `app/domain/analysis/control.py`
2. Add model-specific API parameters in `LLMClient.classify()`
3. Test with dry-run mode: `./scripts/start-worker.sh --dry-run`

### Testing
```bash
# Unit tests (if implemented)
pytest tests/test_worker.py

# Integration test with live database
WORKER_CHUNK_SIZE=2 ./scripts/start-worker.sh --verbose

# Dry-run test (no API calls)
./scripts/start-worker.sh --dry-run --verbose
```

### Debugging
```bash
# Run with debug logging
LOG_LEVEL=DEBUG ./scripts/start-worker.sh --verbose

# Monitor database changes
psql -d news_db -c "\\watch 2 SELECT state, COUNT(*) FROM analysis_run_items WHERE run_id=3 GROUP BY state;"

# Check recent analysis results
psql -d news_db -c "SELECT item_id, model_tag, created_at FROM item_analysis ORDER BY created_at DESC LIMIT 10;"
```

## Security

- **API Keys**: Stored in .env.worker, nicht in Git committed
- **Database**: Uses dedicated news_user mit limited permissions
- **Systemd**: Läuft als user `cytrex`, nicht als root
- **Logs**: Keine sensitive Daten in Log-Files
- **Network**: Only outbound HTTPS zu OpenAI API