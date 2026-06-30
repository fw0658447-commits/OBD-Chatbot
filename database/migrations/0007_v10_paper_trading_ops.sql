CREATE TABLE IF NOT EXISTS bot_runtime_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_name TEXT NOT NULL UNIQUE DEFAULT 'default',
    bot_enabled BOOLEAN DEFAULT FALSE,
    scheduler_enabled BOOLEAN DEFAULT FALSE,
    scheduler_interval_seconds INTEGER DEFAULT 60,
    symbols JSONB DEFAULT '["BTC/USD", "ETH/USD", "AAPL", "SPY"]'::jsonb,
    timeframes JSONB DEFAULT '["1h"]'::jsonb,
    strategy_name TEXT DEFAULT 'trend_atr_v0.7',
    decision_mode TEXT DEFAULT 'rule',
    model_id TEXT,
    max_risk_per_trade NUMERIC DEFAULT 0.01,
    max_daily_loss NUMERIC DEFAULT 0.02,
    max_open_trades INTEGER DEFAULT 3,
    min_crv NUMERIC DEFAULT 2.0,
    min_confidence_score NUMERIC DEFAULT 65,
    max_risk_score NUMERIC DEFAULT 70,
    min_ml_probability NUMERIC DEFAULT 0.52,
    min_model_profit_factor NUMERIC DEFAULT 1.0,
    min_model_win_rate NUMERIC DEFAULT 45,
    allow_degraded_fallback BOOLEAN DEFAULT TRUE,
    kill_switch_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO bot_runtime_config (config_name)
VALUES ('default')
ON CONFLICT (config_name) DO NOTHING;

CREATE TABLE IF NOT EXISTS scheduler_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT,
    status TEXT,
    symbols JSONB DEFAULT '[]'::jsonb,
    timeframes JSONB DEFAULT '[]'::jsonb,
    strategy TEXT,
    decision_mode TEXT,
    result JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bot_runtime_config_name ON bot_runtime_config(config_name);
CREATE INDEX IF NOT EXISTS idx_scheduler_runs_created_at ON scheduler_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scheduler_runs_status ON scheduler_runs(status);
