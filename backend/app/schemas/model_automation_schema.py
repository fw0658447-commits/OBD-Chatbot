from typing import Any

from pydantic import BaseModel, Field


class ModelAutomationConfigPatch(BaseModel):
    enabled: bool | None = Field(default=None)
    search_profile: str | None = Field(default=None)
    apply_search_profile: bool | None = Field(default=None)
    interval_minutes: int | None = Field(default=None, ge=5, le=1440)
    symbols: list[str] | str | None = Field(default=None)
    timeframes: list[str] | str | None = Field(default=None)
    strategies: list[str] | str | None = Field(default=None)
    model_type: str | None = Field(default=None)
    model_type_candidates: list[str] | str | None = Field(default=None)
    limit: int | None = Field(default=None, ge=180, le=2500)
    training_limit_candidates: list[int] | str | None = Field(default=None)
    lookahead_bars: int | None = Field(default=None, ge=1, le=120)
    lookahead_candidates: list[int] | str | None = Field(default=None)
    max_rows: int | None = Field(default=None, ge=200, le=50000)
    max_model_candidates: int | None = Field(default=None, ge=1, le=12)
    min_warmup_bars: int | None = Field(default=None, ge=50, le=500)
    assets_per_run: int | None = Field(default=None, ge=1, le=12)
    auto_expand_assets: bool | None = Field(default=None)
    asset_universe: list[str] | str | None = Field(default=None)
    max_auto_assets: int | None = Field(default=None, ge=1, le=50)
    strategies_per_asset: int | None = Field(default=None, ge=1, le=4)
    full_strategy_search: bool | None = Field(default=None)
    optimization_limit: int | None = Field(default=None, ge=160, le=1500)
    max_combinations: int | None = Field(default=None, ge=1, le=250)
    objective: str | None = Field(default=None)
    optimization_objectives: list[str] | str | None = Field(default=None)
    auto_objective_search: bool | None = Field(default=None)
    initial_capital: float | None = Field(default=None, gt=0)
    risk_per_trade: float | None = Field(default=None, gt=0, le=0.05)
    auto_update_bot_model: bool | None = Field(default=None)
    auto_update_bot_strategy: bool | None = Field(default=None)
    quality_gate_enabled: bool | None = Field(default=None)
    quality_require_beats_rule: bool | None = Field(default=None)
    min_model_accuracy: float | None = Field(default=None, ge=0, le=1)
    min_model_win_rate_percent: float | None = Field(default=None, ge=0, le=100)
    min_model_profit_factor: float | None = Field(default=None, ge=0, le=10)


class ModelAutomationRunRequest(BaseModel):
    config_patch: dict[str, Any] | None = Field(default=None)
