# Special Reports - Process Flow & Data Flow Documentation

## Overview

Special Reports is a feature that automatically generates customized news reports by:
1. Selecting relevant articles based on criteria
2. Analyzing them with LLM
3. Generating a structured report for a specific target audience

---

## 1. Configuration Phase

### 1.1 Creating a Special Report

**Entry Point:** `/admin/special-reports` → "Create New" Button

**User Input (via UI):**
- **Basic Info:**
  - `name`: Report name (e.g., "Security Intelligence Brief")
  - `description`: Purpose/scope
  - `target_audience`: Who it's for (e.g., "IT Managers")

- **LLM Configuration:**
  - `llm_model`: Model to use (gpt-4o, gpt-4o-mini, gpt-3.5-turbo)
  - `prompt_template`: Custom prompt (optional, defaults to system template)

- **Article Selection Criteria (`selection_criteria` JSONB):**
  - `feed_ids`: List of feed IDs to include (e.g., [12, 40, 57])
  - `timeframe_hours`: Look back period (e.g., 24 hours)
  - `max_articles`: Maximum articles to include (e.g., 20)
  - `min_impact_score`: Minimum impact (0.0-1.0)
  - `min_sentiment_score`: Minimum sentiment (-1.0 to 1.0)
  - `keywords`: Include keywords (e.g., ["security", "breach"])
  - `exclude_keywords`: Exclude keywords (e.g., ["spam"])

- **Scheduling:**
  - `generation_schedule`: Cron expression (e.g., "0 8 * * *" = daily at 8 AM)
  - `is_active`: Enable/disable

**Database Storage:**
```sql
INSERT INTO special_reports (
    name, description, target_audience,
    llm_model, prompt_template,
    selection_criteria,
    generation_schedule, is_active,
    created_at, updated_at
) VALUES (...);
```

**Files Involved:**
- UI: `templates/admin/special_reports.html`
- Backend: `app/web/views/special_report_views.py:htmx_create_special_report()`
- Model: `app/models/special_reports.py:SpecialReport`

---

## 2. Trigger Phase

### 2.1 How Reports are Triggered

**Three Trigger Methods:**

#### A. **Manual Trigger** (On-Demand)
- User clicks "Generate Now" button in UI
- POST request to `/htmx/special_reports/{id}/generate`
- Immediate execution

#### B. **Scheduled Trigger** (Cron-based)
- Background scheduler checks `generation_schedule` field
- Runs based on cron expression (e.g., daily at 8 AM)
- Only active reports (`is_active = true`)

**Scheduler Location:** `app/services/special_report_scheduler.py` (TODO: to be implemented)

#### C. **API Trigger** (External)
- POST `/api/v1/special-reports/{id}/generate`
- Allows external systems to trigger generation

**Files Involved:**
- Manual: `app/web/views/special_report_views.py:htmx_generate_report()`
- Scheduled: `app/services/special_report_scheduler.py` (TODO)
- API: `app/api/v1/special_reports.py` (TODO)

---

## 3. Article Selection Phase

### 3.1 Query Building

**Process:**
1. Read `selection_criteria` from Special Report config
2. Build SQL query with filters:

```python
from sqlmodel import select, and_, or_
from app.models.content import Item

# Base query
query = select(Item)

# Filter 1: Feed IDs
if feed_ids := criteria.get('feed_ids'):
    query = query.where(Item.feed_id.in_(feed_ids))

# Filter 2: Timeframe
if timeframe_hours := criteria.get('timeframe_hours'):
    cutoff = datetime.now() - timedelta(hours=timeframe_hours)
    query = query.where(Item.published_at >= cutoff)

# Filter 3: Impact Score
if min_impact := criteria.get('min_impact_score'):
    query = query.where(Item.impact_score >= min_impact)

# Filter 4: Sentiment Score
if min_sentiment := criteria.get('min_sentiment_score'):
    query = query.where(Item.sentiment_score >= min_sentiment)

# Filter 5: Keywords (JSONB search)
if keywords := criteria.get('keywords'):
    keyword_conditions = [
        Item.title.ilike(f"%{kw}%") | Item.summary.ilike(f"%{kw}%")
        for kw in keywords
    ]
    query = query.where(or_(*keyword_conditions))

# Filter 6: Exclude Keywords
if exclude_kw := criteria.get('exclude_keywords'):
    for kw in exclude_kw:
        query = query.where(
            ~(Item.title.ilike(f"%{kw}%") | Item.summary.ilike(f"%{kw}%"))
        )

# Limit results
max_articles = criteria.get('max_articles', 50)
query = query.limit(max_articles)

# Order by relevance (impact score desc, then published date)
query = query.order_by(Item.impact_score.desc(), Item.published_at.desc())

# Execute
articles = session.exec(query).all()
```

