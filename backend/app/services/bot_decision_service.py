from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class BotDecision:
    allowed: bool
    mode: str
    reason: str
    decision_score: float
    model_source: str
    ml_direction: str | None = None
    ml_probability: float | None = None
    ml_model_id: str | None = None
    degraded: bool = False
    details: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            'allowed': self.allowed,
            'mode': self.mode,
            'reason': self.reason,
            'decision_score': round(float(self.decision_score), 6),
            'model_source': self.model_source,
            'ml_direction': self.ml_direction,
            'ml_probability': self.ml_probability,
            'ml_model_id': self.ml_model_id,
            'degraded': self.degraded,
            'details': self.details or {},
        }


class BotDecisionService:
    """Decision gate for v0.9.

    The strategy and risk engine still do the heavy lifting. The v0.9 decision
    layer decides whether a rule signal may pass as-is, whether an ML model must
    agree with it, or whether the system should fall back to rule-only because
    the selected ML model looks degraded.
    """

    VALID_MODES = {'rule', 'ml', 'ensemble'}

    def decide(
        self,
        mode: str,
        signal: dict[str, Any] | None,
        rule_prediction: dict[str, Any],
        ml_asset_result: dict[str, Any] | None,
        min_ml_probability: float = 0.52,
        min_model_profit_factor: float = 1.0,
        min_model_win_rate: float = 45.0,
        allow_degraded_fallback: bool = True,
    ) -> BotDecision:
        normalized_mode = (mode or 'rule').lower().strip()
        if normalized_mode not in self.VALID_MODES:
            return BotDecision(
                allowed=False,
                mode=normalized_mode,
                reason=f'Unknown decision mode: {mode}',
                decision_score=0.0,
                model_source='invalid',
            )

        if signal is None:
            return BotDecision(
                allowed=False,
                mode=normalized_mode,
                reason='No strategy signal was generated.',
                decision_score=0.0,
                model_source='strategy',
            )

        rule_direction = str(rule_prediction.get('direction') or 'neutral')
        signal_side = str(signal.get('signal_type') or 'neutral')
        rule_probability = self._rule_probability(rule_prediction, signal_side)
        rule_confidence = float(rule_prediction.get('confidence_score') or signal.get('signal_score') or 0.0)

        if normalized_mode == 'rule':
            return BotDecision(
                allowed=True,
                mode='rule',
                reason='Rule strategy accepted; ML filter not required.',
                decision_score=rule_confidence,
                model_source='rule',
                details={
                    'rule_direction': rule_direction,
                    'rule_probability': rule_probability,
                    'rule_confidence': rule_confidence,
                },
            )

        if ml_asset_result is None:
            if allow_degraded_fallback and normalized_mode == 'ensemble':
                return BotDecision(
                    allowed=True,
                    mode='ensemble_fallback_rule',
                    reason='No ML model available; ensemble fell back to rule-only mode.',
                    decision_score=rule_confidence,
                    model_source='rule_fallback',
                    degraded=True,
                    details={'fallback_reason': 'ml_unavailable'},
                )
            return BotDecision(
                allowed=False,
                mode=normalized_mode,
                reason='ML model unavailable. Train a model first or use rule mode.',
                decision_score=0.0,
                model_source='ml_unavailable',
            )

        ml_prediction = ml_asset_result.get('ml_prediction') or {}
        ml_direction = str(ml_prediction.get('prediction_direction') or 'neutral')
        probabilities = ml_prediction.get('probabilities') or {}
        ml_probability = float(probabilities.get(signal_side) or 0.0)
        ml_model_id = ml_prediction.get('model_id')
        metadata = ml_prediction.get('metadata') or {}
        health = self.model_health(metadata, min_model_profit_factor, min_model_win_rate)

        if not health['healthy']:
            if allow_degraded_fallback and normalized_mode == 'ensemble':
                return BotDecision(
                    allowed=True,
                    mode='ensemble_fallback_rule',
                    reason=f'ML model degraded ({health["reason"]}); ensemble fell back to rule-only mode.',
                    decision_score=rule_confidence,
                    model_source='rule_fallback',
                    ml_direction=ml_direction,
                    ml_probability=ml_probability,
                    ml_model_id=ml_model_id,
                    degraded=True,
                    details={'model_health': health, 'ml_probabilities': probabilities},
                )
            return BotDecision(
                allowed=False,
                mode=normalized_mode,
                reason=f'ML model degraded: {health["reason"]}',
                decision_score=0.0,
                model_source='ml_degraded',
                ml_direction=ml_direction,
                ml_probability=ml_probability,
                ml_model_id=ml_model_id,
                degraded=True,
                details={'model_health': health, 'ml_probabilities': probabilities},
            )

        if normalized_mode == 'ml':
            allowed = ml_direction == signal_side and ml_probability >= min_ml_probability
            return BotDecision(
                allowed=allowed,
                mode='ml',
                reason='ML direction accepted.' if allowed else 'ML direction/probability did not confirm the strategy signal.',
                decision_score=ml_probability * 100,
                model_source='ml',
                ml_direction=ml_direction,
                ml_probability=round(ml_probability, 6),
                ml_model_id=ml_model_id,
                details={
                    'signal_side': signal_side,
                    'min_ml_probability': min_ml_probability,
                    'model_health': health,
                    'ml_probabilities': probabilities,
                },
            )

        ml_agrees = ml_direction == signal_side and ml_probability >= min_ml_probability
        rule_agrees = rule_direction == signal_side and rule_probability >= 0.5
        ensemble_score = (rule_confidence * 0.55) + (ml_probability * 100 * 0.45)
        allowed = ml_agrees and rule_agrees
        return BotDecision(
            allowed=allowed,
            mode='ensemble',
            reason='Rule and ML agree.' if allowed else 'Rule and ML did not agree strongly enough.',
            decision_score=ensemble_score,
            model_source='ensemble',
            ml_direction=ml_direction,
            ml_probability=round(ml_probability, 6),
            ml_model_id=ml_model_id,
            details={
                'signal_side': signal_side,
                'rule_direction': rule_direction,
                'rule_probability': rule_probability,
                'rule_confidence': rule_confidence,
                'ml_agrees': ml_agrees,
                'rule_agrees': rule_agrees,
                'min_ml_probability': min_ml_probability,
                'model_health': health,
                'ml_probabilities': probabilities,
            },
        )

    def model_health(
        self,
        metadata: dict[str, Any],
        min_profit_factor: float = 1.0,
        min_win_rate: float = 45.0,
    ) -> dict[str, Any]:
        trading_metrics = metadata.get('trading_metrics') or {}
        model_id = metadata.get('model_id')
        trades = int(trading_metrics.get('trades') or 0)
        win_rate = float(trading_metrics.get('win_rate_percent') or 0.0)
        profit_factor_value = trading_metrics.get('profit_factor')
        profit_factor = None if profit_factor_value is None else float(profit_factor_value)

        reasons: list[str] = []
        if trades < 5:
            reasons.append('too_few_validation_trades')
        if profit_factor is not None and profit_factor < min_profit_factor:
            reasons.append('profit_factor_below_threshold')
        if trades >= 5 and win_rate < min_win_rate:
            reasons.append('win_rate_below_threshold')

        return {
            'model_id': model_id,
            'healthy': len(reasons) == 0,
            'reason': ','.join(reasons) if reasons else 'ok',
            'trades': trades,
            'win_rate_percent': round(win_rate, 4),
            'profit_factor': profit_factor,
            'thresholds': {
                'min_profit_factor': min_profit_factor,
                'min_win_rate_percent': min_win_rate,
            },
        }

    def _rule_probability(self, prediction: dict[str, Any], side: str) -> float:
        if side == 'long':
            return float(prediction.get('probability_long') or 0.0)
        if side == 'short':
            return float(prediction.get('probability_short') or 0.0)
        return float(prediction.get('probability_neutral') or 0.0)
