# Database Schema Documentation

**Database:** `news_db`
**User:** `news_user`
**Password:** `news_password`
**Total Tables:** 30

---

## Core Tables

### `items` - News Articles

Main table storing all fetched news articles.

```sql
Table "public.items"
    Column    |            Type             | Nullable |              Default
--------------+-----------------------------+----------+-----------------------------------
 id           | integer                     | not null | nextval('items_id_seq'::regclass)
 title        | character varying           | not null |
 link         | character varying           | not null |   -- ⚠️ NOT "url", use "link"
 description  | character varying           |          |
 content      | character varying           |          |
 author       | character varying           |          |
 published    | timestamp without time zone |          |
 guid         | character varying           |          |
 content_hash | character varying           | not null |   -- For deduplication
 feed_id      | integer                     | not null |
 created_at   | timestamp without time zone | not null |

Indexes:
    "items_pkey" PRIMARY KEY (id)
    "items_content_hash_idx" UNIQUE (content_hash)  -- Deduplication by content
    "ix_items_content_hash" UNIQUE (content_hash)
    "items_feed_timeline_idx" (feed_id, created_at DESC)
    "items_published_idx" (published DESC NULLS LAST)
    "ix_items_guid" (guid)
    "ix_items_link" (link)

Foreign Keys:
    feed_id -> feeds(id)

Referenced By:
    - analysis_run_items.item_id
    - content_processing_logs.item_id
    - item_analysis.item_id (CASCADE DELETE)
    - item_tags.item_id
```

**Deduplication Logic:**
- Primary: `content_hash` (UNIQUE constraint)
- Secondary: `link` (indexed, can have duplicates)
- Note: `guid` can be NULL (0 unique_guids in some feeds)

**Common Queries:**
```sql
-- Find duplicates by link
SELECT link, COUNT(*) as count, array_agg(id) as item_ids
FROM items
GROUP BY link
HAVING COUNT(*) > 1;

-- Get items with analysis
SELECT i.*, ia.sentiment_json
FROM items i
LEFT JOIN item_analysis ia ON i.id = ia.item_id
WHERE i.feed_id = ?;
```

---

### `feeds` - RSS Feed Configurations

```sql
Table "public.feeds"
         Column         |            Type             | Nullable |              Default
------------------------+-----------------------------+----------+-----------------------------------
 id                     | integer                     | not null | nextval('feeds_id_seq'::regclass)
 url                    | character varying           | not null |   -- ⚠️ Feed URL (NOT items.link)
 title                  | character varying           |          |
 description            | character varying           |          |
 status                 | feedstatus (ENUM)           | not null |
 fetch_interval_minutes | integer                     | not null |
 last_fetched           | timestamp without time zone |          |
 next_fetch_scheduled   | timestamp without time zone |          |
 last_modified          | character varying           |          |
 etag                   | character varying           |          |
 configuration_hash     | character varying           |          |
 source_id              | integer                     | not null |
 feed_type_id           | integer                     |          |
 created_at             | timestamp without time zone | not null |
 updated_at             | timestamp without time zone | not null |
 auto_analyze_enabled   | boolean                     | not null | false

Indexes:
    "feeds_pkey" PRIMARY KEY (id)
    "ix_feeds_url" UNIQUE (url)

Foreign Keys:
    feed_type_id -> feed_types(id)
    source_id -> sources(id)

Referenced By:
    - items.feed_id
    - fetch_log.feed_id
    - feed_health.feed_id
    - pending_auto_analysis.feed_id (CASCADE DELETE)
    (+ 8 more tables)
```

**Common Queries:**
```sql
-- Get active feeds
SELECT * FROM feeds WHERE status = 'ACTIVE';

-- Find feed by URL pattern
SELECT * FROM feeds WHERE url ILIKE '%cointelegraph%';
```

---

### `item_analysis` - AI Analysis Results

Stores sentiment and geopolitical analysis results.

