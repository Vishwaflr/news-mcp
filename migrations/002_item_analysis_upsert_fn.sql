-- Migration: Create upsert function for item_analysis
-- Description: Adds optimized upsert function for efficient analysis data management

CREATE OR REPLACE FUNCTION upsert_item_analysis(
  p_item_id BIGINT,
  p_sentiment JSONB,
  p_impact JSONB,
  p_model_tag TEXT
) RETURNS VOID AS $$
BEGIN
  INSERT INTO item_analysis (item_id, sentiment_json, impact_json, model_tag, updated_at)
  VALUES (p_item_id, p_sentiment, p_impact, p_model_tag, NOW())
  ON CONFLICT (item_id)
  DO UPDATE SET
    sentiment_json = EXCLUDED.sentiment_json,
    impact_json    = EXCLUDED.impact_json,
    model_tag      = EXCLUDED.model_tag,
    updated_at     = NOW();
END;
$$ LANGUAGE plpgsql;

-- Comment for documentation
COMMENT ON FUNCTION upsert_item_analysis(BIGINT, JSONB, JSONB, TEXT) IS 'Efficiently inserts or updates item analysis data with automatic timestamp management';