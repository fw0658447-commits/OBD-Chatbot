class AIPredictionService:
    MODEL_VERSION = 'ai-rule-v0.2.0'

    def predict(self, symbol: str, timeframe: str, indicators: dict) -> dict:
        score = self._calculate_signal_score(indicators)
        risk_score = self._calculate_risk_score(indicators)
        probability_long = self._score_to_long_probability(score)
        probability_short = self._score_to_short_probability(score)
        probability_neutral = max(0.0, round(1.0 - probability_long - probability_short, 4))
        direction = self._get_direction(probability_long, probability_short, probability_neutral)
        expected_return = self._expected_return(score, indicators)

        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'horizon': f'next_{timeframe}',
            'direction': direction,
            'probability_long': probability_long,
            'probability_short': probability_short,
            'probability_neutral': probability_neutral,
            'expected_return_percent': expected_return,
            'confidence_score': score,
            'risk_score': risk_score,
            'model_version': self.MODEL_VERSION,
            'explanation': self._build_explanation(score, risk_score, indicators),
        }

    def _calculate_signal_score(self, indicators: dict) -> float:
        score = 0.0
        if indicators['price_above_sma50']:
            score += 15
        if indicators['sma20_above_sma50']:
            score += 15
        rsi = indicators['rsi']
        if 45 <= rsi <= 70:
            score += 15
        elif 35 <= rsi < 45:
            score += 8
        elif rsi > 75:
            score -= 10
        trend = indicators['trend_strength']
        if trend >= 70:
            score += 20
        elif trend >= 55:
            score += 10
        if indicators['volume_confirmation']:
            score += 10
        atr_percent = indicators['atr_percent']
        if atr_percent < 4:
            score += 15
        elif atr_percent > 8:
            score -= 10
        if indicators.get('last_return_percent', 0) > 0:
            score += 5
        return max(0.0, min(score, 100.0))

    def _calculate_risk_score(self, indicators: dict) -> float:
        risk = 50.0
        atr_percent = indicators['atr_percent']
        rsi = indicators['rsi']
        if atr_percent > 5:
            risk += 15
        if atr_percent > 8:
            risk += 10
        if rsi > 75:
            risk += 10
        if indicators['trend_strength'] < 45:
            risk += 10
        if atr_percent < 2:
            risk -= 10
        if indicators['volume_confirmation']:
            risk -= 5
        return max(0.0, min(risk, 100.0))

    def _score_to_long_probability(self, score: float) -> float:
        if score >= 80:
            return 0.70
        if score >= 70:
            return 0.64
        if score >= 60:
            return 0.58
        if score >= 50:
            return 0.52
        return 0.40

    def _score_to_short_probability(self, score: float) -> float:
        if score <= 30:
            return 0.60
        if score <= 40:
            return 0.52
        return 0.18

    def _get_direction(self, long_p: float, short_p: float, neutral_p: float) -> str:
        probabilities = {'long': long_p, 'short': short_p, 'neutral': neutral_p}
        return max(probabilities, key=probabilities.get)

    def _expected_return(self, score: float, indicators: dict) -> float:
        atr = indicators['atr_percent']
        if score >= 75:
            return round(atr * 1.2, 2)
        if score >= 60:
            return round(atr * 0.7, 2)
        if score <= 35:
            return round(-atr * 0.7, 2)
        return 0.0

    def _build_explanation(self, score: float, risk_score: float, indicators: dict) -> str:
        return (
            f'Das regelbasierte KI-Modul bewertet das Setup mit {score:.0f}/100 Confidence. '
            f'Der Risk Score liegt bei {risk_score:.0f}/100. '
            f'RSI {indicators["rsi"]:.1f}, ATR {indicators["atr_percent"]:.2f} Prozent, '
            f'Trendstaerke {indicators["trend_strength"]:.0f}/100.'
        )