```sql
Table "public.item_analysis"
     Column     |           Type           | Nullable |   Default
----------------+--------------------------+----------+-------------
 item_id        | bigint                   | not null |   -- ⚠️ PK, not "id"
 sentiment_json | jsonb                    | not null | '{}'::jsonb
 impact_json    | jsonb                    | not null | '{}'::jsonb
 model_tag      | text                     |          |
 updated_at     | timestamp with time zone | not null | now()

Indexes:
    "item_analysis_pkey" PRIMARY KEY (item_id)
    -- Geopolitical indexes:
    "idx_geopolitical_regions_gin" GIN ((sentiment_json->'geopolitical'->'regions_affected'))
    "idx_geopolitical_stability" ((sentiment_json->'geopolitical'->>'stability_score')::double precision)
    "idx_geopolitical_escalation" ((sentiment_json->'geopolitical'->>'escalation_potential')::double precision)
    "idx_geopolitical_security" ((sentiment_json->'geopolitical'->>'security_relevance')::double precision)
    "idx_geopolitical_conflict_type" ((sentiment_json->'geopolitical'->>'conflict_type'))
    -- Overall sentiment indexes:
    "idx_item_analysis_sentiment_label" ((sentiment_json->'overall'->>'label'))
    "idx_item_analysis_urgency" ((sentiment_json->>'urgency')::numeric)
    "idx_item_analysis_impact_overall" ((impact_json->>'overall')::numeric)

Foreign Keys:
    item_id -> items(id) ON DELETE CASCADE
```

**JSONB Structure:**
```json
{
  "sentiment_json": {
    "overall": {
      "label": "positive|negative|neutral",
      "score": -1.0 to 1.0
    },
    "urgency": 0.0 to 1.0,
    "geopolitical": {
      "stability_score": -1.0 to 1.0,
      "escalation_potential": 0.0 to 1.0,
      "security_relevance": 0.0 to 1.0,
      "conflict_type": "string",
      "time_horizon": "string",
      "regions_affected": ["region1", "region2"],
      "impact_affected": ["country1", "country2"],
      "impact_beneficiaries": ["country1", "country2"]
    }
  },
  "impact_json": {
    "overall": 0.0 to 1.0
  }
}
```

**Common Queries:**
```sql
-- Get items with sentiment analysis
SELECT
    i.id,
    i.title,
    ia.sentiment_json->'overall'->>'label' as sentiment,
    (ia.sentiment_json->'overall'->>'score')::float as score
FROM items i
JOIN item_analysis ia ON i.id = ia.item_id;

-- Find items with geopolitical analysis
SELECT
    i.id,
    i.title,
    ia.sentiment_json->'geopolitical'->>'stability_score' as stability,
    ia.sentiment_json->'geopolitical'->'regions_affected' as regions
FROM items i
JOIN item_analysis ia ON i.id = ia.item_id
WHERE ia.sentiment_json->'geopolitical' IS NOT NULL;
```

---

### `analysis_runs` - Analysis Job Tracking

```sql
Table "public.analysis_runs"
 -- Schema TBD: Check with \d analysis_runs
```

---

### `fetch_log` - Feed Fetch History

```sql
Table "public.fetch_log"
 -- Schema TBD: Check with \d fetch_log
```

---

### `feed_health` - Feed Health Monitoring

```sql
Table "public.feed_health"
 -- Schema TBD: Check with \d feed_health
```

---

## Supporting Tables

### `sources` - News Sources

```sql
Table "public.sources"
 -- Schema TBD: Check with \d sources
```

---

### `categories` - Content Categories

```sql
Table "public.categories"
 -- Schema TBD: Check with \d categories
```

---

### `feed_types` - Feed Type Classifications

```sql
Table "public.feed_types"
 -- Schema TBD: Check with \d feed_types
```

---

## Analysis & Processing Tables

- `analysis_run_items` - Links analysis runs to items
- `pending_auto_analysis` - Queue for automatic analysis
- `content_processing_logs` - Processing history
- `queued_runs` - Analysis queue

---

## Configuration Tables

- `feed_template_assignments` - Template assignments to feeds
- `dynamic_feed_templates` - Feed templates
- `processor_templates` - Processing templates
- `feed_processor_configs` - Processor configurations
- `feed_configuration_changes` - Configuration change history
- `analysis_presets` - Analysis presets
- `user_settings` - User preferences

