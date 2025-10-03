"""
MCP Server Schema Registry
Centralized JSON schemas for all data structures with versioning
"""

from typing import Dict, Any

# Version of schema registry
SCHEMA_VERSION = "1.0.0"

# Basic Item Schema
ITEM_BASIC_SCHEMA = {
    "type": "object",
    "title": "News Item (Basic)",
    "description": "Basic news article/item without analysis data",
    "properties": {
        "id": {
            "type": "integer",
            "description": "Unique item identifier"
        },
        "title": {
            "type": "string",
            "description": "Article headline/title"
        },
        "description": {
            "type": ["string", "null"],
            "description": "Article summary/excerpt (may contain HTML)"
        },
        "link": {
            "type": "string",
            "format": "uri",
            "description": "URL to full article"
        },
        "published": {
            "type": ["string", "null"],
            "format": "date-time",
            "description": "Publication timestamp (ISO 8601)"
        },
        "feed_id": {
            "type": "integer",
            "description": "Source feed identifier"
        }
    },
    "required": ["id", "title", "link", "feed_id"]
}

# Overall Sentiment Schema
SENTIMENT_SCHEMA = {
    "type": "object",
    "title": "Overall Sentiment Analysis",
    "description": "General sentiment classification and score",
    "properties": {
        "label": {
            "type": "string",
            "enum": ["positive", "negative", "neutral"],
            "description": "Sentiment classification"
        },
        "score": {
            "type": "number",
            "minimum": -1.0,
            "maximum": 1.0,
            "description": "Sentiment polarity: -1.0 (very negative) to +1.0 (very positive)"
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Model confidence in classification (0.0-1.0)"
        }
    },
    "required": ["label", "score", "confidence"]
}

# Geopolitical Sentiment Schema
GEOPOLITICAL_SCHEMA = {
    "type": "object",
    "title": "Geopolitical Sentiment Analysis",
    "description": "Geopolitical impact and risk assessment",
    "properties": {
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Model confidence in geopolitical assessment (0.0-1.0)"
        },
        "time_horizon": {
            "type": "string",
            "enum": ["immediate", "short_term", "medium_term", "long_term"],
            "description": "Expected timeframe of impact (immediate: <1 week, short: 1-4 weeks, medium: 1-6 months, long: >6 months)"
        },
        "conflict_type": {
            "type": "string",
            "enum": ["interstate_war", "civil_war", "diplomatic", "economic", "cyber", "terrorism", "humanitarian"],
            "description": "Primary type of geopolitical conflict or event"
        },
        "economic_impact": {
            "type": "number",
            "minimum": -1.0,
            "maximum": 1.0,
            "description": "Economic impact score: -1.0 (severe negative) to +1.0 (strong positive)"
        },
        "stability_score": {
            "type": "number",
            "minimum": -1.0,
            "maximum": 1.0,
            "description": "Political stability impact: -1.0 (highly destabilizing) to +1.0 (stabilizing). Values < -0.5 indicate significant destabilization risk."
        },
        "escalation_potential": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Risk of conflict escalation: 0.0 (no risk) to 1.0 (high risk of escalation). Values > 0.7 indicate significant escalation risk."
        },
        "security_relevance": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "National/international security relevance: 0.0 (low) to 1.0 (critical security issue)"
        },
        "regions_affected": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["Middle_East", "Eastern_Europe", "Western_Europe", "North_America", "South_America",
                        "East_Asia", "South_Asia", "Southeast_Asia", "Africa", "Oceania", "Global"]
            },
            "description": "Geographic regions primarily affected by the event"
        },
        "impact_affected": {
            "type": "array",
            "items": {"type": "string"},
            "description": "ISO 3166-1 alpha-2 country codes of negatively affected countries (e.g., ['US', 'IL', 'UA'])"
        },
        "impact_beneficiaries": {
            "type": "array",
            "items": {"type": "string"},
            "description": "ISO 3166-1 alpha-2 country codes of benefiting countries (e.g., ['CN', 'RU'])"
        },
        "alliance_activation": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["NATO", "EU", "BRICS", "Arab_League", "ASEAN", "AU", "CSTO", "SCO", "G7", "G20"]
            },
            "description": "International alliances likely to be activated or involved"
        },
        "diplomatic_impact": {
            "type": "object",
            "description": "Diplomatic relations impact by region/sphere",
            "properties": {
                "western": {
                    "type": "number",
                    "minimum": -1.0,
                    "maximum": 1.0,
                    "description": "Impact on Western (US/EU/NATO) diplomatic relations"
                },
                "regional": {
                    "type": "number",
                    "minimum": -1.0,
                    "maximum": 1.0,
                    "description": "Impact on regional diplomatic relations"
                },
                "global_impact": {
                    "type": "number",
                    "minimum": -1.0,
                    "maximum": 1.0,
                    "description": "Overall global diplomatic impact"
                }
            }
        }
    },
    "required": ["confidence", "time_horizon", "conflict_type", "stability_score", "regions_affected"]
}

