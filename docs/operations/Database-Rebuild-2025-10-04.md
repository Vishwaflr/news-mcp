# Database Rebuild - October 4, 2025

## Summary
Complete database rebuild after data loss. Fresh PostgreSQL setup with improved access control for Claude operations.

## What Happened
- **Data Loss:** Production database lost (45 feeds, 22,948 items, ~87 MB)
- **Old Backup:** Only backup from Sept 17 found (3 feeds, outdated schema)
- **Decision:** Complete fresh start with better database access configuration

## New Database Setup

### 1. Database Users
Two PostgreSQL users with different permissions:

**Admin User (for Claude operations):**
- Username: `cytrex`
- Password: `Aug2012#`
- Privileges: SUPERUSER, CREATEDB, CREATEROLE
- Purpose: Schema changes, migrations, manual operations

**Application User (for services):**
- Username: `news_user`
- Password: `news_password`
- Privileges: Limited to application operations
- Purpose: API, Scheduler, Worker services

### 2. Database Access

**Password-free Access (via ~/.pgpass):**
```bash
psql -h localhost -U cytrex -d news_db
```

**With explicit password:**
```bash
export PGPASSWORD='Aug2012#'
psql -h localhost -U cytrex -d news_db -c "SELECT COUNT(*) FROM feeds;"
```

**Connection Details:**
- Host: localhost
- Port: 5432
- Database: news_db
- Schema: public (32 tables)

### 3. Schema Creation

**Tables created (32 total):**
```
Core:
- feeds, items, fetch_log

Feed Management:
- sources, categories, feed_types, feed_categories, feed_health
- feed_processor_configs, processor_templates, dynamic_feed_templates
- feed_template_assignments, feed_configuration_changes, feed_scheduler_state

Content:
- item_tags, content_processing_logs

Analysis:
- item_analysis, analysis_runs, analysis_run_items, analysis_presets
- pending_auto_analysis

Content Distribution:
- special_reports, generated_content, distribution_channels, distribution_log
- pending_content_generation

Queue & Metrics:
- queued_runs, queue_metrics, feed_metrics
- feed_limits, feed_violations

User:
- user_settings
```

**Schema Creation Method:**
- Used SQLModel's `metadata.create_all()` instead of Alembic
- Bypassed broken Alembic migrations
- Script: `/home/cytrex/news-mcp/scripts/create-schema.py`

### 4. Docker Services

**Running Containers:**
```bash
docker ps --filter "name=news-mcp"
```

- `news-mcp-postgres` - PostgreSQL 15-alpine (port 5432)
- `news-mcp-redis` - Redis 7-alpine (port 6379)
- `news-mcp-grafana` - Grafana (port 3001)
- `news-mcp-prometheus` - Prometheus (port 9091)

**Data Persistence:**
- Volume: `news-mcp_postgres_data`
- Init script: `/home/cytrex/news-mcp/docker/init/01-create-admin.sql`

### 5. Application Services

**Service Manager:**
```bash
./scripts/service-manager.sh status
```

**Current Status:**
- API Server: Running on 192.168.178.72:8000
- Scheduler: Running (PID 66926)
- Worker: Running (PID 66994)

**Service URLs:**
- API: http://192.168.178.72:8000
- Health: http://192.168.178.72:8000/health
- Feeds: http://192.168.178.72:8000/admin/feeds-v2
- Manager: http://192.168.178.72:8000/admin/manager
- Grafana: http://localhost:3001
- Prometheus: http://localhost:9091

## Key Improvements

### 1. Database Access
- ✅ Password-free access via ~/.pgpass
- ✅ Dedicated admin user (cytrex) for operations
- ✅ Separation of concerns (admin vs. app user)
- ✅ No more export PGPASSWORD needed

### 2. Schema Management
- ✅ SQLModel direct schema creation (bypasses Alembic)
- ✅ All 32 tables created successfully
- ✅ Import errors fixed (verified class names from actual files)

### 3. Process Management
- ✅ Service manager script for easy control
- ✅ Proper PID tracking
- ✅ Graceful shutdown procedures

## Import Fixes Applied

During schema creation, fixed several import errors by **reading actual files** instead of guessing:

1. **content_distribution.py:**
   - ❌ Wrong: `SpecialReportGeneration`
   - ✅ Correct: `SpecialReport`, `GeneratedContent`

2. **run_queue.py vs feed_metrics.py:**
   - ❌ Wrong: `QueueMetrics` from run_queue
   - ✅ Correct: `QueueMetrics` from feed_metrics

3. **feed_limits.py:**
   - ❌ Wrong: `FeedLimits` (plural)
   - ✅ Correct: `FeedLimit` (singular)

## Verification Checklist

✅ Database accessible via cytrex user
✅ All 32 tables created
✅ Docker containers healthy
✅ API responding on port 8000
✅ Scheduler processing feeds
✅ Worker processing analysis
✅ Web UI pages loading
✅ Management dashboard working

## Next Steps

1. **Add Feeds:** Start adding RSS feeds via `/admin/feeds-v2`
2. **Configure Analysis:** Set up analysis presets
3. **Monitor Services:** Use Grafana dashboard at port 3001
4. **Backup Strategy:** Set up automated database backups

## Backup Commands

**Create backup:**
```bash
export PGPASSWORD='Aug2012#'
pg_dump -h localhost -U cytrex -d news_db -F c -f news_db_backup_$(date +%Y%m%d_%H%M%S).dump
```

**Restore backup:**
```bash
export PGPASSWORD='Aug2012#'
pg_restore -h localhost -U cytrex -d news_db -c news_db_backup_YYYYMMDD_HHMMSS.dump
```

## Files Modified/Created

- `/home/cytrex/news-mcp/docker/init/01-create-admin.sql` - Created admin user
- `/home/cytrex/news-mcp/app/models/__init__.py` - Fixed imports
- `/home/cytrex/.pgpass` - Password-free access
- `/home/cytrex/CLAUDE.md` - Added "NEVER GUESS" rules + process management

## Lessons Learned

1. **Always verify class names** by reading actual files (never guess)
2. **Check schema before SQL** with `\d tablename`
3. **Analyze before action** when managing processes
4. **Document access credentials** for easier operations
5. **Use dedicated admin user** for schema operations