---

## Monitoring & Metrics Tables

- `feed_metrics` - Feed performance metrics
- `feed_limits` - Feed rate limits
- `feed_violations` - Limit violations
- `feed_scheduler_state` - Scheduler state
- `queue_metrics` - Queue metrics
- `preview_jobs` - Preview job tracking

---

## Metadata Tables

- `alembic_version` - Database migrations
- `item_tags` - Item tagging
- `feed_categories` - Feed categorization
- `basetablemodel` - Base model metadata

---

## Common Query Patterns

### Check for Duplicates
```sql
-- By link (items can have duplicate links)
SELECT
    link,
    COUNT(*) as count,
    array_agg(id ORDER BY created_at) as item_ids,
    MIN(created_at) as first_seen,
    MAX(created_at) as last_seen
FROM items
WHERE feed_id = ?
GROUP BY link
HAVING COUNT(*) > 1;

-- By content_hash (should be unique, but check violations)
SELECT
    content_hash,
    COUNT(*) as count
FROM items
GROUP BY content_hash
HAVING COUNT(*) > 1;
```

### Get Items with Analysis Status
```sql
SELECT
    i.id,
    i.title,
    i.link,
    i.created_at,
    CASE
        WHEN ia.item_id IS NOT NULL THEN 'analyzed'
        WHEN paa.item_id IS NOT NULL THEN 'pending'
        ELSE 'not_queued'
    END as analysis_status
FROM items i
LEFT JOIN item_analysis ia ON i.id = ia.item_id
LEFT JOIN pending_auto_analysis paa ON i.id = paa.item_id
WHERE i.feed_id = ?
ORDER BY i.created_at DESC;
```

### Feed Performance
```sql
SELECT
    f.id,
    f.title,
    COUNT(DISTINCT i.id) as total_items,
    COUNT(DISTINCT ia.item_id) as analyzed_items,
    COUNT(DISTINCT i.id) - COUNT(DISTINCT ia.item_id) as unanalyzed_items
FROM feeds f
LEFT JOIN items i ON f.id = i.feed_id
LEFT JOIN item_analysis ia ON i.id = ia.item_id
GROUP BY f.id, f.title;
```

---

## Important Notes

### Deduplication Strategy

1. **Primary Deduplication:** `items.content_hash` (UNIQUE constraint)
   - Prevents exact duplicate content
   - Hash generated from title + content

2. **Secondary Check:** `items.link`
   - Indexed but NOT unique
   - Same article can be re-fetched with same link (RSS feed updates)
   - Duplicates by link = 35 found in cointelegraph (2346 total items)

3. **GUID Handling:**
   - `items.guid` can be NULL
   - Some feeds have 0 unique GUIDs (all NULL)
   - NOT reliable for deduplication

### Analysis Workflow

1. Item fetched → `items` table
2. If `feeds.auto_analyze_enabled = true` → `pending_auto_analysis`
3. Worker picks up → Analyzes → `item_analysis`
4. Results stored as JSONB (sentiment_json, impact_json)

### Performance Considerations

- `items` table has composite index: `(feed_id, created_at DESC)` for timeline queries
- `item_analysis` has GIN indexes on JSONB for geopolitical queries
- Use EXPLAIN ANALYZE for complex queries

---

## Schema Maintenance

**When to update this document:**
- ✅ After database migrations (alembic upgrade)
- ✅ When discovering new table structures
- ✅ After adding/removing columns
- ✅ When finding deduplication issues

**How to check current schema:**
```bash
export PGPASSWORD='news_password'
psql -h localhost -U news_user -d news_db -c "\d+ tablename"
```

---

## Content Distribution System (Phase 1 Complete - 2025-10-03)

### `content_templates` - Content Generation Templates

Template definitions for LLM-based content generation with structured prompts.

