-- Migration: Create item_analysis table for LLM-based analysis
-- Description: Adds sentiment and impact analysis storage for news items

CREATE TABLE IF NOT EXISTS item_analysis (
  item_id         BIGINT PRIMARY KEY REFERENCES items(id) ON DELETE CASCADE,
  sentiment_json  JSONB NOT NULL DEFAULT '{}'::jsonb,
  impact_json     JSONB NOT NULL DEFAULT '{}'::jsonb,
  model_tag       TEXT,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_item_analysis_updated ON item_analysis(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_item_analysis_sentiment_label ON item_analysis((sentiment_json->'overall'->>'label'));
CREATE INDEX IF NOT EXISTS idx_item_analysis_impact_overall ON item_analysis(((impact_json->>'overall')::numeric));
CREATE INDEX IF NOT EXISTS idx_item_analysis_urgency ON item_analysis(((sentiment_json->>'urgency')::numeric));

-- Comment for documentation
COMMENT ON TABLE item_analysis IS 'Stores LLM-generated sentiment and impact analysis for news items';
COMMENT ON COLUMN item_analysis.sentiment_json IS 'JSON containing overall sentiment, urgency, and themes';
COMMENT ON COLUMN item_analysis.impact_json IS 'JSON containing impact score and volatility metrics';
COMMENT ON COLUMN item_analysis.model_tag IS 'LLM model identifier used for analysis';