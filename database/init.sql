CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    exchange TEXT,
    currency TEXT,
    provider TEXT,
    provider_symbol TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS watchlist_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES assets(id),
    target_price NUMERIC,
    alert_price NUMERIC,
    note TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS market_candles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES assets(id),
    timeframe TEXT NOT NULL,
    open NUMERIC NOT NULL,
    high NUMERIC NOT NULL,
    low NUMERIC NOT NULL,
    close NUMERIC NOT NULL,
    volume NUMERIC,
    candle_time TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(asset_id, timeframe, candle_time)
);

CREATE TABLE IF NOT EXISTS ai_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES assets(id),
    timeframe TEXT NOT NULL,
    horizon TEXT NOT NULL,
    direction TEXT NOT NULL,
    probability_long NUMERIC NOT NULL,
    probability_short NUMERIC NOT NULL,
    probability_neutral NUMERIC NOT NULL,
    expected_return_percent NUMERIC,
    confidence_score NUMERIC NOT NULL,
    risk_score NUMERIC NOT NULL,
    explanation TEXT,
    model_version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bot_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID REFERENCES assets(id),
    prediction_id UUID REFERENCES ai_predictions(id),
    signal_type TEXT NOT NULL,
    signal_score NUMERIC NOT NULL,
    entry_price NUMERIC NOT NULL,
    stop_loss NUMERIC NOT NULL,
    take_profit NUMERIC NOT NULL,
    crv NUMERIC NOT NULL,
    status TEXT NOT NULL,
    reason TEXT,
    decision_mode TEXT DEFAULT 'rule',
    model_source TEXT DEFAULT 'rule',
    ml_model_id TEXT,
    ml_direction TEXT,
    ml_probability NUMERIC,
    decision_score NUMERIC,
    decision_details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS paper_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID REFERENCES bot_signals(id),
    asset_id UUID REFERENCES assets(id),
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    quantity NUMERIC NOT NULL,
    entry_price NUMERIC NOT NULL,
    stop_loss NUMERIC NOT NULL,
    take_profit NUMERIC NOT NULL,
    status TEXT NOT NULL,
    decision_mode TEXT DEFAULT 'rule',
    model_source TEXT DEFAULT 'rule',
    ml_model_id TEXT,
    ml_direction TEXT,
    ml_probability NUMERIC,
    decision_score NUMERIC,
    decision_details JSONB DEFAULT '{}'::jsonb,
    opened_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP,
    exit_price NUMERIC,
    pnl_amount NUMERIC,
    pnl_percent NUMERIC
);

CREATE TABLE IF NOT EXISTS paper_portfolio (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cash_balance NUMERIC NOT NULL,
    starting_balance NUMERIC NOT NULL,
    current_equity NUMERIC NOT NULL,
    total_realized_pnl NUMERIC DEFAULT 0,
    total_unrealized_pnl NUMERIC DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO assets (symbol, name, asset_type, exchange, currency, provider, provider_symbol)
VALUES
    ('BTC/USD', 'Bitcoin US Dollar', 'crypto', 'MOCK', 'USD', 'mock', 'BTC/USD'),
    ('ETH/USD', 'Ethereum US Dollar', 'crypto', 'MOCK', 'USD', 'mock', 'ETH/USD'),
    ('AAPL', 'Apple Inc.', 'stock', 'NASDAQ', 'USD', 'mock', 'AAPL'),
    ('SPY', 'SPDR S&P 500 ETF', 'etf', 'NYSEARCA', 'USD', 'mock', 'SPY'),
    ('EUR/USD', 'Euro US Dollar', 'forex', 'FX', 'USD', 'mock', 'EUR/USD'),
    ('XAU/USD', 'Gold Spot US Dollar', 'commodity', 'FX', 'USD', 'mock', 'XAU/USD')
ON CONFLICT DO NOTHING;

INSERT INTO paper_portfolio (cash_balance, starting_balance, current_equity)
VALUES (10000, 10000, 10000);

CREATE INDEX IF NOT EXISTS idx_ai_predictions_created_at ON ai_predictions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bot_signals_created_at ON bot_signals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bot_signals_status ON bot_signals(status);
CREATE INDEX IF NOT EXISTS idx_paper_orders_status ON paper_orders(status);
CREATE INDEX IF NOT EXISTS idx_paper_orders_opened_at ON paper_orders(opened_at DESC);
CREATE INDEX IF NOT EXISTS idx_risk_events_created_at ON risk_events(created_at DESC);

CREATE TABLE IF NOT EXISTS backtest_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    strategy TEXT NOT NULL,
    initial_capital NUMERIC NOT NULL,
    final_equity NUMERIC NOT NULL,
    total_trades INTEGER DEFAULT 0,
    win_rate_percent NUMERIC DEFAULT 0,
    profit_factor NUMERIC,
    total_pnl NUMERIC DEFAULT 0,
    return_percent NUMERIC DEFAULT 0,
    max_drawdown_percent NUMERIC DEFAULT 0,
    metrics JSONB DEFAULT '{}'::jsonb,
    equity_curve JSONB DEFAULT '[]'::jsonb,
    trades JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_created_at ON backtest_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_symbol_timeframe ON backtest_runs(symbol, timeframe);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy ON backtest_runs(strategy);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy_symbol_timeframe ON backtest_runs(strategy, symbol, timeframe);
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


CREATE TABLE IF NOT EXISTS bot_decision_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT,
    timeframe TEXT,
    strategy TEXT,
    decision_mode TEXT,
    model_source TEXT,
    ml_model_id TEXT,
    allowed BOOLEAN,
    decision_score NUMERIC,
    reason TEXT,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_paper_orders_decision_mode ON paper_orders(decision_mode);
CREATE INDEX IF NOT EXISTS idx_bot_signals_decision_mode ON bot_signals(decision_mode);
CREATE INDEX IF NOT EXISTS idx_bot_decision_audit_created_at ON bot_decision_audit(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bot_decision_audit_mode ON bot_decision_audit(decision_mode);


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

-- v1.3 usability, portfolio and market-status additions
ALTER TABLE watchlist_items ADD COLUMN IF NOT EXISTS target_price NUMERIC;
CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlist_items_asset_unique ON watchlist_items(asset_id);

CREATE TABLE IF NOT EXISTS paper_cash_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_type TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    balance_after NUMERIC,
    note TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_paper_cash_transactions_created_at
ON paper_cash_transactions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_paper_orders_asset_status
ON paper_orders(asset_id, status);
