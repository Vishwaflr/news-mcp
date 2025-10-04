# Sentiment Analysis Guide

## Overview

News MCP uses AI-powered sentiment analysis to evaluate the tone, market impact, and urgency of news articles. This guide explains the scoring system, interpretation, and how to use sentiment data effectively.

---

## Sentiment Score System

### Overall Sentiment Score

**Range:** `-1.0` to `+1.0`

The overall sentiment score represents the general tone of the article:

| Score Range | Label | Meaning | Icon | Example Use Case |
|------------|-------|---------|------|------------------|
| `+0.5` to `+1.0` | **Positive** | Optimistic, bullish, good news | 🟢 | Product launches, positive earnings, partnerships |
| `-0.2` to `+0.5` | **Neutral** | Balanced, informational, mixed signals | ⚪ | Routine announcements, factual reports |
| `-1.0` to `-0.2` | **Negative** | Pessimistic, bearish, bad news | 🔴 | Layoffs, security breaches, losses |

**Score Interpretation:**
- **+1.0**: Extremely positive news (rare)
- **+0.7**: Very positive, strong bullish signal
- **+0.3**: Slightly positive, cautiously optimistic
- **0.0**: Completely neutral
- **-0.3**: Slightly negative, minor concerns
- **-0.7**: Very negative, strong bearish signal
- **-1.0**: Extremely negative news (rare)

### Confidence Score

**Range:** `0.0` to `1.0`

Indicates how confident the AI model is in its sentiment assessment:

| Score Range | Interpretation |
|------------|----------------|
| `0.8` - `1.0` | High confidence - clear sentiment signals |
| `0.5` - `0.8` | Medium confidence - mixed or ambiguous signals |
| `0.0` - `0.5` | Low confidence - unclear or contradictory signals |

**Usage:**
- Filter out low-confidence analyses (`< 0.6`) for critical decisions
- Use confidence as a reliability indicator when sorting by sentiment

---

## Market Analysis

### Market Sentiment Components

Each article includes three market-specific scores:

#### 1. Bullish Score
**Range:** `0.0` to `1.0`

Measures positive market indicators:
- `0.9` - `1.0`: Strong buy signals, major growth opportunity
- `0.6` - `0.9`: Moderate positive outlook
- `0.3` - `0.6`: Slight positive indicators
- `0.0` - `0.3`: Weak or no bullish signals

#### 2. Bearish Score
**Range:** `0.0` to `1.0`

Measures negative market indicators:
- `0.9` - `1.0`: Strong sell signals, major risks
- `0.6` - `0.9`: Moderate negative outlook
- `0.3` - `0.6`: Slight negative indicators
- `0.0` - `0.3`: Weak or no bearish signals

#### 3. Uncertainty Score
**Range:** `0.0` to `1.0`

Measures market ambiguity and unpredictability:
- `0.8` - `1.0`: High uncertainty, conflicting signals
- `0.5` - `0.8`: Moderate uncertainty, unclear direction
- `0.2` - `0.5`: Low uncertainty, clear trends
- `0.0` - `0.2`: Very low uncertainty, predictable outcome

### Time Horizon

Indicates the timeframe of market impact:

- **`short`**: Impact within days to weeks (earnings reports, product launches)
- **`medium`**: Impact within weeks to months (strategic shifts, partnerships)
- **`long`**: Impact within months to years (regulatory changes, industry trends)

---

## Impact & Urgency Scores

### Impact Score
**Range:** `0.0` to `1.0`

Measures the potential significance of the news:

| Score Range | Interpretation | Examples |
|------------|----------------|----------|
| `0.8` - `1.0` | Critical impact | Major acquisitions, security breaches, CEO changes |
| `0.6` - `0.8` | High impact | Product launches, earnings surprises, partnerships |
| `0.4` - `0.6` | Moderate impact | Feature updates, minor partnerships, routine changes |
| `0.2` - `0.4` | Low impact | Blog posts, minor announcements, clarifications |
| `0.0` - `0.2` | Minimal impact | Social media updates, minor fixes, routine maintenance |

### Urgency Score
**Range:** `0.0` to `1.0`

Measures how quickly action or attention is needed:

| Score Range | Interpretation | Action Needed |
|------------|----------------|---------------|
| `0.8` - `1.0` | Critical urgency | Immediate action required (breaking news, crises) |
| `0.6` - `0.8` | High urgency | Review within hours (time-sensitive developments) |
| `0.4` - `0.6` | Moderate urgency | Review within a day (important but not critical) |
| `0.2` - `0.4` | Low urgency | Review when convenient (informational) |
| `0.0` - `0.2` | No urgency | Optional reading (background information) |

### Volatility Score
**Range:** `0.0` to `1.0`

