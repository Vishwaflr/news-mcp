# Geopolitical Analysis Extension - Implementation Plan

**Status:** Planning Phase
**Date:** 2025-10-01
**Objective:** Extend existing sentiment analysis with geopolitical dimensions

---

## 📊 Current State Analysis

### Existing Analysis Schema

**Location:** `app/domain/analysis/schema.py`

```python
# Current Structure
AnalysisResult:
  - sentiment: SentimentPayload
    - overall: Overall (label, score, confidence)
    - market: Market (bullish, bearish, uncertainty, time_horizon)
    - urgency: float (0.0-1.0)
    - themes: List[str] (max 6)
  - impact: ImpactPayload
    - overall: float (0.0-1.0)
    - volatility: float (0.0-1.0)
  - model_tag: str
```

**Database Schema:** `item_analysis` table

| Column | Type | Current Use |
|--------|------|-------------|
| `item_id` | bigint | Primary key, FK to items.id |
| `sentiment_json` | jsonb | Stores full SentimentPayload |
| `impact_json` | jsonb | Stores full ImpactPayload |
| `model_tag` | text | Model identifier (e.g., "gpt-4.1-nano") |
| `updated_at` | timestamp | Last update time |

**Key Insight:** Uses JSONB columns - **no schema migration needed for new fields!**

### Current Data Flow

```
1. Worker (analysis_worker.py)
   ↓
2. AnalysisOrchestrator (analysis_orchestrator.py)
   ↓
3. LLMClient.classify() (llm_client.py)
   ↓ OpenAI API Call
4. JSON Response Validation (_validate_and_normalize_result)
   ↓
5. Storage in sentiment_json/impact_json (JSONB)
   ↓
6. Cached values in item_analyses view (sentiment_score, impact_score, etc.)
```

**Key Insight:** Single OpenAI call per item, response stored as flexible JSON.

---

## 🎯 Proposed Extension Schema

### New Geopolitical Fields

```json
{
  // === EXISTING (unchanged) ===
  "sentiment": {
    "overall": {"label": "positive", "score": 0.7, "confidence": 0.85},
    "market": {"bullish": 0.6, "bearish": 0.2, "uncertainty": 0.3, "time_horizon": "medium"},
    "urgency": 0.65,
    "themes": ["product-launch", "revenue"]
  },
  "impact": {
    "overall": 0.72,
    "volatility": 0.45
  },

  // === NEW GEOPOLITICAL EXTENSION ===
  "geopolitical": {
    "stability_score": -0.6,           // Regional/Global stability (-1 to +1)
    "economic_impact": -0.5,           // Economic consequences (-1 to +1)
    "security_relevance": 0.8,         // Security relevance (0 to 1)

    "diplomatic_impact": {
      "global": -0.3,                  // Global diplomatic impact (-1 to +1)
      "western": -0.6,                 // EU/NATO/Germany perspective (-1 to +1)
      "regional": -0.8                 // Regional impact (-1 to +1)
    },

    "impact_beneficiaries": ["UA", "EU", "NATO"],          // Max 3, ISO 3166 + Blocs
    "impact_affected": ["RU", "Energy_Markets"],           // Max 3, ISO 3166 + Blocs

    "regions_affected": ["Eastern_Europe", "EU"],          // Geographic regions
    "time_horizon": "immediate",                           // immediate/short_term/long_term
    "confidence": 0.85,                                    // Analysis confidence (0-1)
    "escalation_potential": 0.6,                          // Escalation risk (0-1)
    "alliance_activation": ["NATO Article 5"],            // Activated alliances/treaties
    "conflict_type": "economic_warfare"                    // diplomatic/economic/hybrid/interstate_war/nuclear_threat
  },

  "model_tag": "gpt-4.1-nano"
}
```

### Entity Standardization Rules

