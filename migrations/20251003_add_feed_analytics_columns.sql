-- Migration: Add analytics and health scoring columns to feeds table
-- Date: 2025-10-03
-- Description: Adds computed columns for health score, article counts, and error tracking

-- Add new columns for health scoring and analytics
ALTER TABLE feeds
ADD COLUMN IF NOT EXISTS health_score INTEGER DEFAULT 50 CHECK (health_score >= 0 AND health_score <= 100),
ADD COLUMN IF NOT EXISTS last_error_message TEXT,
ADD COLUMN IF NOT EXISTS last_error_at TIMESTAMP WITHOUT TIME ZONE,
ADD COLUMN IF NOT EXISTS total_articles INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS articles_24h INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS analyzed_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS analyzed_percentage FLOAT DEFAULT 0.0 CHECK (analyzed_percentage >= 0 AND analyzed_percentage <= 100),
ADD COLUMN IF NOT EXISTS source_label VARCHAR(255);

-- Create index on health_score for sorting
CREATE INDEX IF NOT EXISTS idx_feeds_health_score ON feeds(health_score DESC);

-- Create index on last_error_at for filtering error feeds
CREATE INDEX IF NOT EXISTS idx_feeds_last_error_at ON feeds(last_error_at DESC) WHERE last_error_at IS NOT NULL;

-- Create index on source_label for search
CREATE INDEX IF NOT EXISTS idx_feeds_source_label ON feeds(source_label);

-- Comments for documentation
COMMENT ON COLUMN feeds.health_score IS 'Computed health score 0-100 (Reachability 30% + Volume 25% + Duplicates 15% + Quality 15% + Stability 15%)';
COMMENT ON COLUMN feeds.last_error_message IS 'Last error message from fetch or processing';
COMMENT ON COLUMN feeds.last_error_at IS 'Timestamp of last error occurrence';
COMMENT ON COLUMN feeds.total_articles IS 'Total number of articles ever fetched from this feed';
COMMENT ON COLUMN feeds.articles_24h IS 'Number of articles fetched in last 24 hours';
COMMENT ON COLUMN feeds.analyzed_count IS 'Number of articles that have been analyzed';
COMMENT ON COLUMN feeds.analyzed_percentage IS 'Percentage of articles analyzed (analyzed_count / total_articles * 100)';
COMMENT ON COLUMN feeds.source_label IS 'Human-friendly source label (e.g., "Heise Online", "TechCrunch")';

-- Initialize total_articles from existing items
UPDATE feeds
SET total_articles = (
    SELECT COUNT(*)
    FROM items
    WHERE items.feed_id = feeds.id
);

-- Initialize articles_24h from recent items
UPDATE feeds
SET articles_24h = (
    SELECT COUNT(*)
    FROM items
    WHERE items.feed_id = feeds.id
    AND items.created_at >= NOW() - INTERVAL '24 hours'
);

-- Initialize analyzed_count from item_analysis
UPDATE feeds
SET analyzed_count = (
    SELECT COUNT(DISTINCT item_analysis.item_id)
    FROM item_analysis
    JOIN items ON item_analysis.item_id = items.id
    WHERE items.feed_id = feeds.id
);

-- Initialize analyzed_percentage
UPDATE feeds
SET analyzed_percentage = CASE
    WHEN total_articles > 0 THEN (analyzed_count::float / total_articles::float * 100)
    ELSE 0
END;

-- Initialize source_label from feed title (if not set)
UPDATE feeds
SET source_label = title
WHERE source_label IS NULL AND title IS NOT NULL;

-- Create a function to update analytics (can be called by background job)
CREATE OR REPLACE FUNCTION update_feed_analytics(p_feed_id INTEGER)
RETURNS VOID AS $$
BEGIN
    UPDATE feeds
    SET
        total_articles = (
            SELECT COUNT(*)
            FROM items
            WHERE items.feed_id = p_feed_id
        ),
        articles_24h = (
            SELECT COUNT(*)
            FROM items
            WHERE items.feed_id = p_feed_id
            AND items.created_at >= NOW() - INTERVAL '24 hours'
        ),
        analyzed_count = (
            SELECT COUNT(DISTINCT item_analysis.item_id)
            FROM item_analysis
            JOIN items ON item_analysis.item_id = items.id
            WHERE items.feed_id = p_feed_id
        ),
        analyzed_percentage = CASE
            WHEN (SELECT COUNT(*) FROM items WHERE items.feed_id = p_feed_id) > 0
            THEN (
                (SELECT COUNT(DISTINCT item_analysis.item_id)::float
                 FROM item_analysis
                 JOIN items ON item_analysis.item_id = items.id
                 WHERE items.feed_id = p_feed_id)
                /
                (SELECT COUNT(*)::float FROM items WHERE items.feed_id = p_feed_id)
                * 100
            )
            ELSE 0
        END,
        updated_at = NOW()
    WHERE id = p_feed_id;
END;
$$ LANGUAGE plpgsql;

-- Create a function to update all feed analytics (for background job)
CREATE OR REPLACE FUNCTION update_all_feed_analytics()
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER := 0;
    feed_record RECORD;
BEGIN
    FOR feed_record IN SELECT id FROM feeds LOOP
        PERFORM update_feed_analytics(feed_record.id);
        updated_count := updated_count + 1;
    END LOOP;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_feed_analytics(INTEGER) IS 'Updates analytics columns for a specific feed';
COMMENT ON FUNCTION update_all_feed_analytics() IS 'Updates analytics columns for all feeds (use in background job)';
