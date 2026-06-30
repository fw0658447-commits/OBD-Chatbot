from typing import Any
from pydantic import BaseModel, Field


DEFAULT_STRATEGIES = [
    'trend_atr_v0.7',
    'pullback_ema_v0.7',
    'breakout_range_v0.7',
    'mean_reversion_rsi_v0.7',
]


class BacktestRunRequest(BaseModel):
    symbol: str = Field(default='BTC/USD')
    timeframe: str = Field(default='1h')
    strategy_name: str = Field(default='trend_atr_v0.7')
    strategy_params: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=420, ge=120, le=1500)
    initial_capital: float = Field(default=10000, gt=0)
    risk_per_trade: float = Field(default=0.01, gt=0, le=0.05)
    max_hold_bars: int | None = Field(default=None, ge=1, le=240)
    min_warmup_bars: int = Field(default=80, ge=50, le=500)
    min_confidence_score: float = Field(default=65, ge=0, le=100)
    max_risk_score: float = Field(default=70, ge=0, le=100)
    min_crv: float = Field(default=2.0, ge=0.5, le=10)
    persist: bool = Field(default=True)


class BacktestCompareRequest(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ['BTC/USD', 'ETH/USD', 'AAPL', 'SPY'])
    timeframes: list[str] = Field(default_factory=lambda: ['1h', '4h'])
    strategies: list[str] = Field(default_factory=lambda: DEFAULT_STRATEGIES.copy())
    limit: int = Field(default=420, ge=120, le=1500)
    initial_capital: float = Field(default=10000, gt=0)


class WalkForwardRequest(BaseModel):
    symbol: str = Field(default='BTC/USD')
    timeframe: str = Field(default='1h')
    strategy_name: str = Field(default='trend_atr_v0.7')
    limit: int = Field(default=720, ge=180, le=2000)
    initial_capital: float = Field(default=10000, gt=0)
    splits: int = Field(default=3, ge=2, le=8)
    min_warmup_bars: int = Field(default=80, ge=50, le=500)


class ParameterOptimizationRequest(BaseModel):
    symbol: str = Field(default='BTC/USD')
    timeframe: str = Field(default='1h')
    strategy_name: str = Field(default='trend_atr_v0.7')
    limit: int = Field(default=420, ge=160, le=1500)
    initial_capital: float = Field(default=10000, gt=0)
    risk_per_trade: float = Field(default=0.01, gt=0, le=0.05)
    objective: str = Field(default='robust_score')
    max_combinations: int = Field(default=60, ge=1, le=250)
    min_warmup_bars: int = Field(default=80, ge=50, le=500)
    parameter_grid: dict[str, list[Any]] | None = Field(default=None)
    persist: bool = Field(default=True)


class MLDatasetRequest(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ['BTC/USD', 'ETH/USD', 'AAPL', 'SPY'])
    timeframes: list[str] = Field(default_factory=lambda: ['1h'])
    strategies: list[str] = Field(default_factory=lambda: DEFAULT_STRATEGIES.copy())
    limit: int = Field(default=500, ge=120, le=1500)
    lookahead_bars: int = Field(default=12, ge=1, le=120)
    max_rows: int = Field(default=5000, ge=100, le=20000)
    min_warmup_bars: int = Field(default=80, ge=50, le=500)
    include_csv: bool = Field(default=True)
    persist: bool = Field(default=True)