Measures potential for rapid market changes:
- `0.8` - `1.0`: Highly volatile situation, rapid changes expected
- `0.5` - `0.8`: Moderate volatility, some fluctuation likely
- `0.0` - `0.5`: Low volatility, stable situation

---

## Geopolitical Analysis

News MCP includes comprehensive geopolitical sentiment analysis for news with international implications.

### Geopolitical Score Fields

#### 1. Stability Score
**Range:** `-1.0` to `+1.0`

Assesses impact on regional/global stability:
- **+0.5 to +1.0**: Stabilizing (peace agreements, diplomatic breakthroughs)
- **-0.2 to +0.5**: Neutral (routine diplomatic activity)
- **-1.0 to -0.2**: Destabilizing (conflicts, political crises, sanctions)

#### 2. Economic Impact
**Range:** `0.0` to `1.0`

Economic consequences of geopolitical events:
- **0.8 - 1.0**: Major impact (trade wars, sanctions, currency crises)
- **0.5 - 0.8**: Significant (regional trade agreements, energy deals)
- **0.2 - 0.5**: Moderate (bilateral agreements, regulatory changes)
- **0.0 - 0.2**: Minimal (symbolic gestures, minor policy shifts)

#### 3. Security Relevance
**Range:** `0.0` to `1.0`

Military and security implications:
- **0.8 - 1.0**: Critical (armed conflicts, major deployments)
- **0.5 - 0.8**: High (military exercises, defense pacts)
- **0.2 - 0.5**: Moderate (security cooperation, equipment sales)
- **0.0 - 0.2**: Low (routine security matters)

#### 4. Diplomatic Impact
**Range:** `0.0` to `1.0` per region

Multi-regional assessment:
```json
{
  "global": 0.7,    // Worldwide diplomatic significance
  "western": 0.8,   // Impact on Western alliances
  "regional": 0.6   // Regional/local implications
}
```

#### 5. Escalation Potential
**Range:** `0.0` to `1.0`

Likelihood of situation escalating:
- **0.8 - 1.0**: High risk (border disputes, ultimatums, mobilizations)
- **0.5 - 0.8**: Moderate risk (tensions rising, threats issued)
- **0.2 - 0.5**: Low risk (manageable disagreements)
- **0.0 - 0.2**: Minimal risk (stable situation)

#### 6. Regions Affected
**Array of ISO 3166-1 alpha-2 codes**

Countries/regions directly impacted:
```json
["US", "CN", "JP", "EU", "MENA"]
```

Common region codes:
- `EU`: European Union
- `MENA`: Middle East & North Africa
- `APAC`: Asia-Pacific
- `LATAM`: Latin America

#### 7. Impact Beneficiaries & Affected Parties
**Arrays of country/actor codes**

Who benefits and who suffers:
```json
{
  "impact_beneficiaries": ["US", "JP"],  // Winners
  "impact_affected": ["RU", "CN"]        // Losers
}
```

#### 8. Alliance Activation
**Array of alliance names**

Which alliances may be involved:
```json
["NATO", "EU", "Five Eyes", "QUAD"]
```

#### 9. Conflict Type
**Enum:** `diplomatic | economic | military | hybrid`

Nature of geopolitical event:
- **diplomatic**: Diplomatic disputes, sanctions, negotiations
- **economic**: Trade wars, embargoes, financial measures
- **military**: Armed conflicts, military buildups
- **hybrid**: Multiple dimensions (e.g., sanctions + military posturing)

#### 10. Time Horizon
**Enum:** `short_term | medium_term | long_term`

Expected duration of impact:
- **short_term**: Days to weeks (immediate crisis)
- **medium_term**: Months (ongoing situation)
- **long_term**: Years (structural changes)

#### 11. Confidence Score
**Range:** `0.0` to `1.0`

AI confidence in geopolitical assessment:
- **0.8 - 1.0**: High confidence (clear indicators)
- **0.5 - 0.8**: Medium confidence (some ambiguity)
- **0.0 - 0.5**: Low confidence (insufficient information)

### Geopolitical JSON Example

```json
{
  "geopolitical": {
    "stability_score": -0.7,
    "economic_impact": 0.8,
    "security_relevance": 0.9,
    "diplomatic_impact": {
      "global": 0.8,
      "western": 0.9,
      "regional": 0.7
    },
    "escalation_potential": 0.6,
    "regions_affected": ["UA", "RU", "EU", "US"],
    "impact_beneficiaries": ["US", "EU"],
    "impact_affected": ["RU"],
    "time_horizon": "medium_term",
    "confidence": 0.85,
    "alliance_activation": ["NATO", "EU"],
    "conflict_type": "hybrid"
  }
}
```

### Using Geopolitical Data