### 3.2 Article Data Structure

**Each selected article contains:**
```python
{
    "id": 123,
    "title": "Major Security Breach at Corp X",
    "link": "https://...",
    "summary": "Full article summary...",
    "published_at": "2025-10-03T10:30:00Z",
    "feed_id": 12,
    "feed_title": "Security News Daily",
    "impact_score": 0.85,
    "sentiment_score": -0.6,
    "categories": ["security", "breach"],
    "entities": ["Corp X", "ransomware"]
}
```

**Files Involved:**
- Query builder: `app/services/special_report_service.py:select_articles()` (TODO)
- Model: `app/models/content.py:Item`

---

## 4. LLM Analysis Phase

### 4.1 Prompt Construction

**Template Variables:**
- `{target_audience}`: From Special Report config
- `{article_count}`: Number of selected articles
- `{timeframe}`: Time period covered
- `{articles}`: Formatted article list

**Default Prompt Template:**
```
You are an AI assistant creating a {report_type} for {target_audience}.

Analyze the following {article_count} articles from the last {timeframe} hours:

{articles}

Generate a comprehensive report with:
1. Executive Summary (2-3 paragraphs)
2. Key Themes & Trends
3. Critical Events (prioritized by impact)
4. Actionable Insights & Recommendations

Focus on information relevant to {target_audience}.
```

**Article Formatting for LLM:**
```python
article_text = "\n\n".join([
    f"Article {i+1}:\n"
    f"Title: {article.title}\n"
    f"Source: {article.feed_title}\n"
    f"Published: {article.published_at}\n"
    f"Impact: {article.impact_score}\n"
    f"Summary: {article.summary}\n"
    f"Link: {article.link}"
    for i, article in enumerate(articles)
])
```

### 4.2 LLM API Call

**Request Structure (OpenAI API):**
```python
import openai

response = openai.ChatCompletion.create(
    model=special_report.llm_model,  # e.g., "gpt-4o"
    messages=[
        {
            "role": "system",
            "content": "You are a professional news analyst creating executive briefings."
        },
        {
            "role": "user",
            "content": prompt  # Constructed prompt with articles
        }
    ],
    temperature=0.7,
    max_tokens=2000
)

report_content = response.choices[0].message.content
```

**Cost Tracking:**
```python
# Tokens used
prompt_tokens = response.usage.prompt_tokens
completion_tokens = response.usage.completion_tokens
total_tokens = response.usage.total_tokens

# Cost calculation (example for gpt-4o)
cost = (prompt_tokens * 0.03 / 1000) + (completion_tokens * 0.06 / 1000)
```

**Files Involved:**
- LLM service: `app/services/llm_service.py` (existing, reuse)
- Prompt templates: `app/templates/prompts/special_report_template.txt` (TODO)

---

## 5. Report Generation Phase

### 5.1 Report Structure

**Generated Report Format (Markdown):**
```markdown
# {Special Report Name}
**Target Audience:** {target_audience}
**Generated:** {timestamp}
**Period Covered:** {timeframe}
**Articles Analyzed:** {article_count}

---

## Executive Summary
{LLM-generated summary}

---

## Key Themes & Trends
{LLM-generated themes}

---

## Critical Events
{LLM-generated events with links}

---

## Actionable Insights
{LLM-generated recommendations}

---

## Source Articles
1. [{article.title}]({article.link}) - {article.feed_title}
2. ...
```

### 5.2 Database Storage

**Insert into `special_report_generations` table:**
```sql
INSERT INTO special_report_generations (
    special_report_id,
    content,
    article_count,
    llm_tokens_used,
    llm_cost,
    generation_time_seconds,
    status,
    generated_at
) VALUES (
    1,
    '# Security Intelligence Brief...',
    15,
    1850,
    0.095,
    3.5,
    'completed',
    NOW()
);
```

