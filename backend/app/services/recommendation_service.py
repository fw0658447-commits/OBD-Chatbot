from __future__ import annotations

from typing import Any

from app.config import settings
from app.services.ai_prediction_service import AIPredictionService
from app.services.data_quality_service import data_quality_service
from app.services.indicator_service import IndicatorService
from app.services.internet_analysis_service import internet_analysis_service
from app.services.market_data_service import get_market_data_service
from app.services.strategy_engine import StrategyEngine


class RecommendationService:
    """Produce a human-readable Long/Short/No-Trade recommendation.

    The output is a decision-support layer, not financial advice. It combines market data,
    rule-based AI prediction, strategy signal, data quality and optional online context.
    """

    def recommend(
        self,
        symbol: str,
        timeframe: str = '1h',
        strategy_name: str = StrategyEngine.DEFAULT_STRATEGY,
        include_internet: bool = True,
        limit: int = 220,
    ) -> dict[str, Any]:
        market = get_market_data_service()
        quote = market.get_quote(symbol)
        candles = market.get_candles(symbol, timeframe, limit)
        quality = data_quality_service.assess_candles(candles=candles, timeframe=timeframe, provider=quote.get('provider'))
        indicators = IndicatorService().calculate(candles)
        prediction = AIPredictionService().predict(symbol, timeframe, indicators)
        signal = StrategyEngine().create_signal(prediction=prediction, indicators=indicators, strategy_name=strategy_name)
        online = internet_analysis_service.analyze(symbol, max_items=6) if include_internet else None

        decision = self._decision(prediction, signal, quality, online)
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'strategy_name': strategy_name,
            'quote': quote,
            'decision': decision,
            'prediction': prediction,
            'signal_preview': signal,
            'data_quality': quality,
            'online_analysis': online,
            'explanation': self._explain(decision, prediction, signal, quality, online),
            'disclaimer': 'Keine Anlageberatung. Die Empfehlung ist eine regelbasierte Entscheidungsunterstuetzung fuer Paper-Trading/Analyse.',
        }

    def _decision(self, prediction: dict[str, Any], signal: dict[str, Any] | None, quality: dict[str, Any], online: dict[str, Any] | None) -> dict[str, Any]:
        blockers: list[str] = []
        reasons: list[str] = []
        risk_adjustments = 0

        quality_score = float(quality.get('score', quality.get('quality_score', 100) or 100))
        if quality_score < settings.min_data_quality_score:
            blockers.append(f'Datenqualitaet zu schwach ({quality_score:.0f}/100).')
            risk_adjustments += 20

        if prediction.get('risk_score', 100) > settings.max_risk_score:
            blockers.append(f'Risk Score zu hoch ({prediction.get("risk_score"):.0f}/100).')

        confidence = float(prediction.get('confidence_score', 0))
        if confidence < settings.min_confidence_score:
            reasons.append(f'Confidence noch unter Zielwert ({confidence:.0f}/100).')

        sentiment_score = 0.0
        if online:
            sentiment_score = float(online.get('sentiment_score') or 0.0)
            risk_flags = online.get('risk_flags') or []
            if risk_flags:
                risk_adjustments += min(20, 5 * len(risk_flags))
                reasons.extend(risk_flags[:3])
            if sentiment_score >= 0.25:
                reasons.append('Online-Sentiment unterstuetzt bullisches Szenario.')
            elif sentiment_score <= -0.25:
                reasons.append('Online-Sentiment warnt vor negativer Nachrichtenlage.')

        long_p = float(prediction.get('probability_long', 0))
        short_p = float(prediction.get('probability_short', 0))
        base_risk = float(prediction.get('risk_score', 50)) + risk_adjustments
        risk_level = self._risk_level(base_risk)

        action = 'WATCH'
        side = 'neutral'
        yes_no = 'Nein'
        size_hint = 'keine Position'

        if blockers:
            action = 'NO_TRADE'
            side = 'neutral'
            yes_no = 'Nein'
            size_hint = 'nicht handeln'
        elif signal and signal.get('signal_type') == 'long' and long_p >= 0.62 and confidence >= 65:
            action = 'LONG'
            side = 'long'
            yes_no = 'Ja' if risk_level in {'gering', 'mittel'} else 'Nur klein / Beobachten'
            size_hint = 'kleine bis normale Paper-Position' if risk_level == 'mittel' else 'kleine Paper-Position' if risk_level == 'hoch' else 'normale Paper-Position'
        elif signal and signal.get('signal_type') == 'short' and short_p >= 0.55 and confidence >= 65:
            action = 'SHORT'
            side = 'short'
            yes_no = 'Ja' if risk_level in {'gering', 'mittel'} else 'Nur klein / Beobachten'
            size_hint = 'kleine bis normale Paper-Short-Position' if risk_level == 'mittel' else 'kleine Paper-Short-Position'
        elif max(long_p, short_p) >= 0.58:
            action = 'WATCH'
            side = 'long' if long_p > short_p else 'short'
            yes_no = 'Beobachten'
            size_hint = 'erst nach bestaetigtem Signal'
        else:
            action = 'NO_TRADE'
            side = 'neutral'
            yes_no = 'Nein'
            size_hint = 'kein Setup'

        if not reasons and signal:
            reasons.append(f'Strategie-Signal {signal.get("signal_type")} mit CRV {float(signal.get("crv", 0)):.2f}.')
        if not reasons:
            reasons.append('Kein ausreichendes Signal nach aktueller Bewertungslogik.')

        return {
            'action': action,
            'side': side,
            'trade_decision': yes_no,
            'risk_level': risk_level,
            'risk_score_adjusted': round(min(base_risk, 100), 1),
            'position_size_hint': size_hint,
            'confidence_score': confidence,
            'long_probability': long_p,
            'short_probability': short_p,
            'neutral_probability': float(prediction.get('probability_neutral', 0)),
            'blockers': blockers,
            'reasons': reasons,
            'checklist': self._checklist(prediction, signal, quality, online),
        }

    def _risk_level(self, score: float) -> str:
        if score <= 40:
            return 'gering'
        if score <= 70:
            return 'mittel'
        return 'hoch'

    def _checklist(self, prediction: dict[str, Any], signal: dict[str, Any] | None, quality: dict[str, Any], online: dict[str, Any] | None) -> list[dict[str, Any]]:
        quality_score = float(quality.get('score', quality.get('quality_score', 100) or 100))
        return [
            {'name': 'Datenqualitaet', 'passed': quality_score >= settings.min_data_quality_score, 'value': f'{quality_score:.0f}/100'},
            {'name': 'Confidence', 'passed': float(prediction.get('confidence_score', 0)) >= settings.min_confidence_score, 'value': f'{float(prediction.get("confidence_score", 0)):.0f}/100'},
            {'name': 'Risk Score', 'passed': float(prediction.get('risk_score', 100)) <= settings.max_risk_score, 'value': f'{float(prediction.get("risk_score", 0)):.0f}/100'},
            {'name': 'Strategie-Signal', 'passed': signal is not None, 'value': signal.get('signal_type') if signal else 'kein Signal'},
            {'name': 'CRV', 'passed': bool(signal and float(signal.get('crv', 0)) >= settings.min_crv), 'value': f'{float(signal.get("crv", 0)):.2f}' if signal else '-'},
            {'name': 'Online-Kontext', 'passed': bool(online and online.get('online')), 'value': (online or {}).get('sentiment_label', 'nicht verbunden')},
        ]

    def _explain(self, decision: dict[str, Any], prediction: dict[str, Any], signal: dict[str, Any] | None, quality: dict[str, Any], online: dict[str, Any] | None) -> str:
        signal_text = 'kein konkretes Strategie-Signal' if not signal else f'{signal.get("signal_type").upper()}-Signal mit CRV {float(signal.get("crv", 0)):.2f}'
        online_text = 'Online-Kontext nicht verbunden' if not online or not online.get('online') else online.get('summary')
        return (
            f'Entscheidung: {decision["trade_decision"]} ({decision["action"]}), Risiko {decision["risk_level"]}. '
            f'Basis: {signal_text}, Long-Wahrscheinlichkeit {float(prediction.get("probability_long", 0))*100:.1f}%, '
            f'Short-Wahrscheinlichkeit {float(prediction.get("probability_short", 0))*100:.1f}%, '
            f'Confidence {float(prediction.get("confidence_score", 0)):.0f}/100. {online_text}'
        )


recommendation_service = RecommendationService()
