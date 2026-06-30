from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    database_url: str = ''
    redis_url: str = ''
    market_data_provider: str = 'free'
    market_data_api_key: str = ''
    openfigi_api_key: str = ''
    finnhub_api_key: str = ''
    alpha_vantage_api_key: str = ''
    internet_analysis_provider: str = 'auto'
    bot_mode: str = 'paper'
    model_storage_path: str = '/tmp/trading-cockpit-models'

    max_risk_per_trade: float = 0.01
    max_daily_loss: float = 0.02
    max_open_trades: int = 3
    min_crv: float = 2.0
    min_confidence_score: float = 65.0
    max_risk_score: float = 70.0
    live_trading_enabled: bool = False

    scheduler_interval_seconds: int = 60
    scheduler_symbols: str = 'BTC/USD,ETH/USD,AAPL,SPY'
    scheduler_timeframes: str = '1h'
    default_strategy_name: str = 'trend_atr_v0.7'
    default_decision_mode: str = 'rule'

    quote_cache_ttl_seconds: int = 10
    candle_cache_ttl_seconds: int = 60
    market_provider_fallback_enabled: bool = True
    block_trades_on_data_quality_fail: bool = True
    min_data_quality_score: float = 70.0

    # v1.2 validation gates for realistic paper-operation release.
    enforce_validation_gate: bool = False
    min_closed_trades_for_release: int = 100
    min_profit_factor_for_release: float = 1.15
    min_win_rate_for_release: float = 45.0
    max_drawdown_percent_for_release: float = 12.0
    min_expectancy_per_trade_for_release: float = 0.0

    paper_slippage_bps: float = 2.0
    paper_spread_bps: float = 4.0
    paper_commission_bps: float = 1.0
    paper_min_commission: float = 0.0

    live_trading_hard_locked: bool = True


settings = Settings()
