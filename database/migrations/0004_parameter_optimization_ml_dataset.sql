CREATE TABLE IF NOT EXISTS parameter_optimization_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    strategy TEXT NOT NULL,
    objective TEXT NOT NULL,
    tested_combinations INTEGER DEFAULT 0,
    best_score NUMERIC,
    best_params JSONB DEFAULT '{}'::jsonb,
    results JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ml_dataset_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    row_count INTEGER DEFAULT 0,
    feature_columns JSONB DEFAULT '[]'::jsonb,
    target_columns JSONB DEFAULT '[]'::jsonb,
    note TEXT,
    sample_rows JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_parameter_optimization_created_at ON parameter_optimization_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_parameter_optimization_strategy ON parameter_optimization_runs(strategy);
CREATE INDEX IF NOT EXISTS idx_ml_dataset_exports_created_at ON ml_dataset_exports(created_at DESC);