# Full Analysis Schema (combines sentiment + geopolitical)
ANALYSIS_SCHEMA = {
    "type": "object",
    "title": "Full Analysis Data",
    "description": "Complete analysis including sentiment, impact, urgency, and optional geopolitical assessment",
    "properties": {
        "sentiment": {
            "$ref": "#/definitions/sentiment",
            "description": "Overall sentiment analysis"
        },
        "impact": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Overall impact score: 0.0 (minimal) to 1.0 (critical impact)"
        },
        "urgency": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Urgency score: 0.0 (not urgent) to 1.0 (immediate action required)"
        },
        "model": {
            "type": "string",
            "description": "AI model used for analysis (e.g., 'gpt-4.1-nano')"
        },
        "analyzed_at": {
            "type": "string",
            "format": "date-time",
            "description": "Timestamp when analysis was performed (ISO 8601)"
        },
        "geopolitical": {
            "$ref": "#/definitions/geopolitical",
            "description": "Geopolitical analysis (only present if include_geopolitical=true)"
        }
    },
    "required": ["sentiment", "impact", "urgency", "model", "analyzed_at"],
    "definitions": {
        "sentiment": SENTIMENT_SCHEMA,
        "geopolitical": GEOPOLITICAL_SCHEMA
    }
}

# Item with Analysis Schema
ITEM_WITH_ANALYSIS_SCHEMA = {
    "type": "object",
    "title": "News Item with Analysis",
    "description": "News item including full sentiment and geopolitical analysis",
    "allOf": [
        ITEM_BASIC_SCHEMA,
        {
            "properties": {
                "analysis": ANALYSIS_SCHEMA
            }
        }
    ]
}

# Example Data
EXAMPLE_ITEM_BASIC = {
    "id": 19043,
    "title": "Gaza aid flotilla: more than a dozen vessels intercepted by Israeli forces",
    "description": "Israeli foreign ministry posts video; vessels carrying about 500 activists intercepted...",
    "link": "https://www.theguardian.com/world/live/2025/oct/01/israel-gaza-aid-global-sumud-flotilla",
    "published": "2025-10-02T04:13:18",
    "feed_id": 26
}

EXAMPLE_ITEM_WITH_ANALYSIS = {
    **EXAMPLE_ITEM_BASIC,
    "analysis": {
        "sentiment": {
            "label": "negative",
            "score": -0.7,
            "confidence": 0.9
        },
        "impact": 0.7,
        "urgency": 0.9,
        "model": "gpt-4.1-nano",
        "analyzed_at": "2025-10-02T04:40:24.160707+00:00",
        "geopolitical": {
            "confidence": 0.9,
            "time_horizon": "immediate",
            "conflict_type": "diplomatic",
            "economic_impact": -0.6,
            "stability_score": -0.8,
            "escalation_potential": 0.8,
            "security_relevance": 0.9,
            "regions_affected": ["Middle_East"],
            "impact_affected": ["IL", "PS"],
            "impact_beneficiaries": ["IL", "PS"],
            "alliance_activation": [],
            "diplomatic_impact": {
                "western": -0.7,
                "regional": -0.9,
                "global_impact": -0.8
            }
        }
    }
}

