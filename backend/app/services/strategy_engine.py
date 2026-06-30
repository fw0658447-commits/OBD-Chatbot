from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class StrategyDefinition:
    name: str
    label: str
    description: str
    family: str
    min_confidence: float
    max_risk_score: float
    default_max_hold_bars: int
    default_params: dict[str, Any] = field(default_factory=dict)
    optimization_grid: dict[str, list[Any]] = field(default_factory=dict)


class StrategyEngine:
    """Rule-strategy catalogue for bot signals and backtests.

    The catalogue keeps the trading decision deterministic and auditable. The
    AI-prediction module supplies direction/confidence/risk; the selected
    strategy converts that into concrete entry, stop, target and CRV values.

    v0.7 adds parameter overrides so the optimizer can sweep strategy-specific
    values without changing production defaults.
    """

    DEFAULT_STRATEGY = 'trend_atr_v0.7'

    STRATEGIES: dict[str, StrategyDefinition] = {
        'trend_atr_v0.7': StrategyDefinition(
            name='trend_atr_v0.7',
            label='Trendfolge ATR',
            description='Folgt bestehenden Trends: Preis ueber/unter SMA50, SMA20-Richtung, ATR-basierter Stop und Ziel.',
            family='trend_following',
            min_confidence=65,
            max_risk_score=70,
            default_max_hold_bars=48,
            default_params={'stop_atr': 1.5, 'target_atr': 3.0, 'max_rsi_long': 75, 'min_rsi_short': 25},
            optimization_grid={'stop_atr': [1.2, 1.5, 1.8], 'target_atr': [2.4, 3.0, 3.6], 'min_confidence_score': [58, 65, 72], 'max_hold_bars': [24, 48, 72]},
        ),
        'pullback_ema_v0.7': StrategyDefinition(
            name='pullback_ema_v0.7',
            label='Pullback EMA21',
            description='Sucht Ruecksetzer in Richtung des Haupttrends nahe EMA21 mit moderatem RSI.',
            family='pullback',
            min_confidence=58,
            max_risk_score=72,
            default_max_hold_bars=36,
            default_params={'max_ema_distance_atr': 1.25, 'rsi_long_min': 38, 'rsi_long_max': 63, 'rsi_short_min': 37, 'rsi_short_max': 62, 'stop_atr': 1.2, 'target_atr': 2.6},
            optimization_grid={'max_ema_distance_atr': [0.8, 1.25, 1.8], 'stop_atr': [1.0, 1.2, 1.5], 'target_atr': [2.2, 2.6, 3.0], 'min_confidence_score': [52, 58, 65], 'max_hold_bars': [24, 36, 60]},
        ),
        'breakout_range_v0.7': StrategyDefinition(
            name='breakout_range_v0.7',
            label='Breakout Range',
            description='Handelt Ausbrueche ueber/unter die 20-Kerzen-Range mit optionaler Volumenbestaetigung.',
            family='breakout',
            min_confidence=60,
            max_risk_score=76,
            default_max_hold_bars=32,
            default_params={'stop_atr': 1.1, 'target_atr': 2.4, 'require_volume': True, 'min_trend_strength_long': 70, 'max_trend_strength_short': 35},
            optimization_grid={'stop_atr': [0.9, 1.1, 1.4], 'target_atr': [2.0, 2.4, 3.0], 'require_volume': [True, False], 'min_confidence_score': [55, 60, 68], 'max_hold_bars': [16, 32, 48]},
        ),
        'mean_reversion_rsi_v0.7': StrategyDefinition(
            name='mean_reversion_rsi_v0.7',
            label='Mean Reversion RSI',
            description='Antizyklischer Rebound-Ansatz bei ueberverkauftem/ueberkauftem RSI mit Ziel Richtung EMA21.',
            family='mean_reversion',
            min_confidence=35,
            max_risk_score=82,
            default_max_hold_bars=24,
            default_params={'long_rsi_max': 34, 'short_rsi_min': 72, 'stop_atr': 1.1, 'target_atr': 2.2},
            optimization_grid={'long_rsi_max': [28, 32, 36], 'short_rsi_min': [68, 72, 76], 'stop_atr': [0.9, 1.1, 1.4], 'target_atr': [1.8, 2.2, 2.8], 'max_hold_bars': [12, 24, 36]},
        ),
    }

    LEGACY_ALIASES: dict[str, str] = {
        'trend_atr_v0.6': 'trend_atr_v0.7',
        'pullback_ema_v0.6': 'pullback_ema_v0.7',
        'breakout_range_v0.6': 'breakout_range_v0.7',
        'mean_reversion_rsi_v0.6': 'mean_reversion_rsi_v0.7',
    }

    def resolve_strategy_name(self, strategy_name: str | None) -> str:
        name = strategy_name or self.DEFAULT_STRATEGY
        return self.LEGACY_ALIASES.get(name, name)

    def list_strategies(self) -> list[dict[str, Any]]:
        return [definition.__dict__ for definition in self.STRATEGIES.values()]

    def get_parameter_grid(self, strategy_name: str) -> dict[str, list[Any]]:
        resolved = self.resolve_strategy_name(strategy_name)
        definition = self.STRATEGIES.get(resolved)
        if not definition:
            raise ValueError(f'Unknown strategy: {strategy_name}')
        return definition.optimization_grid

    def _params(self, strategy_name: str, overrides: dict[str, Any] | None) -> dict[str, Any]:
        resolved = self.resolve_strategy_name(strategy_name)
        definition = self.STRATEGIES[resolved]
        params = dict(definition.default_params)
        if overrides:
            params.update({key: value for key, value in overrides.items() if value is not None})
        return params

    def create_signal(
        self,
        prediction: dict,
        indicators: dict,
        strategy_name: str | None = None,
        strategy_params: dict[str, Any] | None = None,
    ) -> dict | None:
        strategy_name = self.resolve_strategy_name(strategy_name)
        handlers: dict[str, Callable[[dict, dict, dict[str, Any]], dict | None]] = {
            'trend_atr_v0.7': self._trend_atr,
            'pullback_ema_v0.7': self._pullback_ema,
            'breakout_range_v0.7': self._breakout_range,
            'mean_reversion_rsi_v0.7': self._mean_reversion_rsi,
        }
        handler = handlers.get(strategy_name)
        if handler is None:
            raise ValueError(f'Unknown strategy: {strategy_name}')
        params = self._params(strategy_name, strategy_params)
        signal = handler(prediction, indicators, params)
        if signal:
            signal['strategy'] = strategy_name
            signal['strategy_params'] = params
        return signal

    def _trend_atr(self, prediction: dict, indicators: dict, params: dict[str, Any]) -> dict | None:
        if prediction['direction'] == 'long':
            if not indicators.get('price_above_sma50') or not indicators.get('sma20_above_sma50'):
                return None
            if indicators.get('rsi', 50) > float(params.get('max_rsi_long', 75)):
                return None
            return self._build_signal('long', prediction, indicators, stop_atr=float(params['stop_atr']), target_atr=float(params['target_atr']), reason_prefix='Trendfolge')

        if prediction['direction'] == 'short':
            if indicators.get('price_above_sma50') or indicators.get('sma20_above_sma50'):
                return None
            if indicators.get('rsi', 50) < float(params.get('min_rsi_short', 25)):
                return None
            return self._build_signal('short', prediction, indicators, stop_atr=float(params['stop_atr']), target_atr=float(params['target_atr']), reason_prefix='Trendfolge')

        return None

    def _pullback_ema(self, prediction: dict, indicators: dict, params: dict[str, Any]) -> dict | None:
        entry = float(indicators['latest_close'])
        ema21 = float(indicators.get('ema21') or entry)
        atr = max(float(indicators.get('atr') or 0.0), 1e-9)
        distance_to_ema_atr = abs(entry - ema21) / atr
        rsi = float(indicators.get('rsi') or 50.0)

        if distance_to_ema_atr > float(params.get('max_ema_distance_atr', 1.25)):
            return None

        if prediction['direction'] == 'long':
            if not indicators.get('price_above_sma50'):
                return None
            if not float(params.get('rsi_long_min', 38)) <= rsi <= float(params.get('rsi_long_max', 63)):
                return None
            return self._build_signal('long', prediction, indicators, stop_atr=float(params['stop_atr']), target_atr=float(params['target_atr']), reason_prefix='Pullback EMA21')

        if prediction['direction'] == 'short':
            if indicators.get('price_above_sma50'):
                return None
            if not float(params.get('rsi_short_min', 37)) <= rsi <= float(params.get('rsi_short_max', 62)):
                return None
            return self._build_signal('short', prediction, indicators, stop_atr=float(params['stop_atr']), target_atr=float(params['target_atr']), reason_prefix='Pullback EMA21')

        return None

    def _breakout_range(self, prediction: dict, indicators: dict, params: dict[str, Any]) -> dict | None:
        entry = float(indicators['latest_close'])
        previous_close = float(indicators.get('previous_close') or entry)
        previous_high_20 = float(indicators.get('previous_high_20') or entry)
        previous_low_20 = float(indicators.get('previous_low_20') or entry)
        volume_ok = bool(indicators.get('volume_confirmation'))
        trend_strength = float(indicators.get('trend_strength') or 50.0)
        require_volume = bool(params.get('require_volume', True))

        if prediction['direction'] == 'long':
            broke_out = entry > previous_high_20 and previous_close <= previous_high_20
            if not broke_out and not (entry > previous_high_20 and trend_strength >= float(params.get('min_trend_strength_long', 70))):
                return None
            if require_volume and not volume_ok:
                return None
            return self._build_signal('long', prediction, indicators, stop_atr=float(params['stop_atr']), target_atr=float(params['target_atr']), reason_prefix='Breakout Range')

        if prediction['direction'] == 'short':
            broke_down = entry < previous_low_20 and previous_close >= previous_low_20
            if not broke_down and not (entry < previous_low_20 and trend_strength <= float(params.get('max_trend_strength_short', 35))):
                return None
            if require_volume and not volume_ok:
                return None
            return self._build_signal('short', prediction, indicators, stop_atr=float(params['stop_atr']), target_atr=float(params['target_atr']), reason_prefix='Breakout Range')

        return None

    def _mean_reversion_rsi(self, prediction: dict, indicators: dict, params: dict[str, Any]) -> dict | None:
        entry = float(indicators['latest_close'])
        ema21 = float(indicators.get('ema21') or entry)
        atr = max(float(indicators.get('atr') or 0.0), 1e-9)
        rsi = float(indicators.get('rsi') or 50.0)
        target_atr = float(params.get('target_atr', 2.2))
        stop_atr = float(params.get('stop_atr', 1.1))

        if rsi <= float(params.get('long_rsi_max', 34)):
            stop_loss = entry - (stop_atr * atr)
            technical_target = max(ema21, entry + (target_atr * atr))
            return self._build_custom_signal(
                side='long',
                prediction=prediction,
                entry=entry,
                stop_loss=stop_loss,
                take_profit=technical_target,
                reason_prefix='Mean Reversion RSI ueberverkauft',
            )

        if rsi >= float(params.get('short_rsi_min', 72)):
            stop_loss = entry + (stop_atr * atr)
            technical_target = min(ema21, entry - (target_atr * atr))
            return self._build_custom_signal(
                side='short',
                prediction=prediction,
                entry=entry,
                stop_loss=stop_loss,
                take_profit=technical_target,
                reason_prefix='Mean Reversion RSI ueberkauft',
            )

        return None

    def _build_signal(
        self,
        side: str,
        prediction: dict,
        indicators: dict,
        stop_atr: float,
        target_atr: float,
        reason_prefix: str,
    ) -> dict | None:
        entry = float(indicators['latest_close'])
        atr = max(float(indicators.get('atr') or 0.0), 1e-9)
        if side == 'long':
            stop_loss = entry - (stop_atr * atr)
            take_profit = entry + (target_atr * atr)
        else:
            stop_loss = entry + (stop_atr * atr)
            take_profit = entry - (target_atr * atr)
        return self._build_custom_signal(side, prediction, entry, stop_loss, take_profit, reason_prefix)

    def _build_custom_signal(
        self,
        side: str,
        prediction: dict,
        entry: float,
        stop_loss: float,
        take_profit: float,
        reason_prefix: str,
    ) -> dict | None:
        if entry <= 0:
            return None
        if side == 'long':
            risk = entry - stop_loss
            reward = take_profit - entry
        else:
            risk = stop_loss - entry
            reward = entry - take_profit
        crv = reward / risk if risk > 0 else 0.0
        if crv < 1.8:
            return None
        return {
            'signal_type': side,
            'signal_score': prediction['confidence_score'],
            'entry_price': round(entry, 6),
            'stop_loss': round(stop_loss, 6),
            'take_profit': round(take_profit, 6),
            'crv': round(crv, 2),
            'reason': f'{reason_prefix}: {prediction.get("explanation", "")}',
        }