**Files Involved:**
- Generator: `app/services/special_report_generator.py` (TODO)
- Model: `app/models/special_reports.py:SpecialReportGeneration`

---

## 6. Delivery Phase

### 6.1 Output Formats

**A. Web View** (Primary)
- Rendered as HTML from Markdown
- Available at `/admin/special-reports/{id}/generations/{gen_id}`
- Displays with Bootstrap styling

**B. Email Delivery** (TODO)
- Convert Markdown to HTML email
- Send to configured recipients
- Use template: `templates/emails/special_report.html`

**C. API Export** (TODO)
- GET `/api/v1/special-reports/{id}/generations/{gen_id}`
- Returns JSON with content + metadata

**D. PDF Export** (TODO)
- Generate PDF from Markdown
- Download link in UI

### 6.2 Notification

**When report is generated:**
1. Update Special Report `last_generated_at` timestamp
2. Send notification (if configured):
   - Email to recipients
   - Webhook to external system
   - Slack/Teams message (TODO)

---

## 7. Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     1. CONFIGURATION                            │
│  User → UI Form → special_reports table                         │
│  (name, criteria, schedule, LLM config)                         │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     2. TRIGGER                                  │
│  • Manual (UI button)                                           │
│  • Scheduled (Cron job)                                         │
│  • API call                                                     │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                3. ARTICLE SELECTION                             │
│  Read selection_criteria → Build SQL Query → Filter items       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ SELECT * FROM items WHERE                               │   │
│  │   feed_id IN (12, 40, 57)                               │   │
│  │   AND published_at >= NOW() - INTERVAL '24 hours'      │   │
│  │   AND impact_score >= 0.5                               │   │
│  │   AND (title ILIKE '%security%' OR ...)                 │   │
│  │ ORDER BY impact_score DESC LIMIT 20;                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│  Result: List of Article objects                                │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                4. PROMPT CONSTRUCTION                           │
│  Template + Articles → Formatted Prompt                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ You are creating a report for IT Managers.              │   │
│  │                                                         │   │
│  │ Article 1:                                              │   │
│  │ Title: Major Breach at Corp X                           │   │
│  │ Impact: 0.85                                            │   │
│  │ Summary: ...                                            │   │
│  │                                                         │   │
│  │ Article 2: ...                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                5. LLM ANALYSIS                                  │
│  OpenAI API Call (gpt-4o)                                       │
│  Input: Prompt (1500 tokens) → Output: Report (500 tokens)     │
│  Cost: $0.095                                                   │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                6. REPORT GENERATION                             │
│  LLM Response → Format as Markdown → Store in DB                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ # Security Intelligence Brief                           │   │
│  │ ## Executive Summary                                    │   │
│  │ Three major security incidents...                       │   │
│  │                                                         │   │
│  │ ## Key Themes                                           │   │
│  │ - Ransomware attacks increasing...                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│  Save to: special_report_generations table                      │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                7. DELIVERY                                      │
│  • Web: Render HTML at /admin/special-reports/1/gen/42         │
│  • Email: Send to recipients (TODO)                             │
│  • API: Export as JSON (TODO)                                   │
│  • PDF: Generate download (TODO)                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Database Schema

### 8.1 Main Tables

**`special_reports`** (Configuration)
```sql
CREATE TABLE special_reports (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    target_audience VARCHAR(255),

    -- LLM Config
    llm_model VARCHAR(50) DEFAULT 'gpt-4o',
    prompt_template TEXT,

    -- Article Selection
    selection_criteria JSONB,  -- {feed_ids, timeframe_hours, keywords, etc.}

    -- Scheduling
    generation_schedule VARCHAR(100),  -- Cron expression
    is_active BOOLEAN DEFAULT true,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_generated_at TIMESTAMP
);
```