```sql
Table "public.content_templates"
     Column         |            Type             | Nullable |              Default
--------------------+-----------------------------+----------+-----------------------------------
 id                 | integer                     | not null | nextval('content_templates_id_seq')
 name               | character varying(200)      | not null |
 description        | text                        |          |
 target_audience    | character varying(100)      |          |

 -- Article Selection
 selection_criteria | jsonb                       | not null | -- Keywords, timeframe, scores

 -- Content Structure
 content_structure  | jsonb                       | not null | -- Sections, max_words, etc.

 -- LLM Configuration (Legacy)
 llm_prompt_template| text                        | not null | -- User prompt
 llm_model          | character varying(50)       | not null | 'gpt-4o-mini'
 llm_temperature    | numeric(3,2)                | not null | 0.7

 -- Enhanced LLM Instructions (Phase 1)
 system_instruction | text                        |          | -- Role & constraints
 output_format      | character varying(50)       | not null | 'markdown' -- html/json
 output_constraints | jsonb                       |          | -- Forbidden/required elements
 few_shot_examples  | jsonb                       |          | -- Example outputs
 validation_rules   | jsonb                       |          | -- Post-generation checks

 -- Enrichment Placeholder (Phase 2 - Future)
 enrichment_config  | jsonb                       |          | -- CVE lookup, web search, etc.

 -- Scheduling & Status
 generation_schedule| character varying(100)      |          | -- Cron expression
 is_active          | boolean                     | not null | true
 created_at         | timestamp without time zone | not null |
 updated_at         | timestamp without time zone | not null |
 version            | integer                     | not null | 1
 tags               | jsonb                       |          |

Indexes:
    "content_templates_pkey" PRIMARY KEY (id)
    "uq_template_name" UNIQUE (name)
    "idx_templates_active" (is_active)
    "idx_templates_schedule" (generation_schedule)

Referenced By:
    - generated_content.template_id (CASCADE DELETE)
    - distribution_channels.template_id (CASCADE DELETE)
    - pending_content_generation.template_id (CASCADE DELETE)
```

**Phase 1 Features (Implemented):**
- ✅ Structured system prompts (role definition, constraints)
- ✅ Output format control (markdown/html/json)
- ✅ Constraint enforcement (forbidden: code blocks, required: sources)
- ✅ Few-shot learning examples
- ✅ Validation rules (min/max word count, source citations)
- ✅ Modular architecture ready for Phase 2 enrichment

**Example Configuration:**
```json
{
  "system_instruction": "You are a senior security analyst...\nIMPORTANT: NO code blocks, only prose analysis.",
  "output_constraints": {
    "forbidden": ["code_blocks", "shell_commands"],
    "required": ["sources", "executive_summary"],
    "min_word_count": 500,
    "max_word_count": 2000
  },
  "validation_rules": {
    "require_sources": true,
    "check_for_code": true
  },
  "enrichment_config": null  // Reserved for Phase 2
}
```

**Common Queries:**
```sql
-- Get active templates with LLM instructions
SELECT name, system_instruction, output_constraints
FROM content_templates
WHERE is_active = true;

-- Find templates using specific constraints
SELECT name, output_constraints->'forbidden' as forbidden_elements
FROM content_templates
WHERE output_constraints ? 'forbidden';
```

---

### `generated_content` - LLM-Generated Reports

Stores generated content instances from templates.

```sql
Table "public.generated_content"
     Column                 |       Type       | Nullable | Default
----------------------------+------------------+----------+---------
 id                         | integer          | not null |
 template_id                | integer          | not null | FK -> content_templates

 -- Generated Content
 title                      | varchar(500)     |          |
 content_html               | text             |          |
 content_markdown           | text             |          |
 content_json               | jsonb            |          |

 -- Metadata
 generated_at               | timestamp        | not null |
 generation_job_id          | varchar(100)     |          |

 -- Source Tracking
 source_article_ids         | integer[]        | not null | -- Articles used
 articles_count             | integer          | not null |

 -- Quality Metrics
 word_count                 | integer          |          |
 generation_cost_usd        | numeric          |          |
 generation_time_seconds    | integer          |          |
 llm_model_used             | varchar(50)      |          |

 -- Status
 status                     | varchar(20)      | not null | 'generated'
 published_at               | timestamp        |          |
 error_message              | text             |          |

Indexes:
    "generated_content_pkey" PRIMARY KEY (id)
    "idx_content_template" (template_id)
    "idx_content_generated_at" (generated_at DESC)
    "idx_content_status" (status)

Foreign Keys:
    template_id -> content_templates(id) ON DELETE CASCADE
```