#### Filter High-Impact Geopolitical Events
```python
# Critical geopolitical developments
SELECT * FROM items i
JOIN item_analysis ia ON i.id = ia.item_id
WHERE
  ia.sentiment_json->'geopolitical'->>'stability_score' < '-0.5'
  AND ia.sentiment_json->'geopolitical'->>'security_relevance' > '0.7'
ORDER BY i.published DESC;
```

#### Monitor Specific Regions
```python
# Track Middle East developments
SELECT * FROM items i
JOIN item_analysis ia ON i.id = ia.item_id
WHERE ia.sentiment_json->'geopolitical'->'regions_affected' @> '["MENA"]'
ORDER BY i.published DESC;
```

#### Escalation Risk Alerts
```python
# High escalation risk situations
if geopolitical["escalation_potential"] >= 0.8:
    if geopolitical["security_relevance"] >= 0.7:
        send_critical_alert("High escalation risk detected")
```

### Non-Geopolitical News

For domestic or non-geopolitical news, all geopolitical fields are set to neutral/zero:
```json
{
  "geopolitical": {
    "stability_score": 0.0,
    "economic_impact": 0.0,
    "security_relevance": 0.0,
    "diplomatic_impact": {"global": 0.0, "western": 0.0, "regional": 0.0},
    "escalation_potential": 0.0,
    "regions_affected": [],
    "impact_beneficiaries": [],
    "impact_affected": [],
    "time_horizon": "short_term",
    "confidence": 0.0,
    "alliance_activation": [],
    "conflict_type": "diplomatic"
  }
}
```

This indicates the analysis was performed but found no significant geopolitical implications.

---

## Practical Usage

### Filtering Articles by Sentiment

**API Example:**
```bash
# Get positive articles only
curl "http://localhost:8000/api/items/?sentiment=positive"

# Get negative articles only
curl "http://localhost:8000/api/items/?sentiment=negative"

# Get neutral articles only
curl "http://localhost:8000/api/items/?sentiment=neutral"
```

**Query Parameters:**
```python
# Python API client example
from news_mcp_client import NewsClient

client = NewsClient("http://localhost:8000")

# Filter by sentiment
positive_news = client.get_items(sentiment="positive")

# Filter by impact threshold
high_impact = client.get_items(impact_min=0.7)

# Filter by urgency
urgent_news = client.get_items(urgency_min=0.8)

# Combine filters
critical_negative = client.get_items(
    sentiment="negative",
    impact_min=0.7,
    urgency_min=0.7
)
```

### Sorting by Sentiment

```bash
# Sort by sentiment score (highest first)
curl "http://localhost:8000/api/items/?sort_by=sentiment_score&sort_desc=true"

# Sort by impact score
curl "http://localhost:8000/api/items/?sort_by=impact_score&sort_desc=true"
```

### Dashboard Usage

**Web UI Filters:**
1. Navigate to `/admin/items`
2. Use sentiment badges to filter:
   - Click 🟢 for positive articles
   - Click 🔴 for negative articles
   - Click ⚪ for neutral articles
3. Adjust impact/urgency sliders to refine results

**Manager Dashboard (`/admin/manager`):**
- View aggregate sentiment statistics
- Monitor sentiment trends over time
- Track high-urgency items in real-time

---

## Data Structure

### JSON Schema

Analysis results are stored in the `item_analysis` table with the following structure:

```json
{
  "sentiment": {
    "overall": {
      "label": "positive",
      "score": 0.75,
      "confidence": 0.88
    },
    "market": {
      "bullish": 0.80,
      "bearish": 0.15,
      "uncertainty": 0.25,
      "time_horizon": "medium"
    },
    "urgency": 0.65,
    "themes": ["product-launch", "revenue-growth", "market-expansion"],
    "geopolitical": {
      "stability_score": 0.0,
      "economic_impact": 0.3,
      "security_relevance": 0.0,
      "diplomatic_impact": {"global": 0.2, "western": 0.1, "regional": 0.4},
      "escalation_potential": 0.0,
      "regions_affected": ["US", "CN"],
      "impact_beneficiaries": ["US"],
      "impact_affected": ["CN"],
      "time_horizon": "medium_term",
      "confidence": 0.75,
      "alliance_activation": [],
      "conflict_type": "economic"
    }
  },
  "impact": {
    "overall": 0.72,
    "volatility": 0.45
  },
  "model_tag": "gpt-4.1-nano"
}
```

**Note:** The `geopolitical` object is **always present** in sentiment_json, even for non-geopolitical news (all fields set to 0/empty).

### Database Columns