**`special_report_generations`** (Output)
```sql
CREATE TABLE special_report_generations (
    id SERIAL PRIMARY KEY,
    special_report_id INTEGER REFERENCES special_reports(id) ON DELETE CASCADE,

    -- Content
    content TEXT,  -- Markdown report
    article_count INTEGER,

    -- Metrics
    llm_tokens_used INTEGER,
    llm_cost DECIMAL(10, 4),
    generation_time_seconds DECIMAL(6, 2),

    -- Status
    status VARCHAR(20),  -- 'pending', 'completed', 'failed'
    error_message TEXT,

    generated_at TIMESTAMP DEFAULT NOW()
);
```

### 8.2 Related Tables

**`items`** (Source Articles)
- Fields used: `id`, `title`, `link`, `summary`, `published_at`, `feed_id`, `impact_score`, `sentiment_score`

**`feeds`** (Feed Information)
- Fields used: `id`, `title`, `url` (for source attribution)

---

## 9. API Endpoints

### Current Endpoints

**Web UI (HTMX):**
```
GET    /admin/special-reports                  # List page
GET    /htmx/special_reports/list             # HTMX list
GET    /htmx/special_reports/{id}/edit-form   # Edit form
POST   /htmx/special_reports/create           # Create new
PUT    /htmx/special_reports/{id}/update      # Update config
DELETE /htmx/special_reports/{id}/delete      # Delete
POST   /htmx/special_reports/{id}/generate    # Trigger generation (TODO)
```

### Future API Endpoints (TODO)

**REST API:**
```
GET    /api/v1/special-reports                    # List all
GET    /api/v1/special-reports/{id}               # Get one
POST   /api/v1/special-reports                    # Create
PUT    /api/v1/special-reports/{id}               # Update
DELETE /api/v1/special-reports/{id}               # Delete
POST   /api/v1/special-reports/{id}/generate      # Trigger generation
GET    /api/v1/special-reports/{id}/generations   # List generations
GET    /api/v1/special-reports/{id}/generations/{gen_id}  # Get report
```

---

## 10. File Structure

```
app/
├── models/
│   └── special_reports.py           # SpecialReport, SpecialReportGeneration models
├── services/
│   ├── special_report_service.py    # Article selection logic (TODO)
│   ├── special_report_generator.py  # Report generation orchestration (TODO)
│   ├── special_report_scheduler.py  # Cron-based scheduling (TODO)
│   └── llm_service.py               # OpenAI API wrapper (exists)
├── web/views/
│   └── special_report_views.py      # HTMX endpoints
├── api/v1/
│   └── special_reports.py           # REST API endpoints (TODO)
└── templates/
    ├── admin/special_reports.html   # UI page
    └── prompts/
        └── special_report_template.txt  # Default prompt (TODO)

docs/
└── Special-Reports-Flow.md          # This file
```

---

## 11. Implementation Status

### ✅ Completed
- Database models (`SpecialReport`, `SpecialReportGeneration`)
- Web UI (CRUD operations via HTMX)
- Edit form with full configuration options
- Basic structure

### 🚧 In Progress
- N/A

### 📋 TODO (Priority Order)
1. **Article Selection Service** (`special_report_service.py:select_articles()`)
   - Implement SQL query builder
   - Filter by all criteria
   - Return ranked articles

2. **Report Generator** (`special_report_generator.py:generate_report()`)
   - Construct prompt from template
   - Call LLM service
   - Parse response
   - Save to database

3. **Generate Endpoint** (`/htmx/special_reports/{id}/generate`)
   - Trigger generation flow
   - Handle async execution
   - Return status updates

4. **Scheduler** (`special_report_scheduler.py`)
   - Cron-based trigger
   - Check active reports
   - Queue generation jobs

5. **Email Delivery** (`email_service.py`)
   - Convert Markdown to HTML email
   - Send to recipients

6. **API Endpoints** (`api/v1/special_reports.py`)
   - Full REST API
   - Swagger docs

---

## 12. Example: Complete Generation Flow

**User Action:** Clicks "Generate Now" for "Security Intelligence Brief"

**Step-by-Step:**

1. **Trigger** → POST `/htmx/special_reports/1/generate`

2. **Load Config** → Read `special_reports` table (ID=1):
   ```json
   {
     "name": "Security Intelligence Brief",
     "target_audience": "IT Managers",
     "llm_model": "gpt-4o",
     "selection_criteria": {
       "feed_ids": [12, 40, 57],
       "timeframe_hours": 24,
       "min_impact_score": 0.5,
       "keywords": ["security", "breach"]
     }
   }
   ```

