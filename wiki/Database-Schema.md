# Database Schema - News MCP Data Model

Complete database schema documentation for News MCP PostgreSQL database.

---

## 📊 Schema Overview

**Total Tables:** 30
**Total Rows:** 54,000+
**Database:** PostgreSQL 15+

---

## 🗂️ Core Tables

### feeds
**Purpose:** RSS feed configuration and management

| Column | Type | Description |
|--------|------|-------------|
| id | bigint | Primary key |
| title | text | Feed title |
| url | text | RSS feed URL |
| status | text | active \| inactive \| error |
| fetch_interval_minutes | int | Fetch interval (default: 60) |
| last_fetched_at | timestamp | Last fetch time |
| auto_analysis_enabled | boolean | Auto-analysis toggle (Phase 2) |
| created_at | timestamp | Creation timestamp |
| updated_at | timestamp | Last update timestamp |

**Current Rows:** 37 (37 active)

---

### items
**Purpose:** News articles/feed items

| Column | Type | Description |
|--------|------|-------------|
| id | bigint | Primary key |
| feed_id | bigint | Foreign key → feeds |
| title | text | Article title |
| url | text | Article URL |
| content | text | Article content |
| published | timestamp | Publication date |
| guid | text | Unique identifier (from RSS) |
| created_at | timestamp | Import timestamp |

**Current Rows:** 10,285

**Indexes:**
- `idx_items_feed_published` on (feed_id, published DESC)
- `idx_items_guid` on (guid)

---

### item_analysis
**Purpose:** AI analysis results for articles

| Column | Type | Description |
|--------|------|-------------|
| id | bigint | Primary key |
| item_id | bigint | Foreign key → items |
| run_id | bigint | Foreign key → analysis_runs |
| sentiment | text | positive \| negative \| neutral |
| sentiment_score | float | -1.0 to 1.0 |
| summary | text | AI-generated summary |
| topics | jsonb | Extracted topics |
| analyzed_at | timestamp | Analysis timestamp |

**Current Rows:** 2,866

---

## 🔄 Analysis System Tables

### analysis_runs
**Purpose:** Analysis job tracking

| Column | Type | Description |
|--------|------|-------------|
| id | bigint | Primary key |
| scope_json | jsonb | Target selection config |
| params_json | jsonb | Analysis parameters |
| status | text | queued \| running \| completed \| failed |
| items_total | int | Total items to process |
| items_processed | int | Items completed |
| created_at | timestamp | Job creation time |
| started_at | timestamp | Processing start time |
| completed_at | timestamp | Processing end time |

**Current Rows:** 49

---

### analysis_run_items
**Purpose:** Individual analysis tasks

| Column | Type | Description |
|--------|------|-------------|
| id | bigint | Primary key |
| run_id | bigint | Foreign key → analysis_runs |
| item_id | bigint | Foreign key → items |
| status | text | pending \| completed \| failed |
| error_message | text | Error details (if failed) |
| processed_at | timestamp | Processing timestamp |

**Current Rows:** 2,981

---

## 📝 Monitoring Tables

### fetch_log
**Purpose:** Feed fetch operation history

| Column | Type | Description |
|--------|------|-------------|
| id | bigint | Primary key |
| feed_id | bigint | Foreign key → feeds |
| started_at | timestamp | Fetch start time |
| completed_at | timestamp | Fetch end time |
| status | text | success \| error |
| items_found | int | Items in RSS |
| items_new | int | New items added |
| error_message | text | Error details |

**Current Rows:** 35,040

**Partitioning:** Time-based partitioning recommended for production

---

### feed_health
**Purpose:** Feed health monitoring

| Column | Type | Description |
|--------|------|-------------|
| feed_id | bigint | Primary key → feeds |
| status | text | healthy \| degraded \| unhealthy |
| success_rate | float | Fetch success rate (0.0-1.0) |
| avg_items_per_fetch | float | Average new items |
| last_error | text | Most recent error |
| consecutive_errors | int | Error counter |
| updated_at | timestamp | Last health check |

**Current Rows:** 37 (one per feed)

---

## 🏷️ Organization Tables

### categories
**Purpose:** Content categories

| Column | Type | Description |
|--------|------|-------------|
| id | bigint | Primary key |
| name | text | Category name |
| description | text | Category description |
| created_at | timestamp | Creation timestamp |

**Current Rows:** 8

---

### sources
**Purpose:** News sources/publishers

| Column | Type | Description |
|--------|------|-------------|
| id | bigint | Primary key |
| name | text | Source name |
| domain | text | Website domain |
| created_at | timestamp | Creation timestamp |

**Current Rows:** 38

---

## 🎯 Advanced Features

### dynamic_feed_templates
**Purpose:** Reusable feed configurations

| Column | Type | Description |
|--------|------|-------------|
| id | bigint | Primary key |
| name | text | Template name |
| description | text | Template description |
| config_json | jsonb | Configuration |
| created_at | timestamp | Creation timestamp |

**Current Rows:** 3

---

### user_settings
**Purpose:** User preferences

| Column | Type | Description |
|--------|------|-------------|
| id | bigint | Primary key |
| key | text | Setting key |
| value | jsonb | Setting value |
| updated_at | timestamp | Last update |

**Current Rows:** 1

---

## 📈 Relationships

```
feeds (1) ──< (N) items
items (1) ──< (N) item_analysis
analysis_runs (1) ──< (N) analysis_run_items
analysis_run_items (N) ──> (1) items
feeds (1) ──< (N) fetch_log
feeds (1) ──< (1) feed_health
```

---

## 🔍 Common Queries

### Get Feed with Item Count
```sql
SELECT
  f.id,
  f.title,
  f.status,
  COUNT(i.id) as item_count
FROM feeds f
LEFT JOIN items i ON f.id = i.feed_id
GROUP BY f.id, f.title, f.status;
```

### Get Analyzed Items
```sql
SELECT
  i.title,
  ia.sentiment,
  ia.sentiment_score,
  ia.analyzed_at
FROM items i
JOIN item_analysis ia ON i.id = ia.item_id
WHERE ia.sentiment = 'positive'
ORDER BY ia.analyzed_at DESC
LIMIT 10;
```

### Feed Health Summary
```sql
SELECT
  f.title,
  fh.status,
  fh.success_rate,
  fh.consecutive_errors
FROM feeds f
JOIN feed_health fh ON f.id = fh.feed_id
WHERE fh.status != 'healthy';
```

---

## 🔗 Related Documentation

- **[Architecture](Architecture)** - System design
- **[API Overview](API-Overview)** - REST endpoints
- **[Reference](Reference-Database)** - Complete table reference

---

**Last Updated:** 2025-10-01
**Schema Version:** 4.0.0
**Total Tables:** 30
**Total Rows:** 54,000+
