from pydantic import BaseModel, Field


class BotRunRequest(BaseModel):
    symbol: str = Field(..., examples=['BTC/USD'])
    timeframe: str = Field(default='1h', examples=['1h'])
    portfolio_value: float = Field(default=10000, gt=0)
    open_trades_count: int = Field(default=0, ge=0)
    daily_pnl_percent: float = Field(default=0)
    strategy_name: str = Field(default='trend_atr_v0.7')
    decision_mode: str = Field(default='rule', description='rule, ml, or ensemble')
    model_id: str | None = Field(default=None, description='Optional trained ML model id. If omitted, latest model is used.')
    min_ml_probability: float = Field(default=0.52, ge=0.0, le=1.0)
    min_model_profit_factor: float = Field(default=1.0, ge=0.0)
    min_model_win_rate: float = Field(default=45.0, ge=0.0, le=100.0)
    allow_degraded_fallback: bool = Field(default=True)


class BotStatusResponse(BaseModel):
    status: str
    mode: str
    live_trading_enabled: bool
    max_risk_per_trade: float
    max_daily_loss: float
    max_open_trades: int
    min_crv: float
    min_confidence_score: float
    max_risk_score: float
    supported_decision_modes: list[str]
    default_decision_mode: str
    validation_gate: dict | None = None
    paper_execution_model: dict | None = None


class ManualCloseOrderRequest(BaseModel):
    exit_price: float | None = Field(default=None, gt=0)
    reason: str = Field(default='closed_manual')


class BotConfigPatch(BaseModel):
    bot_enabled: bool | None = None
    scheduler_enabled: bool | None = None
    scheduler_interval_seconds: int | None = Field(default=None, ge=10, le=86400)
    symbols: list[str] | str | None = None
    timeframes: list[str] | str | None = None
    strategy_name: str | None = None
    decision_mode: str | None = Field(default=None, description='rule, ml, or ensemble')
    model_id: str | None = None
    max_risk_per_trade: float | None = Field(default=None, gt=0, le=0.1)
    max_daily_loss: float | None = Field(default=None, gt=0, le=0.5)
    max_open_trades: int | None = Field(default=None, ge=1, le=100)
    min_crv: float | None = Field(default=None, ge=0)
    min_confidence_score: float | None = Field(default=None, ge=0, le=100)
    max_risk_score: float | None = Field(default=None, ge=0, le=100)
    min_ml_probability: float | None = Field(default=None, ge=0, le=1)
    min_model_profit_factor: float | None = Field(default=None, ge=0)
    min_model_win_rate: float | None = Field(default=None, ge=0, le=100)
    allow_degraded_fallback: bool | None = None
    enforce_validation_gate: bool | None = None
    min_closed_trades_for_release: int | None = Field(default=None, ge=1, le=100000)
    min_profit_factor_for_release: float | None = Field(default=None, ge=0)
    min_win_rate_for_release: float | None = Field(default=None, ge=0, le=100)
    max_drawdown_percent_for_release: float | None = Field(default=None, ge=0, le=100)
    min_expectancy_per_trade_for_release: float | None = None
    min_data_quality_score_for_release: float | None = Field(default=None, ge=0, le=100)
    kill_switch_active: bool | None = None