# Usage Guide
USAGE_GUIDE = """
# News-MCP API Usage Guide

## Quick Start

### 1. Get Recent Items (Basic)
```python
items_recent(limit=10)
```
Returns: Basic item data (id, title, link, published)

### 2. Get Recent Items with Sentiment Analysis
```python
items_recent(limit=10, include_analysis=True)
```
Returns: Items + sentiment (label, score), impact, urgency

### 3. Get Recent Items with Full Geopolitical Analysis
```python
items_recent(limit=10, include_analysis=True, include_geopolitical=True)
```
Returns: Items + sentiment + geopolitical (regions, stability, escalation, diplomatic impact)

## Field Interpretation Guide

### Sentiment Scores
- **sentiment.score**: -1.0 to +1.0
  - Below -0.5: Strong negative sentiment
  - -0.5 to -0.2: Moderately negative
  - -0.2 to +0.2: Neutral
  - +0.2 to +0.5: Moderately positive
  - Above +0.5: Strong positive sentiment

### Impact & Urgency
- **impact**: 0.0 to 1.0 (overall importance/significance)
  - 0.0-0.3: Low impact (routine news)
  - 0.3-0.6: Medium impact (notable events)
  - 0.6-1.0: High impact (major events)

- **urgency**: 0.0 to 1.0 (time sensitivity)
  - 0.0-0.3: Not time-sensitive
  - 0.3-0.6: Moderately urgent
  - 0.6-1.0: Highly urgent/breaking news

### Geopolitical Metrics
- **stability_score**: -1.0 to +1.0
  - Below -0.7: Severe destabilization
  - -0.7 to -0.3: Moderate destabilization
  - -0.3 to +0.3: Stable situation
  - Above +0.3: Stabilizing effect

- **escalation_potential**: 0.0 to 1.0
  - 0.0-0.3: Low escalation risk
  - 0.3-0.7: Moderate escalation risk
  - 0.7-1.0: High escalation risk

- **security_relevance**: 0.0 to 1.0
  - 0.0-0.3: Low security concern
  - 0.3-0.7: Moderate security concern
  - 0.7-1.0: Critical security issue

## Best Practices

1. **Always request analysis data when you need sentiment/geopolitical context**
   - Use `include_analysis=True` for sentiment scores
   - Use `include_geopolitical=True` for geopolitical events

2. **Filter by feed for specific sources**
   - Use `feed_id=26` for The Guardian, `feed_id=33` for Bloomberg, etc.

3. **Use time filtering for recent events**
   - Use `since="2025-10-01T00:00:00Z"` for items since a specific date

4. **Combine filters for precise queries**
   ```python
   items_search(
       q="Ukraine",
       include_analysis=True,
       include_geopolitical=True,
       time_range={"from": "2025-10-01T00:00:00Z"}
   )
   ```

## Country Codes Reference
- US = United States
- IL = Israel
- PS = Palestine
- UA = Ukraine
- RU = Russia
- CN = China
- EU = European Union (collective)

## Alliance Codes
- NATO = North Atlantic Treaty Organization
- EU = European Union
- BRICS = Brazil, Russia, India, China, South Africa
- G7 = Group of Seven (major advanced economies)
- G20 = Group of Twenty (major economies)
"""

# Schema registry for easy access
SCHEMAS: Dict[str, Any] = {
    "item_basic": ITEM_BASIC_SCHEMA,
    "item_with_analysis": ITEM_WITH_ANALYSIS_SCHEMA,
    "sentiment": SENTIMENT_SCHEMA,
    "geopolitical": GEOPOLITICAL_SCHEMA,
    "analysis": ANALYSIS_SCHEMA
}

# Examples registry
EXAMPLES: Dict[str, Any] = {
    "item_basic": EXAMPLE_ITEM_BASIC,
    "item_with_analysis": EXAMPLE_ITEM_WITH_ANALYSIS
}
