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
