-- Analysis Control Center Tables
-- Migration: 002_create_analysis_runs.sql

-- Table for tracking analysis runs
CREATE TABLE IF NOT EXISTS analysis_runs (
    id                 BIGSERIAL PRIMARY KEY,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Run Configuration
    scope_json         JSONB NOT NULL DEFAULT '{}'::jsonb,
    params_json        JSONB NOT NULL DEFAULT '{}'::jsonb,
    scope_hash         TEXT NOT NULL,

    -- Run Status
    status             TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'paused', 'completed', 'failed', 'cancelled')),

    -- Progress Metrics
    queued_count       INTEGER NOT NULL DEFAULT 0,
    processed_count    INTEGER NOT NULL DEFAULT 0,
    failed_count       INTEGER NOT NULL DEFAULT 0,

    -- Performance Metrics
    cost_estimate      DECIMAL(10,4) DEFAULT 0.0,
    actual_cost        DECIMAL(10,4) DEFAULT 0.0,
    error_rate         DECIMAL(5,4) DEFAULT 0.0,
    items_per_min      DECIMAL(8,2) DEFAULT 0.0,
    eta_seconds        INTEGER DEFAULT NULL,

    -- Coverage Metrics (SLO tracking)
    coverage_10m       DECIMAL(5,4) DEFAULT 0.0,
    coverage_60m       DECIMAL(5,4) DEFAULT 0.0,

    -- Runtime Info
    started_at         TIMESTAMPTZ DEFAULT NULL,
    completed_at       TIMESTAMPTZ DEFAULT NULL,
    last_error         TEXT DEFAULT NULL
);

-- Index for efficient queries
CREATE INDEX IF NOT EXISTS idx_analysis_runs_status ON analysis_runs(status);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_created ON analysis_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_scope_hash ON analysis_runs(scope_hash);

-- Table for tracking individual items in a run
CREATE TABLE IF NOT EXISTS analysis_run_items (
    id                 BIGSERIAL PRIMARY KEY,
    run_id             BIGINT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    item_id            BIGINT NOT NULL REFERENCES items(id) ON DELETE CASCADE,

    -- Item Status
    state              TEXT NOT NULL DEFAULT 'queued' CHECK (state IN ('queued', 'processing', 'completed', 'failed', 'skipped')),

    -- Processing Info
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at         TIMESTAMPTZ DEFAULT NULL,
    completed_at       TIMESTAMPTZ DEFAULT NULL,
    error_message      TEXT DEFAULT NULL,

    -- Cost Tracking
    tokens_used        INTEGER DEFAULT NULL,
    cost_usd           DECIMAL(8,6) DEFAULT NULL,

    UNIQUE(run_id, item_id)
);

-- Indexes for efficient item tracking
CREATE INDEX IF NOT EXISTS idx_run_items_run_id ON analysis_run_items(run_id);
CREATE INDEX IF NOT EXISTS idx_run_items_state ON analysis_run_items(state);
CREATE INDEX IF NOT EXISTS idx_run_items_item_id ON analysis_run_items(item_id);

-- Table for saving analysis presets
CREATE TABLE IF NOT EXISTS analysis_presets (
    id                 BIGSERIAL PRIMARY KEY,
    name               TEXT NOT NULL UNIQUE,
    description        TEXT DEFAULT NULL,
    scope_json         JSONB NOT NULL DEFAULT '{}'::jsonb,
    params_json        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Update trigger for analysis_runs
CREATE OR REPLACE FUNCTION update_analysis_runs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_analysis_runs_updated_at
    BEFORE UPDATE ON analysis_runs
    FOR EACH ROW
    EXECUTE FUNCTION update_analysis_runs_updated_at();

-- Update trigger for analysis_presets
CREATE TRIGGER trigger_analysis_presets_updated_at
    BEFORE UPDATE ON analysis_presets
    FOR EACH ROW
    EXECUTE FUNCTION update_analysis_runs_updated_at();

-- Helper function to calculate run metrics
CREATE OR REPLACE FUNCTION calculate_run_metrics(p_run_id BIGINT)
RETURNS TABLE(
    queued_count INTEGER,
    processed_count INTEGER,
    failed_count INTEGER,
    error_rate DECIMAL(5,4),
    eta_seconds INTEGER
) AS $$
DECLARE
    total_items INTEGER;
    items_done INTEGER;
    items_failed INTEGER;
    avg_time_per_item DECIMAL;
    remaining_items INTEGER;
BEGIN
    -- Get counts
    SELECT
        COUNT(CASE WHEN state = 'queued' THEN 1 END),
        COUNT(CASE WHEN state IN ('completed', 'skipped') THEN 1 END),
        COUNT(CASE WHEN state = 'failed' THEN 1 END)
    INTO queued_count, processed_count, failed_count
    FROM analysis_run_items
    WHERE run_id = p_run_id;

    total_items := queued_count + processed_count + failed_count;
    items_done := processed_count + failed_count;

    -- Calculate error rate
    IF items_done > 0 THEN
        error_rate := failed_count::DECIMAL / items_done;
    ELSE
        error_rate := 0.0;
    END IF;

    -- Calculate ETA (simple estimation based on completed items)
    IF processed_count > 5 THEN
        SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
        INTO avg_time_per_item
        FROM analysis_run_items
        WHERE run_id = p_run_id
        AND state = 'completed'
        AND completed_at IS NOT NULL
        AND started_at IS NOT NULL;

        remaining_items := queued_count + (SELECT COUNT(*) FROM analysis_run_items WHERE run_id = p_run_id AND state = 'processing');

        IF avg_time_per_item > 0 THEN
            eta_seconds := (remaining_items * avg_time_per_item)::INTEGER;
        ELSE
            eta_seconds := NULL;
        END IF;
    ELSE
        eta_seconds := NULL;
    END IF;

    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;