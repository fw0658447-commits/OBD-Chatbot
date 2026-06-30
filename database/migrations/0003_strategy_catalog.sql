-- v0.6 keeps the existing backtest_runs table and uses the existing strategy column.
-- These indexes make strategy-centred comparisons faster once PostgreSQL persistence is enabled.
CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy ON backtest_runs(strategy);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy_symbol_timeframe ON backtest_runs(strategy, symbol, timeframe);
