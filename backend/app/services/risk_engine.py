from dataclasses import dataclass

from app.config import settings


@dataclass
class RiskResult:
    allowed: bool
    reason: str
    quantity: float = 0.0
    max_risk_amount: float = 0.0


class RiskEngine:
    def validate(
        self,
        signal: dict,
        prediction: dict,
        portfolio_value: float,
        open_trades_count: int,
        daily_pnl_percent: float,
        limits: dict | None = None,
    ) -> RiskResult:
        limits = limits or {}
        live_trading_enabled = bool(limits.get('live_trading_enabled', settings.live_trading_enabled))
        min_crv = float(limits.get('min_crv', settings.min_crv))
        min_confidence_score = float(limits.get('min_confidence_score', settings.min_confidence_score))
        max_risk_score = float(limits.get('max_risk_score', settings.max_risk_score))
        max_open_trades = int(limits.get('max_open_trades', settings.max_open_trades))
        max_daily_loss = float(limits.get('max_daily_loss', settings.max_daily_loss))
        max_risk_per_trade = float(limits.get('max_risk_per_trade', settings.max_risk_per_trade))

        if live_trading_enabled:
            return RiskResult(False, 'Live-Trading ist in diesem MVP nicht erlaubt')
        if signal['crv'] < min_crv:
            return RiskResult(False, 'CRV zu niedrig')
        if prediction['confidence_score'] < min_confidence_score:
            return RiskResult(False, 'Confidence Score zu niedrig')
        if prediction['risk_score'] > max_risk_score:
            return RiskResult(False, 'Risk Score zu hoch')
        if open_trades_count >= max_open_trades:
            return RiskResult(False, 'Maximale Anzahl offener Trades erreicht')
        if daily_pnl_percent <= -max_daily_loss:
            return RiskResult(False, 'Tagesverlustlimit erreicht')
        if signal['entry_price'] <= 0:
            return RiskResult(False, 'Ungueltiger Einstiegskurs')

        risk_per_unit = abs(signal['entry_price'] - signal['stop_loss'])
        if risk_per_unit <= 0:
            return RiskResult(False, 'Ungueltiger Stop-Loss')

        max_risk_amount = portfolio_value * max_risk_per_trade
        quantity = max_risk_amount / risk_per_unit
        if quantity <= 0:
            return RiskResult(False, 'Positionsgroesse ungueltig')

        return RiskResult(
            allowed=True,
            reason='Paper-Trade erlaubt',
            quantity=round(quantity, 8),
            max_risk_amount=round(max_risk_amount, 2),
        )
