# News MCP Database Schema

Generated: 2025-09-23 21:12:49

## Database Overview

Total Tables: 28

Total Rows: 44,648

## Tables

- [alembic_version](#alembic-version) (1 rows)
- [analysis_presets](#analysis-presets) (0 rows)
- [analysis_run_items](#analysis-run-items) (2,761 rows)
- [analysis_runs](#analysis-runs) (32 rows)
- [basetablemodel](#basetablemodel) (0 rows)
- [categories](#categories) (8 rows)
- [content_processing_logs](#content-processing-logs) (3,152 rows)
- [dynamic_feed_templates](#dynamic-feed-templates) (3 rows)
- [feed_categories](#feed-categories) (31 rows)
- [feed_configuration_changes](#feed-configuration-changes) (4 rows)
- [feed_health](#feed-health) (37 rows)
- [feed_limits](#feed-limits) (2 rows)
- [feed_metrics](#feed-metrics) (3 rows)
- [feed_processor_configs](#feed-processor-configs) (0 rows)
- [feed_scheduler_state](#feed-scheduler-state) (2 rows)
- [feed_template_assignments](#feed-template-assignments) (0 rows)
- [feed_types](#feed-types) (0 rows)
- [feed_violations](#feed-violations) (0 rows)
- [feeds](#feeds) (37 rows)
- [fetch_log](#fetch-log) (28,684 rows)
- [item_analysis](#item-analysis) (2,674 rows)
- [item_tags](#item-tags) (0 rows)
- [items](#items) (7,177 rows)
- [processor_templates](#processor-templates) (0 rows)
- [queue_metrics](#queue-metrics) (0 rows)
- [queued_runs](#queued-runs) (1 rows)
- [sources](#sources) (38 rows)
- [user_settings](#user-settings) (1 rows)

## Table Details

### alembic_version

**Rows:** 1

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| version_num | character varying | NO | None |

**Indexes:**

- `alembic_version_pkc`

---

### analysis_presets

**Rows:** 0

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | bigint | NO | nextval('analysis_presets_id_seq'::regclass) |
| name | text | NO | None |
| description | text | YES | None |
| scope_json | jsonb | NO | '{}'::jsonb |
| params_json | jsonb | NO | '{}'::jsonb |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |

**Indexes:**

- `analysis_presets_pkey`
- `analysis_presets_name_key`

---

### analysis_run_items

**Rows:** 2,761

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | bigint | NO | nextval('analysis_run_items_id_seq'::regclass) |
| run_id | bigint | NO | None |
| item_id | bigint | NO | None |
| state | text | NO | 'queued'::text |
| created_at | timestamp with time zone | NO | now() |
| started_at | timestamp with time zone | YES | None |
| completed_at | timestamp with time zone | YES | None |
| error_message | text | YES | None |
| tokens_used | integer | YES | None |
| cost_usd | numeric | YES | NULL::numeric |

**Foreign Keys:**

- `run_id` → `analysis_runs.id`
- `item_id` → `items.id`

**Indexes:**

- `analysis_run_items_pkey`
- `analysis_run_items_run_id_item_id_key`
- `idx_run_items_run_id`
- `idx_run_items_state`
- `idx_run_items_item_id`

---

### analysis_runs

**Rows:** 32

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | bigint | NO | nextval('analysis_runs_id_seq'::regclass) |
| created_at | timestamp with time zone | NO | now() |
| updated_at | timestamp with time zone | NO | now() |
| scope_json | jsonb | NO | '{}'::jsonb |
| params_json | jsonb | NO | '{}'::jsonb |
| scope_hash | text | NO | None |
| status | text | NO | 'pending'::text |
| queued_count | integer | NO | 0 |
| processed_count | integer | NO | 0 |
| failed_count | integer | NO | 0 |
| cost_estimate | numeric | YES | 0.0 |
| actual_cost | numeric | YES | 0.0 |
| error_rate | numeric | YES | 0.0 |
| items_per_min | numeric | YES | 0.0 |
| eta_seconds | integer | YES | None |
| coverage_10m | numeric | YES | 0.0 |
| coverage_60m | numeric | YES | 0.0 |
| started_at | timestamp with time zone | YES | None |
| completed_at | timestamp with time zone | YES | None |
| last_error | text | YES | None |
| triggered_by | character varying | NO | 'manual'::character varying |

**Indexes:**

- `analysis_runs_pkey`
- `idx_analysis_runs_status`
- `idx_analysis_runs_created`
- `idx_analysis_runs_scope_hash`

---

### basetablemodel

**Rows:** 0

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| created_at | timestamp without time zone | NO | None |
| updated_at | timestamp without time zone | YES | None |
| id | integer | NO | nextval('basetablemodel_id_seq'::regclass) |

**Indexes:**

- `basetablemodel_pkey`

---

### categories

**Rows:** 8

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('categories_id_seq'::regclass) |
| name | character varying | NO | None |
| description | character varying | YES | None |
| color | character varying | YES | None |
| created_at | timestamp without time zone | NO | None |
| updated_at | timestamp without time zone | NO | CURRENT_TIMESTAMP |

**Indexes:**

- `categories_pkey`
- `ix_categories_name`

---

### content_processing_logs

**Rows:** 3,152

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('content_processing_logs_id_seq'::regclass) |
| item_id | integer | NO | None |
| feed_id | integer | NO | None |
| processor_type | USER-DEFINED | NO | None |
| processing_status | USER-DEFINED | NO | None |
| original_title | character varying | YES | None |
| processed_title | character varying | YES | None |
| original_description | character varying | YES | None |
| processed_description | character varying | YES | None |
| transformations_applied | character varying | NO | None |
| error_message | character varying | YES | None |
| processing_time_ms | integer | YES | None |
| processed_at | timestamp without time zone | NO | None |
| created_at | timestamp without time zone | NO | now() |
| updated_at | timestamp without time zone | NO | now() |

**Foreign Keys:**

- `feed_id` → `feeds.id`
- `item_id` → `items.id`

**Indexes:**

- `content_processing_logs_pkey`
- `ix_content_processing_logs_feed_id`
- `ix_content_processing_logs_item_id`

---

### dynamic_feed_templates

**Rows:** 3

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('dynamic_feed_templates_id_seq'::regclass) |
| name | character varying | NO | None |
| description | character varying | YES | None |
| version | character varying | NO | None |
| url_patterns | character varying | NO | None |
| field_mappings | character varying | NO | None |
| content_processing_rules | character varying | NO | None |
| quality_filters | character varying | NO | None |
| categorization_rules | character varying | NO | None |
| fetch_settings | character varying | NO | None |
| is_active | boolean | NO | None |
| is_builtin | boolean | NO | None |
| created_by | character varying | YES | None |
| created_at | timestamp without time zone | NO | None |
| updated_at | timestamp without time zone | NO | None |
| last_used | timestamp without time zone | YES | None |
| usage_count | integer | YES | 0 |

**Indexes:**

- `dynamic_feed_templates_pkey`
- `ix_dynamic_feed_templates_name`

---

### feed_categories

**Rows:** 31

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| feed_id | integer | NO | None |
| category_id | integer | NO | None |
| id | integer | NO | nextval('feed_categories_id_seq'::regclass) |
| created_at | timestamp without time zone | NO | now() |
| updated_at | timestamp without time zone | NO | now() |

**Foreign Keys:**

- `category_id` → `categories.id`
- `feed_id` → `feeds.id`

**Indexes:**

- `feed_categories_pkey`

---

### feed_configuration_changes

**Rows:** 4

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('feed_configuration_changes_id_seq'::regclass) |
| feed_id | integer | YES | None |
| template_id | integer | YES | None |
| change_type | character varying | NO | None |
| old_config | character varying | YES | None |
| new_config | character varying | YES | None |
| applied_at | timestamp without time zone | YES | None |
| created_by | character varying | YES | None |
| created_at | timestamp without time zone | NO | None |
| updated_at | timestamp without time zone | NO | now() |

**Foreign Keys:**

- `feed_id` → `feeds.id`
- `template_id` → `dynamic_feed_templates.id`

**Indexes:**

- `feed_configuration_changes_pkey`
- `ix_feed_configuration_changes_change_type`
- `ix_feed_configuration_changes_feed_id`
- `ix_feed_configuration_changes_template_id`

---

### feed_health

**Rows:** 37

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('feed_health_id_seq'::regclass) |
| feed_id | integer | NO | None |
| ok_ratio | double precision | NO | None |
| consecutive_failures | integer | NO | None |
| avg_response_time_ms | double precision | YES | None |
| last_success | timestamp without time zone | YES | None |
| last_failure | timestamp without time zone | YES | None |
| uptime_24h | double precision | NO | None |
| uptime_7d | double precision | NO | None |
| updated_at | timestamp without time zone | NO | None |
| created_at | timestamp without time zone | YES | now() |

**Foreign Keys:**

- `feed_id` → `feeds.id`

**Indexes:**

- `feed_health_feed_id_key`
- `feed_health_pkey`

---

### feed_limits

**Rows:** 2

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('feed_limits_id_seq'::regclass) |
| feed_id | integer | NO | None |
| max_analyses_per_day | integer | YES | None |
| max_analyses_per_hour | integer | YES | None |
| min_interval_minutes | integer | YES | 30 |
| daily_cost_limit | double precision | YES | None |
| monthly_cost_limit | double precision | YES | None |
| cost_alert_threshold | double precision | YES | None |
| max_items_per_analysis | integer | YES | None |
| max_queue_priority | character varying | YES | 'MEDIUM'::character varying |
| emergency_stop_enabled | boolean | YES | false |
| auto_disable_on_error_rate | double precision | YES | None |
| auto_disable_on_cost_breach | boolean | YES | true |
| alert_email | character varying | YES | None |
| alert_on_limit_breach | boolean | YES | true |
| alert_on_cost_threshold | boolean | YES | true |
| custom_settings | jsonb | YES | '{}'::jsonb |
| is_active | boolean | YES | true |
| violations_count | integer | YES | 0 |
| last_violation_at | timestamp with time zone | YES | None |
| created_at | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| updated_at | timestamp with time zone | YES | CURRENT_TIMESTAMP |

**Foreign Keys:**

- `feed_id` → `feeds.id`

**Indexes:**

- `ix_feed_limits_feed_id`
- `ix_feed_limits_feed_active`
- `feed_limits_pkey`
- `feed_limits_feed_id_key`

---

### feed_metrics

**Rows:** 3

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('feed_metrics_id_seq'::regclass) |
| feed_id | integer | NO | None |
| metric_date | date | NO | None |
| total_analyses | integer | NO | None |
| auto_analyses | integer | NO | None |
| manual_analyses | integer | NO | None |
| scheduled_analyses | integer | NO | None |
| total_items_processed | integer | NO | None |
| successful_items | integer | NO | None |
| failed_items | integer | NO | None |
| total_cost_usd | double precision | NO | None |
| input_cost_usd | double precision | NO | None |
| output_cost_usd | double precision | NO | None |
| cached_cost_usd | double precision | NO | None |
| total_tokens_used | integer | NO | None |
| input_tokens | integer | NO | None |
| output_tokens | integer | NO | None |
| cached_tokens | integer | NO | None |
| avg_processing_time_seconds | double precision | NO | None |
| avg_items_per_run | double precision | NO | None |
| success_rate | double precision | NO | None |
| total_queue_time_seconds | double precision | NO | None |
| avg_queue_time_seconds | double precision | NO | None |
| max_queue_time_seconds | double precision | NO | None |
| model_usage | json | YES | None |
| created_at | timestamp with time zone | YES | None |
| updated_at | timestamp with time zone | YES | None |

**Foreign Keys:**

- `feed_id` → `feeds.id`

**Indexes:**

- `ix_feed_metrics_metric_date`
- `ix_feed_metrics_feed_id`
- `feed_metrics_pkey`
- `ix_feed_metrics_feed_date`

---

### feed_processor_configs

**Rows:** 0

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('feed_processor_configs_id_seq'::regclass) |
| feed_id | integer | NO | None |
| processor_type | USER-DEFINED | NO | None |
| config_json | character varying | NO | None |
| is_active | boolean | NO | None |
| created_at | timestamp without time zone | NO | None |
| updated_at | timestamp without time zone | NO | None |

**Foreign Keys:**

- `feed_id` → `feeds.id`

**Indexes:**

- `feed_processor_configs_feed_id_key`
- `feed_processor_configs_pkey`

---

### feed_scheduler_state

**Rows:** 2

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('feed_scheduler_state_id_seq'::regclass) |
| scheduler_instance | character varying | NO | None |
| last_config_check | timestamp without time zone | YES | None |
| last_feed_config_hash | character varying | YES | None |
| last_template_config_hash | character varying | YES | None |
| is_active | boolean | NO | None |
| started_at | timestamp without time zone | YES | None |
| last_heartbeat | timestamp without time zone | YES | None |
| created_at | timestamp without time zone | NO | None |
| updated_at | timestamp without time zone | NO | None |

**Indexes:**

- `feed_scheduler_state_pkey`
- `ix_feed_scheduler_state_scheduler_instance`

---

### feed_template_assignments

**Rows:** 0

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('feed_template_assignments_id_seq'::regclass) |
| feed_id | integer | NO | None |
| template_id | integer | NO | None |
| custom_overrides | character varying | NO | None |
| is_active | boolean | NO | None |
| priority | integer | NO | None |
| assigned_by | character varying | YES | None |
| created_at | timestamp without time zone | NO | None |
| updated_at | timestamp without time zone | NO | None |

**Foreign Keys:**

- `feed_id` → `feeds.id`
- `template_id` → `dynamic_feed_templates.id`

**Indexes:**

- `feed_template_assignments_pkey`
- `ix_feed_template_assignments_feed_id`
- `ix_feed_template_assignments_template_id`

---

### feed_types

**Rows:** 0

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('feed_types_id_seq'::regclass) |
| name | character varying | NO | None |
| default_interval_minutes | integer | NO | None |
| description | character varying | YES | None |
| created_at | timestamp without time zone | NO | None |

**Indexes:**

- `feed_types_pkey`
- `ix_feed_types_name`

---

### feed_violations

**Rows:** 0

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('feed_violations_id_seq'::regclass) |
| feed_id | integer | NO | None |
| violation_type | character varying | NO | None |
| violation_date | date | NO | None |
| violation_time | timestamp with time zone | NO | None |
| limit_value | double precision | YES | None |
| actual_value | double precision | YES | None |
| threshold_percentage | double precision | YES | None |
| action_taken | character varying | YES | 'LOGGED'::character varying |
| auto_resolved | boolean | YES | false |
| resolved_at | timestamp with time zone | YES | None |
| analysis_run_id | integer | YES | None |
| error_message | text | YES | None |
| metadata | jsonb | YES | '{}'::jsonb |
| created_at | timestamp with time zone | YES | CURRENT_TIMESTAMP |

**Foreign Keys:**

- `feed_id` → `feeds.id`
- `analysis_run_id` → `analysis_runs.id`

**Indexes:**

- `ix_feed_violations_feed_id`
- `feed_violations_pkey`
- `ix_feed_violations_violation_type`
- `ix_feed_violations_violation_date`
- `ix_feed_violations_feed_date`
- `ix_feed_violations_type_date`

---

### feeds

**Rows:** 37

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('feeds_id_seq'::regclass) |
| url | character varying | NO | None |
| title | character varying | YES | None |
| description | character varying | YES | None |
| status | USER-DEFINED | NO | None |
| fetch_interval_minutes | integer | NO | None |
| last_fetched | timestamp without time zone | YES | None |
| next_fetch_scheduled | timestamp without time zone | YES | None |
| last_modified | character varying | YES | None |
| etag | character varying | YES | None |
| configuration_hash | character varying | YES | None |
| source_id | integer | NO | None |
| feed_type_id | integer | YES | None |
| created_at | timestamp without time zone | NO | None |
| updated_at | timestamp without time zone | NO | None |
| auto_analyze_enabled | boolean | NO | false |

**Foreign Keys:**

- `feed_type_id` → `feed_types.id`
- `source_id` → `sources.id`

**Indexes:**

- `feeds_pkey`
- `ix_feeds_url`

---

### fetch_log

**Rows:** 28,684

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('fetch_log_id_seq'::regclass) |
| feed_id | integer | NO | None |
| started_at | timestamp without time zone | NO | None |
| completed_at | timestamp without time zone | YES | None |
| status | character varying | NO | None |
| items_found | integer | NO | None |
| items_new | integer | NO | None |
| error_message | character varying | YES | None |
| response_time_ms | integer | YES | None |

**Foreign Keys:**

- `feed_id` → `feeds.id`

**Indexes:**

- `fetch_log_pkey`

---

### item_analysis

**Rows:** 2,674

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| item_id | bigint | NO | None |
| sentiment_json | jsonb | NO | '{}'::jsonb |
| impact_json | jsonb | NO | '{}'::jsonb |
| model_tag | text | YES | None |
| updated_at | timestamp with time zone | NO | now() |

**Foreign Keys:**

- `item_id` → `items.id`

**Indexes:**

- `item_analysis_pkey`
- `idx_item_analysis_updated`
- `idx_item_analysis_sentiment_label`
- `idx_item_analysis_impact_overall`
- `idx_item_analysis_urgency`
- `item_analysis_item_id_idx`

---

### item_tags

**Rows:** 0

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('item_tags_id_seq'::regclass) |
| item_id | integer | NO | None |
| tag | character varying | NO | None |
| created_at | timestamp without time zone | NO | now() |
| updated_at | timestamp without time zone | NO | now() |

**Foreign Keys:**

- `item_id` → `items.id`

**Indexes:**

- `item_tags_pkey`
- `ix_item_tags_tag`

---

### items

**Rows:** 7,177

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('items_id_seq'::regclass) |
| title | character varying | NO | None |
| link | character varying | NO | None |
| description | character varying | YES | None |
| content | character varying | YES | None |
| author | character varying | YES | None |
| published | timestamp without time zone | YES | None |
| guid | character varying | YES | None |
| content_hash | character varying | NO | None |
| feed_id | integer | NO | None |
| created_at | timestamp without time zone | NO | None |

**Foreign Keys:**

- `feed_id` → `feeds.id`

**Indexes:**

- `items_pkey`
- `ix_items_content_hash`
- `ix_items_guid`
- `ix_items_link`
- `items_feed_timeline_idx`
- `items_published_idx`
- `items_content_hash_idx`

---

### processor_templates

**Rows:** 0

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('processor_templates_id_seq'::regclass) |
| name | character varying | NO | None |
| processor_type | USER-DEFINED | NO | None |
| description | character varying | YES | None |
| config_json | character varying | NO | None |
| url_patterns | character varying | NO | None |
| is_builtin | boolean | NO | None |
| is_active | boolean | NO | None |
| created_at | timestamp without time zone | NO | None |
| updated_at | timestamp without time zone | NO | None |

**Indexes:**

- `processor_templates_pkey`
- `ix_processor_templates_name`

---

### queue_metrics

**Rows:** 0

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('queue_metrics_id_seq'::regclass) |
| metric_date | date | NO | None |
| metric_hour | integer | NO | None |
| items_processed | integer | NO | None |
| items_failed | integer | NO | None |
| items_cancelled | integer | NO | None |
| total_processing_time_seconds | double precision | NO | None |
| avg_processing_time_seconds | double precision | NO | None |
| min_processing_time_seconds | double precision | NO | None |
| max_processing_time_seconds | double precision | NO | None |
| total_queue_time_seconds | double precision | NO | None |
| avg_queue_time_seconds | double precision | NO | None |
| min_queue_time_seconds | double precision | NO | None |
| max_queue_time_seconds | double precision | NO | None |
| high_priority_processed | integer | NO | None |
| medium_priority_processed | integer | NO | None |
| low_priority_processed | integer | NO | None |
| max_queue_length | integer | NO | None |
| avg_queue_length | double precision | NO | None |
| emergency_stops | integer | NO | None |
| created_at | timestamp with time zone | YES | None |
| updated_at | timestamp with time zone | YES | None |

**Indexes:**

- `queue_metrics_pkey`
- `ix_queue_metrics_date_hour`
- `ix_queue_metrics_metric_date`
- `ix_queue_metrics_metric_hour`

---

### queued_runs

**Rows:** 1

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('queued_runs_id_seq'::regclass) |
| priority | USER-DEFINED | NO | None |
| status | USER-DEFINED | NO | None |
| scope_hash | character varying | NO | None |
| triggered_by | character varying | NO | None |
| scope_json | json | YES | None |
| params_json | json | YES | None |
| created_at | timestamp with time zone | YES | None |
| started_at | timestamp with time zone | YES | None |
| completed_at | timestamp with time zone | YES | None |
| analysis_run_id | integer | YES | None |
| error_message | character varying | YES | None |
| queue_position | integer | NO | None |

**Indexes:**

- `queued_runs_pkey`
- `ix_queued_runs_queue_position`
- `ix_queued_runs_scope_hash`
- `ix_queued_runs_status`

---

### sources

**Rows:** 38

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('sources_id_seq'::regclass) |
| name | character varying | NO | None |
| type | USER-DEFINED | NO | None |
| description | character varying | YES | None |
| created_at | timestamp without time zone | NO | None |
| updated_at | timestamp with time zone | YES | now() |

**Indexes:**

- `sources_pkey`
- `ix_sources_name`

---

### user_settings

**Rows:** 1

**Columns:**

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | integer | NO | nextval('user_settings_id_seq'::regclass) |
| default_limit | integer | NO | None |
| default_rate_per_second | double precision | NO | None |
| default_model_tag | character varying | NO | None |
| default_dry_run | boolean | NO | None |
| default_override_existing | boolean | NO | None |
| extra_settings | json | YES | None |
| created_at | timestamp without time zone | NO | None |
| updated_at | timestamp without time zone | NO | None |
| user_id | character varying | NO | None |

**Indexes:**

- `user_settings_pkey`
- `ix_user_settings_user_id`

---

