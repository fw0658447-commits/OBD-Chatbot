ALTER TABLE paper_orders ADD COLUMN IF NOT EXISTS requested_entry_price NUMERIC;
ALTER TABLE paper_orders ADD COLUMN IF NOT EXISTS requested_exit_price NUMERIC;
ALTER TABLE paper_orders ADD COLUMN IF NOT EXISTS gross_pnl_amount NUMERIC;
ALTER TABLE paper_orders ADD COLUMN IF NOT EXISTS entry_slippage_bps NUMERIC;
ALTER TABLE paper_orders ADD COLUMN IF NOT EXISTS exit_slippage_bps NUMERIC;
ALTER TABLE paper_orders ADD COLUMN IF NOT EXISTS spread_bps NUMERIC;
ALTER TABLE paper_orders ADD COLUMN IF NOT EXISTS entry_commission NUMERIC DEFAULT 0;
ALTER TABLE paper_orders ADD COLUMN IF NOT EXISTS exit_commission NUMERIC DEFAULT 0;
ALTER TABLE paper_orders ADD COLUMN IF NOT EXISTS total_commission NUMERIC DEFAULT 0;

CREATE TABLE IF NOT EXISTS data_quality_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES assets(id),
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    provider TEXT,
    quality_score NUMERIC NOT NULL,
    trade_allowed BOOLEAN DEFAULT FALSE,
    issue_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    largest_gap_ratio NUMERIC,
    latest_candle_age_minutes NUMERIC,
    report JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_data_quality_reports_created_at ON data_quality_reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_data_quality_reports_symbol_timeframe ON data_quality_reports(symbol, timeframe, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_market_candles_asset_tf_time ON market_candles(asset_id, timeframe, candle_time DESC);
