from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.config import settings
from app.repositories.trading_repository import trading_repository


def _symbols_from_env() -> list[str]:
    return [item.strip() for item in settings.scheduler_symbols.split(',') if item.strip()]


def _timeframes_from_env() -> list[str]:
    return [item.strip() for item in settings.scheduler_timeframes.split(',') if item.strip()]


DEFAULT_BOT_CONFIG: dict[str, Any] = {
    'config_name': 'default',
    'bot_enabled': False,
    'scheduler_enabled': False,
    'scheduler_interval_seconds': settings.scheduler_interval_seconds,
    'symbols': _symbols_from_env(),
    'timeframes': _timeframes_from_env(),
    'strategy_name': settings.default_strategy_name,
    'decision_mode': settings.default_decision_mode,
    'model_id': None,
    'max_risk_per_trade': settings.max_risk_per_trade,
    'max_daily_loss': settings.max_daily_loss,
    'max_open_trades': settings.max_open_trades,
    'min_crv': settings.min_crv,
    'min_confidence_score': settings.min_confidence_score,
    'max_risk_score': settings.max_risk_score,
    'min_ml_probability': 0.52,
    'min_model_profit_factor': 1.0,
    'min_model_win_rate': 45.0,
    'allow_degraded_fallback': True,
    'enforce_validation_gate': settings.enforce_validation_gate,
    'min_closed_trades_for_release': settings.min_closed_trades_for_release,
    'min_profit_factor_for_release': settings.min_profit_factor_for_release,
    'min_win_rate_for_release': settings.min_win_rate_for_release,
    'max_drawdown_percent_for_release': settings.max_drawdown_percent_for_release,
    'min_expectancy_per_trade_for_release': settings.min_expectancy_per_trade_for_release,
    'min_data_quality_score_for_release': settings.min_data_quality_score,
    'kill_switch_active': False,
    'live_trading_enabled': False,
}

_MEMORY_CONFIG = deepcopy(DEFAULT_BOT_CONFIG)


class BotRuntimeService:
    """Single place for mutable paper-bot runtime configuration.

    In PostgreSQL mode, this reads/writes bot_runtime_config. Without DB it keeps
    an in-memory config so the MVP still runs locally in mock mode.
    """

    def get_config(self) -> dict[str, Any]:
        if trading_repository.available:
            config = trading_repository.get_bot_config()
            if config:
                config['persistence'] = 'postgres'
                config['live_trading_enabled'] = False
                return config
        config = deepcopy(_MEMORY_CONFIG)
        config['persistence'] = 'memory'
        config['live_trading_enabled'] = False
        return config

    def update_config(self, patch: dict[str, Any]) -> dict[str, Any]:
        clean_patch = self._normalise_patch(patch)
        if trading_repository.available:
            config = trading_repository.update_bot_config(clean_patch)
            if config:
                config['persistence'] = 'postgres'
                config['live_trading_enabled'] = False
                return config
        _MEMORY_CONFIG.update(clean_patch)
        _MEMORY_CONFIG['live_trading_enabled'] = False
        config = deepcopy(_MEMORY_CONFIG)
        config['persistence'] = 'memory'
        return config

    def activate_kill_switch(self) -> dict[str, Any]:
        config = self.update_config({
            'bot_enabled': False,
            'scheduler_enabled': False,
            'kill_switch_active': True,
        })
        if trading_repository.available:
            trading_repository.log_risk_event(
                event_type='kill_switch',
                severity='critical',
                message='Kill-Switch activated. New paper bot cycles are blocked. Live trading remains disabled.',
            )
        return config

    def reset_kill_switch(self) -> dict[str, Any]:
        config = self.update_config({'kill_switch_active': False})
        if trading_repository.available:
            trading_repository.log_risk_event(
                event_type='kill_switch_reset',
                severity='warning',
                message='Kill-Switch reset. Bot can run in paper mode if bot_enabled is true.',
            )
        return config

    def _normalise_patch(self, patch: dict[str, Any]) -> dict[str, Any]:
        allowed = set(DEFAULT_BOT_CONFIG.keys()) - {'config_name', 'live_trading_enabled', 'persistence'}
        result: dict[str, Any] = {}
        for key, value in (patch or {}).items():
            if key not in allowed or value is None:
                continue
            if key in {'symbols', 'timeframes'}:
                if isinstance(value, str):
                    result[key] = [item.strip() for item in value.split(',') if item.strip()]
                else:
                    result[key] = [str(item).strip() for item in value if str(item).strip()]
            elif key in {'bot_enabled', 'scheduler_enabled', 'allow_degraded_fallback', 'enforce_validation_gate', 'kill_switch_active'}:
                result[key] = bool(value)
            elif key in {'scheduler_interval_seconds', 'max_open_trades', 'min_closed_trades_for_release'}:
                result[key] = int(value)
            elif key in {'max_risk_per_trade', 'max_daily_loss', 'min_crv', 'min_confidence_score', 'max_risk_score', 'min_ml_probability', 'min_model_profit_factor', 'min_model_win_rate', 'min_profit_factor_for_release', 'min_win_rate_for_release', 'max_drawdown_percent_for_release', 'min_expectancy_per_trade_for_release', 'min_data_quality_score_for_release'}:
                result[key] = float(value)
            else:
                result[key] = value
        result['live_trading_enabled'] = False
        return result


bot_runtime_service = BotRuntimeService()