**Countries:** ISO 3166-1 Alpha-2 codes (US, DE, FR, CN, RU, UA, etc.)
**Blocs:** EU, NATO, ASEAN, BRICS, G7, UN, OPEC
**Regions:** Middle_East, Eastern_Europe, Asia_Pacific, Latin_America, Sub_Saharan_Africa
**Markets:** Energy_Markets, Financial_Markets, Global_Trade, Commodity_Markets
**Max Entries:** 3 per `impact_beneficiaries`/`impact_affected`

---

## 🔧 Implementation Impact Analysis

### 1. Database Schema Changes

**Status:** ✅ **NO MIGRATION NEEDED**

**Reason:**
- Current `sentiment_json` and `impact_json` are JSONB columns
- JSONB is schema-less - can store arbitrary nested structures
- New `geopolitical` object can be added to existing JSON structure

**Storage Options:**

#### Option A: Extend `sentiment_json` (Recommended)
```json
// sentiment_json column
{
  "overall": {...},
  "market": {...},
  "urgency": 0.65,
  "themes": [...],
  "geopolitical": {  // NEW: Added here
    "stability_score": -0.6,
    ...
  }
}
```

**Pros:**
- No schema migration required
- Backward compatible (old analyses don't have geopolitical field)
- All sentiment-related data in one place

**Cons:**
- Slight naming confusion (sentiment_json contains geopolitical data)

#### Option B: New `geopolitical_json` column
```sql
ALTER TABLE item_analysis
ADD COLUMN geopolitical_json jsonb DEFAULT '{}'::jsonb;
```

**Pros:**
- Clear separation of concerns
- Easier to query geopolitical data specifically

**Cons:**
- Requires database migration
- More columns to manage

**Recommendation:** **Option A** - No migration, faster deployment

---

### 2. OpenAI Prompt Extension

**Current Prompt Location:** `app/services/llm_client.py:_build_prompt()`

**Current Prompt Structure:**
```
You are a precise financial news classifier. Return STRICT JSON only.

Title: {title}
Summary: {summary}

Return this exact JSON structure:
{
  "overall": {...},
  "market": {...},
  "urgency": ...,
  "impact": {...},
  "themes": [...]
}
```

**Required Changes:**

1. **Extend JSON schema in prompt:**
```
Return this exact JSON structure:
{
  "overall": {...},
  "market": {...},
  "urgency": ...,
  "impact": {...},
  "themes": [...],

  "geopolitical": {
    "stability_score": -1.0 to 1.0,
    "economic_impact": -1.0 to 1.0,
    "security_relevance": 0.0 to 1.0,
    "diplomatic_impact": {
      "global": -1.0 to 1.0,
      "western": -1.0 to 1.0,
      "regional": -1.0 to 1.0
    },
    "impact_beneficiaries": ["ISO3166|Bloc", "ISO3166|Bloc", "ISO3166|Bloc"],
    "impact_affected": ["ISO3166|Bloc", "ISO3166|Bloc", "ISO3166|Bloc"],
    "regions_affected": ["Region1", "Region2"],
    "time_horizon": "immediate|short_term|long_term",
    "confidence": 0.0 to 1.0,
    "escalation_potential": 0.0 to 1.0,
    "alliance_activation": ["Alliance/Treaty"],
    "conflict_type": "diplomatic|economic|hybrid|interstate_war|nuclear_threat"
  }
}
```

2. **Add entity standardization instructions:**
```
Entity Standards:
- Countries: Use ISO 3166-1 Alpha-2 codes (US, DE, FR, CN, RU, UA, etc.)
- Blocs: EU, NATO, ASEAN, BRICS, G7, UN, OPEC
- Regions: Middle_East, Eastern_Europe, Asia_Pacific, Latin_America, Sub_Saharan_Africa
- Markets: Energy_Markets, Financial_Markets, Global_Trade, Commodity_Markets
- Max 3 entries for impact_beneficiaries and impact_affected
- If news is not geopolitically relevant, set all geopolitical scores to 0.0 and arrays to []
```

**Impact:**
- **Token increase:** ~200 tokens (prompt) + ~150 tokens (response)
- **Cost impact:** Minimal (~$0.0001 per analysis increase with gpt-4.1-nano)
- **API calls:** Same (1 call per item)
- **Response time:** +0.5-1.0 seconds (more JSON to generate)

---

### 3. Validation & Normalization

**Current Location:** `app/services/llm_client.py:_validate_and_normalize_result()`

**Required Changes:**

Add validation for new `geopolitical` object:

```python
# Pseudo-code structure
def _validate_and_normalize_result(self, result: Dict) -> Dict:
    # ... existing validation ...

    # NEW: Validate geopolitical fields
    geopolitical = result.get("geopolitical", {})

    # Validate scores (-1 to +1 or 0 to 1)
    geopolitical["stability_score"] = clamp(geopolitical.get("stability_score", 0.0), -1.0, 1.0)
    geopolitical["economic_impact"] = clamp(geopolitical.get("economic_impact", 0.0), -1.0, 1.0)
    geopolitical["security_relevance"] = clamp(geopolitical.get("security_relevance", 0.0), 0.0, 1.0)

    # Validate diplomatic_impact sub-object
    diplomatic = geopolitical.get("diplomatic_impact", {})
    diplomatic["global"] = clamp(diplomatic.get("global", 0.0), -1.0, 1.0)
    diplomatic["western"] = clamp(diplomatic.get("western", 0.0), -1.0, 1.0)
    diplomatic["regional"] = clamp(diplomatic.get("regional", 0.0), -1.0, 1.0)

    # Validate arrays (max 3 items)
    geopolitical["impact_beneficiaries"] = validate_entities(
        geopolitical.get("impact_beneficiaries", []), max_items=3
    )
    geopolitical["impact_affected"] = validate_entities(
        geopolitical.get("impact_affected", []), max_items=3
    )

    # Validate enums
    geopolitical["time_horizon"] = validate_enum(
        geopolitical.get("time_horizon", "short_term"),
        allowed=["immediate", "short_term", "long_term"]
    )
    geopolitical["conflict_type"] = validate_enum(
        geopolitical.get("conflict_type", "diplomatic"),
        allowed=["diplomatic", "economic", "hybrid", "interstate_war", "nuclear_threat"]
    )

    # Validate confidence & escalation (0 to 1)
    geopolitical["confidence"] = clamp(geopolitical.get("confidence", 0.0), 0.0, 1.0)
    geopolitical["escalation_potential"] = clamp(geopolitical.get("escalation_potential", 0.0), 0.0, 1.0)

    # Validate alliance_activation array
    geopolitical["alliance_activation"] = geopolitical.get("alliance_activation", [])

    return {
        ...existing_fields...,
        "geopolitical": geopolitical
    }
```

**Complexity:** Medium (20-30 lines of validation code)

---

### 4. Pydantic Schema Extension

**Current Location:** `app/domain/analysis/schema.py`

**Required Changes:**

```python
# NEW: Geopolitical enums
ConflictType = Literal["diplomatic", "economic", "hybrid", "interstate_war", "nuclear_threat"]
GeoTimeHorizon = Literal["immediate", "short_term", "long_term"]

# NEW: Diplomatic impact sub-model
class DiplomaticImpact(BaseModel):
    global_impact: float = Field(..., ge=-1.0, le=1.0, alias="global")
    western: float = Field(..., ge=-1.0, le=1.0)
    regional: float = Field(..., ge=-1.0, le=1.0)

# NEW: Geopolitical analysis model
class GeopoliticalPayload(BaseModel):
    stability_score: float = Field(..., ge=-1.0, le=1.0)
    economic_impact: float = Field(..., ge=-1.0, le=1.0)
    security_relevance: float = Field(..., ge=0.0, le=1.0)

    diplomatic_impact: DiplomaticImpact

    impact_beneficiaries: List[str] = Field(default_factory=list, max_items=3)
    impact_affected: List[str] = Field(default_factory=list, max_items=3)

    regions_affected: List[str] = Field(default_factory=list)
    time_horizon: GeoTimeHorizon
    confidence: float = Field(..., ge=0.0, le=1.0)
    escalation_potential: float = Field(..., ge=0.0, le=1.0)
    alliance_activation: List[str] = Field(default_factory=list)
    conflict_type: ConflictType

    @validator('impact_beneficiaries', 'impact_affected')
    def validate_entities(cls, v):
        # Validate max 3 items
        if len(v) > 3:
            v = v[:3]
        return v

# UPDATED: Extend AnalysisResult
class AnalysisResult(BaseModel):
    sentiment: SentimentPayload
    impact: ImpactPayload
    geopolitical: Optional[GeopoliticalPayload] = None  # Optional for backward compatibility
    model_tag: str
```

**Backward Compatibility:** `geopolitical` is Optional - old analyses without this field still validate.

---

### 5. Worker Logic

**Current Location:** `app/worker/analysis_worker.py`, `app/services/analysis_orchestrator.py`

**Required Changes:** ✅ **NONE (if using Option A)**

**Reason:**
- Worker retrieves LLM response as JSON dict
- Stores entire dict in `sentiment_json` JSONB column
- JSONB automatically handles nested `geopolitical` object
- No code changes needed for storage

**Optional Enhancement:**
- Add logging to track geopolitical analysis quality
- Add metrics for geopolitical fields (Prometheus)

---

### 6. MCP Tools Impact

**Affected Tools:** (Based on sentiment/analysis filters)

| Tool | Current Filters | New Filters Needed |
|------|----------------|-------------------|
| `latest_articles` | sentiment, impact_min, urgency_min | stability_min, security_min, escalation_min |
| `analysis_preview` | None (displays all fields) | Display geopolitical fields |
| `search_articles` | sentiment, impact | Add geopolitical search params |
| `get_article_details` | Shows sentiment/impact | Show geopolitical data |

**Changes Required:**

1. **Schema Extension:**
   - Update MCP tool schemas to include geopolitical parameters
   - Add entity filtering (e.g., `filter by country: "UA"`)

2. **Query Filters:**
   - Add JSONB queries for geopolitical fields:
   ```sql
   WHERE (sentiment_json->'geopolitical'->>'stability_score')::float <= -0.5
   WHERE sentiment_json->'geopolitical'->'impact_affected' ? 'RU'
   ```

3. **Response Formatting:**
   - Include geopolitical fields in MCP tool responses
   - Format entities for readability (e.g., "UA, EU, NATO")

**Complexity:** Medium (10-15 tools to update)

---

### 7. Dashboard Integration

**Affected Dashboards:**

| Dashboard | Current Display | New Display Needed |
|-----------|----------------|-------------------|
| `/admin/items` | Sentiment badges (🟢🔴⚪) | Geopolitical badges (stability, security) |
| `/admin/manager` | Aggregate sentiment stats | Aggregate geopolitical trends |
| `/admin/statistics` | Sentiment distribution | Geopolitical hotspots map |
| `/admin/analysis` | Analysis preview | Show geopolitical fields |

**Required Changes:**

1. **Item List Views:**
   - Add geopolitical score badges:
     - Stability: 🛡️ (color-coded: green/yellow/red)
     - Security: ⚠️ (0.0-1.0)
     - Escalation: 🔥 (0.0-1.0)

2. **Detail Views:**
   - Display full geopolitical analysis
   - Show affected countries/regions as tags
   - Visualize diplomatic impact (global/western/regional)

3. **Filters:**
   - Add geopolitical filter dropdowns:
     - Stability range slider
     - Security relevance slider
     - Affected countries multi-select
     - Conflict type dropdown

4. **Aggregations:**
   - Geopolitical trends over time
   - Top affected countries/regions
   - Conflict type distribution

**Complexity:** High (20+ template files to modify)

---

## 📋 Backward Compatibility Plan

### Critical Requirements

1. **Old Analyses Must Work:**
   - Existing analyses don't have `geopolitical` field
   - System must handle `geopolitical: null` gracefully
   - UI must not break when field is missing

2. **Gradual Rollout:**
   - Option 1: Analyze all new items with geopolitical extension
   - Option 2: Phased rollout (10% → 50% → 100%)
   - Option 3: Opt-in per feed (add `enable_geopolitical` flag to feeds table)

3. **Data Migration:**
   - **Not required** (new field is additive)
   - Old analyses remain valid without geopolitical data
   - New analyses include geopolitical data

### Compatibility Layers

**Schema Validation:**
```python
# OLD analyses (no geopolitical field)
{
  "sentiment": {...},
  "impact": {...}
}
# → Valid (geopolitical is Optional[GeopoliticalPayload])

# NEW analyses (with geopolitical)
{
  "sentiment": {...},
  "impact": {...},
  "geopolitical": {...}
}
# → Valid
```

**UI Rendering:**
```python
# Template pseudo-code
{% if analysis.geopolitical %}
  <div class="geopolitical-section">
    Stability: {{ analysis.geopolitical.stability_score }}
  </div>
{% else %}
  <span class="badge bg-secondary">No Geopolitical Data</span>
{% endif %}
```

**API Responses:**
```json
// Old analysis (backward compatible)
{
  "sentiment_score": 0.7,
  "impact_score": 0.8,
  "geopolitical": null  // Missing field = null
}

// New analysis
{
  "sentiment_score": 0.7,
  "impact_score": 0.8,
  "geopolitical": {
    "stability_score": -0.6,
    ...
  }
}
```

---

## 🚀 Implementation Phases

### Phase 1: Schema & Validation (Week 1)
**Goal:** Extend Pydantic schemas and LLM validation logic

**Tasks:**
1. ✅ Create `GeopoliticalPayload` Pydantic model
2. ✅ Update `AnalysisResult` schema (add optional `geopolitical` field)
3. ✅ Extend `_validate_and_normalize_result()` in llm_client.py
4. ✅ Add entity validation helper functions
5. ✅ Write unit tests for geopolitical validation

**Deliverables:**
- Updated `app/domain/analysis/schema.py`
- Updated `app/services/llm_client.py`
- New `tests/unit/test_geopolitical_validation.py`

**Risk:** Low (schema changes only, no runtime impact)

---

### Phase 2: OpenAI Prompt Extension (Week 1-2)
**Goal:** Extend LLM prompt to request geopolitical analysis

**Tasks:**
1. ✅ Update `_build_prompt()` with geopolitical schema
2. ✅ Add entity standardization instructions
3. ✅ Test prompt with OpenAI Playground (validate response structure)
4. ✅ A/B test: old prompt vs. new prompt (10 sample articles)
5. ✅ Measure token/cost increase

**Deliverables:**
- Updated prompt in `app/services/llm_client.py`
- Prompt testing documentation
- Cost impact analysis (before/after)

**Risk:** Medium (LLM may not follow instructions correctly - needs validation)

---

### Phase 3: Storage & Retrieval (Week 2)
**Goal:** Store geopolitical data in database and retrieve correctly

**Tasks:**
1. ✅ Verify JSONB storage works (test write/read cycle)
2. ✅ Add database indexes for common geopolitical queries:
   ```sql
   CREATE INDEX idx_geopolitical_stability
   ON item_analysis ((sentiment_json->'geopolitical'->>'stability_score'));

   CREATE INDEX idx_geopolitical_security
   ON item_analysis ((sentiment_json->'geopolitical'->>'security_relevance'));
   ```
3. ✅ Update repository queries to include geopolitical fields
4. ✅ Test backward compatibility (old analyses load correctly)

**Deliverables:**
- Database migration (indexes only)
- Updated `app/repositories/analysis.py`
- Integration tests

**Risk:** Low (JSONB is schema-less, backward compatible)

---

### Phase 4: API & MCP Tool Updates (Week 3)
**Goal:** Expose geopolitical data via API and MCP tools

**Tasks:**
1. ✅ Update item API responses to include geopolitical fields
2. ✅ Add geopolitical filter parameters to `/api/items/`
3. ✅ Update MCP tool schemas (add geopolitical params)
4. ✅ Update MCP tool implementations (query & format geopolitical data)
5. ✅ Test MCP tools in Claude Desktop

**Deliverables:**
- Updated `app/api/items.py`
- Updated MCP tool definitions
- MCP integration tests

**Risk:** Medium (MCP tool schema changes may break client integrations)

---

### Phase 5: Dashboard Integration (Week 4)
**Goal:** Display geopolitical data in web dashboards

**Tasks:**
1. ✅ Add geopolitical badges to item list views
2. ✅ Create geopolitical detail component (expandable card)
3. ✅ Add geopolitical filters to dashboards
4. ✅ Create geopolitical statistics dashboard (`/admin/geopolitical`)
5. ✅ Add country/region tag visualization

**Deliverables:**
- Updated templates (`templates/admin/*.html`)
- New geopolitical dashboard
- CSS for geopolitical badges

**Risk:** Low (UI-only changes, no backend impact)

---

### Phase 6: Documentation & Testing (Week 4-5)
**Goal:** Document new features and ensure quality

**Tasks:**
1. ✅ Update API documentation (add geopolitical endpoints)
2. ✅ Update sentiment guide (add geopolitical section)
3. ✅ Create geopolitical analysis guide (wiki)
4. ✅ Write E2E tests (Playwright)
5. ✅ Performance testing (query speed with geopolitical filters)

**Deliverables:**
- Updated `docs/SENTIMENT_GUIDE.md`
- New `docs/GEOPOLITICAL_GUIDE.md`
- E2E test suite
- Performance benchmarks

**Risk:** Low

---

## 📊 Cost & Performance Impact

### Token Usage Analysis

**Current Analysis:**
- Prompt: ~150 tokens
- Response: ~100 tokens
- Total: ~250 tokens/item
- Cost (gpt-4.1-nano): ~$0.0003/item

**With Geopolitical Extension:**
- Prompt: ~350 tokens (+200)
- Response: ~250 tokens (+150)
- Total: ~600 tokens/item (+340 tokens)
- Cost (gpt-4.1-nano): ~$0.0007/item (+$0.0004)

**Impact:**
- **Cost increase:** +133% per analysis
- **Absolute cost:** Still very low ($0.0007 ≈ $1 per 1,400 analyses)
- **Response time:** +0.5-1.0 seconds (more JSON to generate)

**Recommendation:** Acceptable cost increase for added value.

---

### Database Performance

**JSONB Query Performance:**
```sql
-- Fast (indexed)
SELECT * FROM item_analysis
WHERE (sentiment_json->'geopolitical'->>'stability_score')::float <= -0.5;

-- Slow (not indexed, requires full table scan)
SELECT * FROM item_analysis
WHERE sentiment_json->'geopolitical'->'impact_affected' ? 'RU';
```

**Mitigation:**
- Add GIN index for array containment queries:
  ```sql
  CREATE INDEX idx_geopolitical_affected_gin
  ON item_analysis USING GIN ((sentiment_json->'geopolitical'->'impact_affected'));
  ```

---

## ⚠️ Risk Assessment

### High Risks

1. **LLM Hallucination:**
   - **Risk:** LLM invents country codes or entities
   - **Mitigation:** Strict validation, whitelist of allowed entities
   - **Fallback:** Log invalid entities, set to empty array

2. **Prompt Complexity:**
   - **Risk:** LLM ignores complex instructions
   - **Mitigation:** A/B testing, gradual rollout, monitor validation failures
   - **Fallback:** Reduce prompt complexity if failure rate > 5%

### Medium Risks

3. **Query Performance:**
   - **Risk:** Complex JSONB queries slow down API
   - **Mitigation:** Add indexes, cache frequent queries
   - **Monitoring:** Track P95 response times

4. **MCP Tool Compatibility:**
   - **Risk:** Breaking changes to MCP tool schemas
   - **Mitigation:** Make geopolitical params optional, version MCP tools
   - **Testing:** Full MCP integration tests before deployment

### Low Risks

5. **Backward Compatibility:**
   - **Risk:** Old analyses break UI
   - **Mitigation:** `geopolitical` field is optional, extensive testing
   - **Coverage:** E2E tests with mixed old/new data

---

## ✅ Success Criteria

### Functional Requirements

1. ✅ All new analyses include geopolitical data
2. ✅ Old analyses continue to work (no errors)
3. ✅ API endpoints support geopolitical filters
4. ✅ MCP tools expose geopolitical parameters
5. ✅ Dashboards display geopolitical data

### Performance Requirements

6. ✅ Analysis cost increase < 200% ($0.0003 → max $0.0009)
7. ✅ Response time increase < 50% (2s → max 3s)
8. ✅ API query performance < 200ms (P95)
9. ✅ No database schema migrations (JSONB-only)

### Quality Requirements

10. ✅ LLM validation failure rate < 5%
11. ✅ Entity standardization compliance > 95%
12. ✅ E2E test coverage > 80%
13. ✅ Documentation complete (API docs, guides, wiki)

---

## 📚 Documentation Plan

### Required Documentation

1. **API Documentation:**
   - Update `docs/API_DOCUMENTATION.md`
   - Add geopolitical filter examples

2. **Sentiment Guide:**
   - Update `docs/SENTIMENT_GUIDE.md`
   - Add geopolitical section

3. **Geopolitical Analysis Guide:**
   - Create `docs/GEOPOLITICAL_GUIDE.md`
   - Explain scores, entities, use cases

4. **Wiki Update:**
   - Create `Feature-Geopolitical-Analysis.md` in wiki
   - Link from homepage

5. **Database Schema:**
   - Update `docs/DATABASE_SCHEMA.md`
   - Document JSONB structure

---

## 🎯 Next Steps

### Immediate Actions (This Week)

1. ✅ **Review this plan with team/stakeholders**
2. ✅ **Approve implementation approach (Option A vs. Option B)**
3. ✅ **Set up feature flag for gradual rollout:**
   ```python
   ENABLE_GEOPOLITICAL_ANALYSIS = os.getenv('ENABLE_GEOPOLITICAL_ANALYSIS', 'false')
   ```
4. ✅ **Create implementation branch:**
   ```bash
   git checkout -b feature/geopolitical-analysis
   ```

### Week 1 Goals

5. ✅ Implement Phase 1 (Schema & Validation)
6. ✅ Implement Phase 2 (OpenAI Prompt Extension)
7. ✅ Test prompt with 20 sample articles
8. ✅ Measure cost impact

### Week 2-5 Goals

- Complete Phases 3-6 according to plan
- Deploy to staging environment
- Run E2E tests
- Gather user feedback
- Deploy to production (gradual rollout)

---

## 📞 Questions for Stakeholders

1. **Rollout Strategy:**
   - Immediate 100% rollout or gradual (10% → 50% → 100%)?
   - Should geopolitical analysis be opt-in per feed?

2. **Cost Approval:**
   - Cost increase from $0.0003 to $0.0007 per analysis acceptable?
   - Current system: ~1,000 analyses/day = $0.30/day → $0.70/day (+$0.40/day)

3. **Priority:**
   - Which dashboards/MCP tools are highest priority for geopolitical integration?
   - Should we build `/admin/geopolitical` dashboard first or later?

4. **Entity Coverage:**
   - Is the provided entity list (countries, blocs, regions, markets) complete?
   - Any additional entities needed?

---

**Document Version:** 1.0
**Last Updated:** 2025-10-01
**Author:** Claude Code
**Status:** Awaiting Approval
