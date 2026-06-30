from typing import Any
from pydantic import BaseModel, Field


class MLTrainRequest(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ['BTC/USD', 'ETH/USD', 'AAPL', 'SPY'])
    timeframes: list[str] = Field(default_factory=lambda: ['1h'])
    strategies: list[str] = Field(default_factory=lambda: ['trend_atr_v0.7', 'pullback_ema_v0.7'])
    limit: int = Field(default=650, ge=180, le=2500)
    lookahead_bars: int = Field(default=12, ge=1, le=120)
    max_rows: int = Field(default=5000, ge=200, le=50000)
    min_warmup_bars: int = Field(default=80, ge=50, le=500)
    model_type: str = Field(default='random_forest')
    test_size: float = Field(default=0.25, gt=0.05, lt=0.5)
    target_column: str = Field(default='target_label')
    persist: bool = Field(default=True)


class MLPredictRequest(BaseModel):
    model_id: str | None = Field(default=None)
    features: dict[str, Any] = Field(default_factory=dict)


class MLPredictAssetRequest(BaseModel):
    model_id: str | None = Field(default=None)
    symbol: str = Field(default='BTC/USD')
    timeframe: str = Field(default='1h')
    strategy_name: str = Field(default='trend_atr_v0.7')
    limit: int = Field(default=220, ge=120, le=1500)


class MLCompareRequest(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ['BTC/USD', 'ETH/USD', 'AAPL', 'SPY'])
    timeframes: list[str] = Field(default_factory=lambda: ['1h'])
    strategies: list[str] = Field(default_factory=lambda: ['trend_atr_v0.7', 'pullback_ema_v0.7'])
    limit: int = Field(default=650, ge=180, le=2500)
    lookahead_bars: int = Field(default=12, ge=1, le=120)
    max_rows: int = Field(default=5000, ge=200, le=50000)
    model_type: str = Field(default='random_forest')