| Column | Type | Description |
|--------|------|-------------|
| `sentiment_json` | `jsonb` | Full sentiment analysis data |
| `sentiment_label` | `varchar(20)` | Cached label (positive/neutral/negative) |
| `sentiment_score` | `numeric(3,2)` | Cached score (-1.0 to +1.0) |
| `impact_json` | `jsonb` | Full impact analysis data |
| `impact_score` | `numeric(3,2)` | Cached overall impact (0.0 to 1.0) |

---

## Best Practices

### 1. Combine Multiple Indicators
Don't rely on sentiment score alone - consider:
- **Sentiment + Impact**: High impact negative news requires attention
- **Sentiment + Urgency**: Urgent positive news may indicate opportunities
- **Sentiment + Confidence**: Low confidence scores need manual review

### 2. Context Matters
- **Industry-specific**: Tech product launches are often positive, but not always
- **Market conditions**: Neutral news during crises may be relatively positive
- **Time sensitivity**: Check `time_horizon` for actionable timeframe

### 3. Monitor Trends
- Track sentiment changes over time for specific feeds
- Compare sentiment across different sources for the same topic
- Use aggregate sentiment to gauge overall market mood

### 4. Set Thresholds
Configure alerts based on your needs:
```python
# High-priority alerts
if impact_score >= 0.8 and urgency >= 0.7:
    send_alert("Critical news detected")

# Portfolio monitoring
if sentiment_score <= -0.5 and feed_id in portfolio_feeds:
    notify_portfolio_manager()

# Opportunity detection
if sentiment_score >= 0.6 and bullish >= 0.7:
    flag_as_opportunity()
```

---

## API Endpoints

### Get Item Analysis
```bash
GET /api/items/{item_id}/analysis
```

**Response:**
```json
{
  "item_id": 12345,
  "analysis": { ... },
  "created_at": "2025-01-15T10:30:00Z"
}
```

### Aggregate Sentiment Statistics
```bash
GET /api/statistics/sentiment
```

**Response:**
```json
{
  "total_analyses": 5000,
  "by_sentiment": {
    "positive": 2100,
    "neutral": 1800,
    "negative": 1100
  },
  "average_impact": 0.58,
  "average_urgency": 0.42
}
```

---

## Troubleshooting

### No Sentiment Data

**Issue:** Articles show "No Analysis" badge

**Causes:**
- Analysis not yet run (check auto-analysis status)
- Analysis failed (check error logs)
- Feed excluded from analysis (check feed settings)

**Solution:**
```bash
# Trigger manual analysis
POST /api/v1/analysis/runs
{
  "feed_id": 123,
  "scope_limit": 10
}

# Check auto-analysis status
GET /admin/auto-analysis
```

### Unexpected Sentiment Scores

**Issue:** Sentiment seems incorrect or inconsistent

**Possible Reasons:**
1. **Low confidence score**: Check `confidence` value
2. **Model limitations**: GPT-4.1-nano may miss nuance
3. **Ambiguous content**: Mixed signals in article
4. **Language/context**: Sarcasm or complex language

**Solutions:**
- Filter by confidence threshold (`>= 0.7`)
- Re-run with different model (if available)
- Manually review flagged articles
- Adjust prompt templates for your use case

### Performance Issues

**Issue:** Slow sentiment queries

**Solutions:**
```sql
-- Add indexes for common queries
CREATE INDEX idx_sentiment_score ON item_analyses(sentiment_score);
CREATE INDEX idx_impact_score ON item_analyses(impact_score);
CREATE INDEX idx_sentiment_label ON item_analyses(sentiment_label);

-- Use cached columns instead of JSON queries
SELECT * FROM items
JOIN item_analyses ON items.id = item_analyses.item_id
WHERE sentiment_score >= 0.7  -- Fast (indexed)
-- NOT: WHERE sentiment_json->'overall'->>'score' >= 0.7  -- Slow
```

---

## Model Information

**Current Model:** `gpt-4.1-nano`
- Optimized for cost-efficiency
- Fast processing (< 2s average)
- Good accuracy for financial/tech news
- May struggle with sarcasm or highly technical content

**Upgrade Options:**
- Switch to `gpt-4o` for better nuance detection (higher cost)
- Configure in `/admin/analysis` under Model Selection

---

## Related Documentation

- [API Documentation](API_DOCUMENTATION.md) - Full API reference
- [Database Schema](DATABASE_SCHEMA.md) - Database structure
- [Auto-Analysis Guide](AUTO_ANALYSIS_GUIDE.md) - Automated processing
- [Architecture](ARCHITECTURE.md) - System design

---

## Support

For issues or questions:
- Check [GitHub Issues](https://github.com/yourusername/news-mcp/issues)
- Review [API Examples](API_EXAMPLES.md)
- See [Troubleshooting Guide](README.md#troubleshooting)
