CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS ml_model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id TEXT NOT NULL UNIQUE,
    model_type TEXT NOT NULL,
    model_path TEXT,
    symbols JSONB DEFAULT '[]'::jsonb,
    timeframes JSONB DEFAULT '[]'::jsonb,
    strategies JSONB DEFAULT '[]'::jsonb,
    lookahead_bars INTEGER,
    row_count INTEGER,
    train_rows INTEGER,
    test_rows INTEGER,
    feature_columns JSONB DEFAULT '[]'::jsonb,
    class_labels JSONB DEFAULT '[]'::jsonb,
    metrics JSONB DEFAULT '{}'::jsonb,
    rule_baseline_metrics JSONB DEFAULT '{}'::jsonb,
    trading_metrics JSONB DEFAULT '{}'::jsonb,
    rule_trading_metrics JSONB DEFAULT '{}'::jsonb,
    feature_importance JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ml_prediction_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id TEXT,
    symbol TEXT,
    timeframe TEXT,
    strategy TEXT,
    prediction_label INTEGER,
    prediction_direction TEXT,
    probabilities JSONB DEFAULT '{}'::jsonb,
    features JSONB DEFAULT '{}'::jsonb,
    result JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ml_model_versions_created_at ON ml_model_versions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ml_prediction_runs_created_at ON ml_prediction_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ml_prediction_runs_symbol ON ml_prediction_runs(symbol);
