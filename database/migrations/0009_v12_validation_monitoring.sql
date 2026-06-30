ALTER TABLE bot_runtime_config ADD COLUMN IF NOT EXISTS enforce_validation_gate BOOLEAN DEFAULT FALSE;
ALTER TABLE bot_runtime_config ADD COLUMN IF NOT EXISTS min_closed_trades_for_release INTEGER DEFAULT 100;
ALTER TABLE bot_runtime_config ADD COLUMN IF NOT EXISTS min_profit_factor_for_release NUMERIC DEFAULT 1.15;
ALTER TABLE bot_runtime_config ADD COLUMN IF NOT EXISTS min_win_rate_for_release NUMERIC DEFAULT 45;
ALTER TABLE bot_runtime_config ADD COLUMN IF NOT EXISTS max_drawdown_percent_for_release NUMERIC DEFAULT 12;
ALTER TABLE bot_runtime_config ADD COLUMN IF NOT EXISTS min_expectancy_per_trade_for_release NUMERIC DEFAULT 0;
ALTER TABLE bot_runtime_config ADD COLUMN IF NOT EXISTS min_data_quality_score_for_release NUMERIC DEFAULT 70;

CREATE TABLE IF NOT EXISTS monitoring_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_type TEXT NOT NULL,
    status TEXT,
    summary JSONB DEFAULT '{}'::jsonb,
    report JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_monitoring_reports_created_at ON monitoring_reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_monitoring_reports_type ON monitoring_reports(report_type, created_at DESC);
