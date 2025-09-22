# Entity Relationship Diagram - News MCP

## Visual Database Schema

```mermaid
erDiagram
    FEEDS ||--o{ ITEMS : contains
    FEEDS ||--o{ FETCH_LOG : has
    FEEDS ||--|| FEED_HEALTH : monitors
    FEEDS }o--|| SOURCES : belongs_to
    FEEDS }o--o| FEED_TYPES : has_type
    FEEDS }o--o{ FEED_CATEGORIES : categorized_as
    FEEDS ||--o{ FEED_TEMPLATE_ASSIGNMENTS : uses
    FEEDS ||--o| FEED_PROCESSOR_CONFIGS : configured_with

    ITEMS ||--o{ ITEM_TAGS : has
    ITEMS ||--o{ ITEM_ANALYSIS : analyzed_by
    ITEMS ||--o{ CONTENT_PROCESSING_LOGS : processed_by
    ITEMS }o--o{ ANALYSIS_RUN_ITEMS : included_in

    CATEGORIES ||--o{ FEED_CATEGORIES : groups

    DYNAMIC_FEED_TEMPLATES ||--o{ FEED_TEMPLATE_ASSIGNMENTS : assigned_to
    DYNAMIC_FEED_TEMPLATES ||--o{ FEED_CONFIGURATION_CHANGES : tracks

    ANALYSIS_RUNS ||--o{ ANALYSIS_RUN_ITEMS : contains

    PROCESSOR_TEMPLATES ||--o{ FEED_PROCESSOR_CONFIGS : implements

    FEEDS {
        int id PK
        string url UK
        string title
        string description
        string status
        int fetch_interval_minutes
        timestamp last_fetched
        timestamp next_fetch_scheduled
        int source_id FK
        int feed_type_id FK
        timestamp created_at
        timestamp updated_at
    }

    ITEMS {
        int id PK
        string title
        string link
        string description
        text content
        string author
        timestamp published
        string guid
        string content_hash UK
        int feed_id FK
        timestamp created_at
    }

    FETCH_LOG {
        int id PK
        int feed_id FK
        timestamp started_at
        timestamp completed_at
        string status
        int items_found
        int items_new
        string error_message
        int response_time_ms
    }

    FEED_HEALTH {
        int id PK
        int feed_id FK_UK
        float ok_ratio
        int consecutive_failures
        float avg_response_time_ms
        timestamp last_success
        timestamp last_failure
        float uptime_24h
        float uptime_7d
        timestamp updated_at
        timestamp created_at
    }

    SOURCES {
        int id PK
        string name
        string type
        timestamp created_at
        timestamp updated_at
    }

    CATEGORIES {
        int id PK
        string name UK
        string description
        timestamp created_at
        timestamp updated_at
    }

    FEED_TYPES {
        int id PK
        string name UK
        int default_interval_minutes
        timestamp created_at
        timestamp updated_at
    }

    DYNAMIC_FEED_TEMPLATES {
        int id PK
        string name UK
        string description
        string version
        json url_patterns
        json field_mappings
        json content_processing_rules
        json quality_filters
        json categorization_rules
        json fetch_settings
        boolean is_active
        boolean is_builtin
        string created_by
        timestamp created_at
        timestamp updated_at
        timestamp last_used
        int usage_count
    }

    ITEM_ANALYSIS {
        int id PK
        int item_id FK
        json analysis_data
        timestamp created_at
    }

    ANALYSIS_RUNS {
        int id PK
        timestamp started_at
        timestamp completed_at
        string status
        json parameters
    }
```

## Table Relationships Summary

### Primary Entities
- **FEEDS**: Central entity connecting sources, items, and monitoring
- **ITEMS**: Content storage with analysis and processing logs
- **DYNAMIC_FEED_TEMPLATES**: Configuration templates for feed processing

### One-to-Many Relationships
- Feed → Items (1:N)
- Feed → Fetch Logs (1:N)
- Feed → Feed Health (1:1)
- Source → Feeds (1:N)
- Feed Type → Feeds (1:N)
- Item → Item Tags (1:N)
- Item → Item Analysis (1:N)
- Item → Content Processing Logs (1:N)

### Many-to-Many Relationships
- Feeds ↔ Categories (via feed_categories)
- Feeds ↔ Dynamic Feed Templates (via feed_template_assignments)
- Items ↔ Analysis Runs (via analysis_run_items)

## Problem Areas Highlighted

### 🔴 Critical Issues
1. **basetablemodel** table - Artifact, should not exist
2. **Model-DB Mismatches**:
   - Items: Model expects updated_at, DB doesn't have it
   - Feed_health: Complex timestamp situation
   - Dynamic_feed_templates: Fields mismatch

### 🟡 Warning Areas
1. **Mixed Timestamp Patterns**:
   - Some tables: created_at only
   - Some tables: created_at + updated_at
   - fetch_log: started_at + completed_at (custom)

### 🟢 Stable Areas
1. Core relationships (Feed → Items)
2. Category and Source associations
3. Basic fetch logging

## Data Integrity Rules

### Constraints
- **Unique**: feed.url, category.name, feed_type.name, dynamic_feed_template.name
- **Foreign Keys**: All properly defined with CASCADE rules
- **Not Null**: Critical fields like feed.url, item.title, item.content_hash

### Business Rules
1. Each feed must belong to exactly one source
2. Feed health record is created automatically with feed
3. Items must have unique content_hash
4. Template assignments have priority for conflict resolution

## Migration Considerations

### Data Dependencies Order
1. **First**: sources, categories, feed_types (no dependencies)
2. **Second**: feeds (depends on sources, feed_types)
3. **Third**: items, feed_health, fetch_log (depend on feeds)
4. **Fourth**: All analysis and processing tables

### Risk Matrix
| Table | Risk Level | Issue | Impact |
|-------|------------|-------|---------|
| dynamic_feed_templates | HIGH | Field mismatch | Template system broken |
| feed_health | MEDIUM | Timestamp issues | Monitoring affected |
| items | MEDIUM | Missing updated_at | Some queries fail |
| basetablemodel | LOW | Shouldn't exist | Confusion only |

---

*This ERD represents the actual database state as of 2025-09-22*
*Use this as the source of truth for any model refactoring*