**Worker:** `app/worker/content_generator_worker.py`
**Queue Table:** `pending_content_generation`

---

### `pending_content_generation` - Content Generation Queue

Queue for async content generation jobs.

```sql
Table "public.pending_content_generation"
     Column             |       Type       | Nullable | Default
------------------------+------------------+----------+---------
 id                     | integer          | not null |
 template_id            | integer          | not null | FK -> content_templates
 status                 | varchar(20)      | not null | 'pending'
 created_at             | timestamp        | not null |
 started_at             | timestamp        |          |
 completed_at           | timestamp        |          |
 worker_id              | varchar(100)     |          |
 generated_content_id   | integer          |          | FK -> generated_content
 error_message          | text             |          |
 retry_count            | integer          | not null | 0
 triggered_by           | varchar(50)      | not null | 'manual'

Indexes:
    "pending_content_generation_pkey" PRIMARY KEY (id)
    "idx_pcg_status" (status)
    "idx_pcg_created" (created_at)

Foreign Keys:
    template_id -> content_templates(id) ON DELETE CASCADE
```

**Statuses:** `pending` → `processing` → `completed`/`failed`

---

### `distribution_channels` - Content Distribution

Channel configurations for distributing generated content (email, web, RSS, API).

```sql
Table "public.distribution_channels"
     Column      |       Type       | Nullable | Default
-----------------+------------------+----------+---------
 id              | integer          | not null |
 template_id     | integer          | not null | FK -> content_templates
 channel_type    | varchar(20)      | not null | -- email/web/rss/api
 channel_name    | varchar(200)     | not null |
 channel_config  | jsonb            | not null |
 is_active       | boolean          | not null | true
 created_at      | timestamp        | not null |
 last_used_at    | timestamp        |          |

Indexes:
    "distribution_channels_pkey" PRIMARY KEY (id)
    "idx_dc_template" (template_id)
    "idx_dc_type_active" (channel_type, is_active)

Foreign Keys:
    template_id -> content_templates(id) ON DELETE CASCADE
```

---

## Storage Statistics (Live Monitoring)

**Endpoint:** `GET /api/metrics/storage/stats`

**Current Storage (as of 2025-10-02):**
- **Total Database Size:** 77 MB
- **Total Items:** 19,129
- **Analyzed Items:** 7,999 (41.82% coverage)
- **Growth Rate:** ~10,203 items/week (530k/year projected)

**Top 5 Tables by Size:**
1. `items` - 29 MB (13 MB data + 16 MB indexes)
2. `analysis_run_items` - 19 MB (7.2 MB data + 12 MB indexes)
3. `fetch_log` - 8 MB (6.4 MB data + 1.7 MB indexes)
4. `item_analysis` - 6.6 MB (4.2 MB data + 2.4 MB indexes)
5. `content_processing_logs` - 3.8 MB (2.8 MB data + 976 kB indexes)

**JSONB Field Sizes:**
- `sentiment_json` (item_analysis): 3.1 MB (7,998 entries, avg 393 bytes)
- `impact_json` (item_analysis): 445 kB (7,998 entries, avg 57 bytes)
- Geopolitical data: 1.08 MB (1,413 items, 17.67% of analyses)

**Storage by Category:**
- RSS Feed Data (items + feeds + fetch_log): 37 MB (48%)
- Sentiment Analysis Data (item_analysis + analysis_runs + analysis_run_items): 26 MB (34%)
- Auto-Analysis Queue (pending_auto_analysis): 400 kB (0.5%)
- Feed Management (health, metrics, config): 232 kB (0.3%)

**Monitoring UI:**
- Manager Dashboard: http://192.168.178.72:8000/admin/manager
- Storage Stats Card (top-left, with Update button)
- Details View (expandable for full breakdown)

---

**Last Updated:** 2025-10-02
**Schema Version:** Based on current production DB
**Maintainer:** News-MCP Team