3. **Select Articles** → Query `items` table:
   ```sql
   SELECT * FROM items
   WHERE feed_id IN (12, 40, 57)
     AND published_at >= NOW() - INTERVAL '24 hours'
     AND impact_score >= 0.5
     AND (title ILIKE '%security%' OR title ILIKE '%breach%')
   ORDER BY impact_score DESC
   LIMIT 20;
   ```
   **Result:** 15 articles found

4. **Build Prompt:**
   ```
   You are creating a Security Intelligence Brief for IT Managers.

   Analyze these 15 articles from the last 24 hours:

   Article 1:
   Title: Major Ransomware Attack Hits Healthcare Provider
   Source: Security News Daily
   Impact: 0.92
   Summary: A major healthcare provider disclosed...

   [... 14 more articles ...]

   Generate a comprehensive report with:
   1. Executive Summary
   2. Key Themes & Trends
   3. Critical Events
   4. Actionable Insights
   ```

5. **Call LLM:**
   ```python
   response = openai.ChatCompletion.create(
       model="gpt-4o",
       messages=[{"role": "user", "content": prompt}],
       temperature=0.7
   )
   # Returns: 1850 tokens used, $0.095 cost
   ```

6. **Save Report:**
   ```sql
   INSERT INTO special_report_generations (
       special_report_id, content, article_count,
       llm_tokens_used, llm_cost, status
   ) VALUES (
       1, '# Security Intelligence Brief\n\n## Executive Summary...',
       15, 1850, 0.095, 'completed'
   );
   ```

7. **Display** → Redirect to `/admin/special-reports/1/generations/42`

**Total Time:** ~5 seconds
**Cost:** $0.095

---

## 13. Cost Estimation

**Per Report Generation:**

| Model | Input Tokens | Output Tokens | Cost per Report | Monthly (30 reports) |
|-------|--------------|---------------|-----------------|---------------------|
| gpt-4o | ~1500 | ~500 | $0.095 | $2.85 |
| gpt-4o-mini | ~1500 | ~500 | $0.015 | $0.45 |
| gpt-3.5-turbo | ~1500 | ~500 | $0.003 | $0.09 |

**Pricing (as of 2025):**
- gpt-4o: $0.03/1K input, $0.06/1K output
- gpt-4o-mini: $0.003/1K input, $0.006/1K output
- gpt-3.5-turbo: $0.0005/1K input, $0.0015/1K output

---

## 14. Performance Considerations

### Optimization Strategies

1. **Caching:**
   - Cache article queries for 5 minutes
   - Reuse if criteria unchanged

2. **Async Processing:**
   - Queue generation jobs with Celery/RQ
   - Don't block UI requests

3. **Rate Limiting:**
   - Max 10 generations per report per day
   - Prevent LLM API abuse

4. **Token Optimization:**
   - Summarize long articles before LLM
   - Use truncation strategies

5. **Database Indexes:**
   ```sql
   CREATE INDEX idx_items_selection ON items(
       feed_id, published_at, impact_score
   );
   ```

---

## 15. Error Handling

### Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| No articles found | Criteria too strict | Relax filters, notify user |
| LLM timeout | Large prompt | Reduce article count |
| LLM API error | Rate limit/outage | Retry with exponential backoff |
| Invalid JSON | Malformed criteria | Validate input, use defaults |

**Error Logging:**
```python
try:
    report = generate_report(special_report_id)
except Exception as e:
    logger.error(f"Report generation failed: {e}", extra={
        "special_report_id": special_report_id,
        "error_type": type(e).__name__
    })
    # Save to special_report_generations with status='failed'
```

---

## Next Steps for Implementation

1. ✅ Read this documentation
2. 🔧 Implement `special_report_service.py:select_articles()`
3. 🔧 Implement `special_report_generator.py:generate_report()`
4. 🔧 Create HTMX generate endpoint
5. 🧪 Test with real data
6. 📧 Add email delivery
7. 📅 Implement scheduler
8. 🚀 Deploy to production

---

**Last Updated:** 2025-10-03
**Status:** Core infrastructure complete, generation logic pending
