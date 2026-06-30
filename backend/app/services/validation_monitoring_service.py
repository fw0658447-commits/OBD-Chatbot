from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from app.config import settings
from app.repositories.trading_repository import trading_repository


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            cleaned = value.replace('Z', '+00:00')
            dt = datetime.fromisoformat(cleaned)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


class ValidationMonitoringService:
    """Operational validation layer for serious paper trading.

    The goal is not to promise profitability. The goal is to stop the user from
    trusting a strategy before it has enough paper-trading evidence and stable
    data quality.
    """

    def __init__(self, repository=trading_repository):
        self.repository = repository

    def validation_gates(self, strategy_name: str | None = None, decision_mode: str | None = None) -> dict[str, Any]:
        config = self._config()
        thresholds = self._thresholds(config)
        performance = self._filtered_performance(strategy_name=strategy_name, decision_mode=decision_mode)
        latest_quality = self._latest_quality()
        alerts = self.alerts(strategy_name=strategy_name, decision_mode=decision_mode, include_items=False)

        gates = []
        gates.append(self._gate(
            name='minimum_closed_trades',
            passed=performance['closed_orders'] >= thresholds['min_closed_trades'],
            actual=performance['closed_orders'],
            required=thresholds['min_closed_trades'],
            severity='blocking',
            message='Mindestens geschlossene Paper-Trades sind erforderlich, bevor eine Strategie als belastbar gilt.',
        ))
        gates.append(self._gate(
            name='profit_factor',
            passed=(performance['profit_factor'] or 0.0) >= thresholds['min_profit_factor'],
            actual=performance['profit_factor'],
            required=thresholds['min_profit_factor'],
            severity='blocking',
            message='Profit Factor muss nach Kostenmodell oberhalb der Mindestschwelle liegen.',
        ))
        gates.append(self._gate(
            name='win_rate',
            passed=performance['win_rate_percent'] >= thresholds['min_win_rate_percent'],
            actual=performance['win_rate_percent'],
            required=thresholds['min_win_rate_percent'],
            severity='warning',
            message='Winrate ist kein alleiniger Erfolgsindikator, darf aber nicht zu schwach sein.',
        ))
        gates.append(self._gate(
            name='max_drawdown',
            passed=performance['max_drawdown_percent'] <= thresholds['max_drawdown_percent'],
            actual=performance['max_drawdown_percent'],
            required=f"<= {thresholds['max_drawdown_percent']}",
            severity='blocking',
            message='Maximaler Drawdown muss innerhalb der Freigabegrenze bleiben.',
        ))
        gates.append(self._gate(
            name='expectancy',
            passed=performance['expectancy_per_trade'] > thresholds['min_expectancy_per_trade'],
            actual=performance['expectancy_per_trade'],
            required=f"> {thresholds['min_expectancy_per_trade']}",
            severity='warning',
            message='Erwartungswert pro Trade sollte nach Kosten positiv sein.',
        ))
        gates.append(self._gate(
            name='data_quality',
            passed=bool(latest_quality and latest_quality.get('trade_allowed') and _to_float(latest_quality.get('quality_score')) >= thresholds['min_data_quality_score']),
            actual=(latest_quality or {}).get('quality_score'),
            required=thresholds['min_data_quality_score'],
            severity='blocking',
            message='Letzter Datenqualitaetsbericht muss trade-allowed sein und die Mindestqualitaet erreichen.',
        ))
        gates.append(self._gate(
            name='critical_alerts',
            passed=alerts['critical_count'] == 0,
            actual=alerts['critical_count'],
            required=0,
            severity='blocking',
            message='Keine kritischen Monitoring-Alerts duerfen aktiv sein.',
        ))

        blocking_failed = [gate for gate in gates if gate['severity'] == 'blocking' and not gate['passed']]
        warning_failed = [gate for gate in gates if gate['severity'] == 'warning' and not gate['passed']]
        released = not blocking_failed

        return {
            'status': 'released' if released else 'not_released',
            'released_for_paper_automation': released,
            'strategy_name': strategy_name,
            'decision_mode': decision_mode,
            'thresholds': thresholds,
            'performance': performance,
            'latest_data_quality': latest_quality,
            'gates': gates,
            'blocking_failures': blocking_failed,
            'warning_failures': warning_failed,
            'alerts_summary': {key: alerts[key] for key in ['status', 'critical_count', 'warning_count', 'info_count']},
            'enforcement_enabled': bool(config.get('enforce_validation_gate')),
            'recommendation': self._release_recommendation(released, blocking_failed, warning_failed),
            'persistence': self._persistence(),
        }

    def daily_report(self, lookback_hours: int = 24) -> dict[str, Any]:
        since = datetime.now(timezone.utc) - timedelta(hours=max(1, lookback_hours))
        orders = self.repository.list_paper_orders(status=None, limit=5000) if self.repository.available else []
        risk_events = self.repository.list_risk_events(limit=500) if self.repository.available else []
        audits = self.repository.list_decision_audits(limit=1000) if self.repository.available else []
        quality = self.repository.list_data_quality_reports(limit=200) if self.repository.available else []
        scheduler = self.repository.list_scheduler_runs(limit=100) if self.repository.available else []

        recent_orders = [item for item in orders if self._is_recent(item.get('closed_at') or item.get('opened_at'), since)]
        closed_recent = [item for item in recent_orders if item.get('status') != 'open']
        open_orders = [item for item in orders if item.get('status') == 'open']
        recent_events = [item for item in risk_events if self._is_recent(item.get('created_at'), since)]
        recent_audits = [item for item in audits if self._is_recent(item.get('created_at'), since)]
        recent_quality = [item for item in quality if self._is_recent(item.get('created_at'), since)]
        recent_scheduler = [item for item in scheduler if self._is_recent(item.get('created_at'), since)]

        pnl_values = [_to_float(item.get('pnl_amount')) for item in closed_recent]
        total_pnl = sum(pnl_values)
        wins = [value for value in pnl_values if value > 0]
        losses = [value for value in pnl_values if value < 0]
        gross_profit = sum(wins)
        gross_loss_abs = abs(sum(losses))

        status_counter = Counter(str(item.get('status') or 'unknown') for item in recent_orders)
        audit_counter = Counter('allowed' if item.get('allowed') else 'blocked' for item in recent_audits)
        risk_counter = Counter(str(item.get('severity') or 'unknown') for item in recent_events)
        mode_counter = Counter(str(item.get('decision_mode') or 'unknown') for item in recent_orders)

        alerts = self.alerts(include_items=True)
        validation = self.validation_gates()

        return {
            'status': 'ok',
            'lookback_hours': lookback_hours,
            'period_start': since.isoformat(),
            'period_end': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'orders_total': len(recent_orders),
                'closed_orders': len(closed_recent),
                'open_orders_total': len(open_orders),
                'total_pnl': round(total_pnl, 2),
                'win_rate_percent': round(len(wins) / len(closed_recent) * 100, 2) if closed_recent else 0.0,
                'profit_factor': round(gross_profit / gross_loss_abs, 4) if gross_loss_abs else None,
                'average_pnl': round(mean(pnl_values), 2) if pnl_values else 0.0,
                'risk_events': len(recent_events),
                'decision_audits': len(recent_audits),
                'data_quality_reports': len(recent_quality),
                'scheduler_runs': len(recent_scheduler),
            },
            'breakdowns': {
                'order_status': dict(status_counter),
                'decision_audits': dict(audit_counter),
                'risk_event_severity': dict(risk_counter),
                'decision_mode': dict(mode_counter),
            },
            'latest_data_quality': recent_quality[0] if recent_quality else self._latest_quality(),
            'recent_risk_events': recent_events[:20],
            'recent_orders': recent_orders[:25],
            'alerts': alerts,
            'validation': validation,
            'persistence': self._persistence(),
        }

    def alerts(self, strategy_name: str | None = None, decision_mode: str | None = None, include_items: bool = True) -> dict[str, Any]:
        config = self._config()
        thresholds = self._thresholds(config)
        performance = self._filtered_performance(strategy_name=strategy_name, decision_mode=decision_mode)
        latest_quality = self._latest_quality()
        risk_events = self.repository.list_risk_events(limit=200) if self.repository.available else []
        recent_critical_events = [event for event in risk_events if str(event.get('severity')) == 'critical'][:10]
        items: list[dict[str, Any]] = []

        if not self.repository.available:
            items.append(self._alert('critical', 'persistence_unavailable', 'PostgreSQL ist nicht erreichbar. Reales Paper-Trading sollte nur mit Persistenz laufen.'))
        if config.get('kill_switch_active'):
            items.append(self._alert('critical', 'kill_switch_active', 'Kill-Switch ist aktiv. Bot-Zyklen sind blockiert.'))
        if performance['closed_orders'] < thresholds['min_closed_trades']:
            items.append(self._alert('warning', 'insufficient_history', f"Nur {performance['closed_orders']} geschlossene Trades. Mindesthistorie: {thresholds['min_closed_trades']}."))
        if performance['closed_orders'] >= max(10, int(thresholds['min_closed_trades'] * 0.25)):
            if (performance['profit_factor'] or 0) < thresholds['min_profit_factor']:
                items.append(self._alert('critical', 'profit_factor_below_gate', f"Profit Factor {performance['profit_factor']} liegt unter {thresholds['min_profit_factor']}."))
            if performance['max_drawdown_percent'] > thresholds['max_drawdown_percent']:
                items.append(self._alert('critical', 'drawdown_above_gate', f"Drawdown {performance['max_drawdown_percent']}% liegt ueber {thresholds['max_drawdown_percent']}%."))
        if latest_quality is None:
            items.append(self._alert('warning', 'missing_data_quality', 'Noch kein Datenqualitaetsreport vorhanden.'))
        elif not latest_quality.get('trade_allowed') or _to_float(latest_quality.get('quality_score')) < thresholds['min_data_quality_score']:
            items.append(self._alert('critical', 'data_quality_below_gate', f"Letzte Datenqualitaet {latest_quality.get('quality_score')} ist nicht ausreichend."))
        for event in recent_critical_events:
            items.append(self._alert('critical', 'recent_critical_risk_event', str(event.get('message') or event.get('event_type')), {'event': event}))

        counts = Counter(item['severity'] for item in items)
        status = 'critical' if counts.get('critical', 0) else ('warning' if counts.get('warning', 0) else 'ok')
        return {
            'status': status,
            'critical_count': counts.get('critical', 0),
            'warning_count': counts.get('warning', 0),
            'info_count': counts.get('info', 0),
            'items': items if include_items else [],
            'persistence': self._persistence(),
        }

    def strategy_matrix(self) -> dict[str, Any]:
        orders = self.repository.list_paper_orders(status=None, limit=10000) if self.repository.available else []
        buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for order in orders:
            if order.get('status') == 'open':
                continue
            details = order.get('decision_details') or {}
            strategy = None
            if isinstance(details, dict):
                strategy = details.get('strategy') or details.get('strategy_name')
            # The strategy is not always stored on order rows in older DBs; fallback to unknown.
            key = (str(strategy or 'unknown'), str(order.get('decision_mode') or 'rule'))
            buckets[key].append(order)

        rows = []
        for (strategy, mode), items in buckets.items():
            rows.append(self._metrics_from_orders(items) | {'strategy_name': strategy, 'decision_mode': mode})
        rows.sort(key=lambda item: (item.get('profit_factor') or 0, item.get('closed_orders') or 0), reverse=True)
        return {'items': rows, 'persistence': self._persistence()}

    def system_report(self) -> dict[str, Any]:
        return {
            'status': 'ok',
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'readiness': self.validation_gates(),
            'daily_report': self.daily_report(lookback_hours=24),
            'alerts': self.alerts(),
            'strategy_matrix': self.strategy_matrix(),
            'recommendation': 'Nur Paper-Trading nutzen, bis alle Blocking-Gates erfuellt sind und mindestens 100 geschlossene Trades vorliegen.',
        }

    def _filtered_performance(self, strategy_name: str | None = None, decision_mode: str | None = None) -> dict[str, Any]:
        if not self.repository.available:
            return self._empty_metrics()
        orders = self.repository.list_paper_orders(status=None, limit=10000)
        filtered = []
        for order in orders:
            if order.get('status') == 'open':
                continue
            if decision_mode and str(order.get('decision_mode') or '').lower() != decision_mode.lower():
                continue
            # Older orders may not store strategy; do not filter by strategy unless explicitly present.
            if strategy_name:
                details = order.get('decision_details') or {}
                order_strategy = details.get('strategy') if isinstance(details, dict) else None
                if order_strategy and str(order_strategy) != strategy_name:
                    continue
            filtered.append(order)
        return self._metrics_from_orders(filtered)

    def _metrics_from_orders(self, orders: list[dict[str, Any]]) -> dict[str, Any]:
        closed = [order for order in orders if order.get('status') != 'open']
        wins = [order for order in closed if _to_float(order.get('pnl_amount')) > 0]
        losses = [order for order in closed if _to_float(order.get('pnl_amount')) < 0]
        gross_profit = sum(_to_float(order.get('pnl_amount')) for order in wins)
        gross_loss = sum(_to_float(order.get('pnl_amount')) for order in losses)
        closed_count = len(closed)
        total_pnl = gross_profit + gross_loss
        equity = 10000.0
        peak = equity
        max_drawdown = 0.0
        for order in sorted(closed, key=lambda item: str(item.get('closed_at') or item.get('opened_at') or '')):
            equity += _to_float(order.get('pnl_amount'))
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        return {
            'closed_orders': closed_count,
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate_percent': round(len(wins) / closed_count * 100, 2) if closed_count else 0.0,
            'gross_profit': round(gross_profit, 2),
            'gross_loss': round(gross_loss, 2),
            'profit_factor': round(gross_profit / abs(gross_loss), 4) if gross_loss else None,
            'total_realized_pnl': round(total_pnl, 2),
            'expectancy_per_trade': round(total_pnl / closed_count, 2) if closed_count else 0.0,
            'max_drawdown_percent': round(max_drawdown / peak * 100, 2) if peak else 0.0,
        }

    def _empty_metrics(self) -> dict[str, Any]:
        return {
            'closed_orders': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate_percent': 0.0,
            'gross_profit': 0.0,
            'gross_loss': 0.0,
            'profit_factor': None,
            'total_realized_pnl': 0.0,
            'expectancy_per_trade': 0.0,
            'max_drawdown_percent': 0.0,
        }

    def _config(self) -> dict[str, Any]:
        try:
            from app.services.bot_runtime_service import bot_runtime_service
            return bot_runtime_service.get_config()
        except Exception:
            return {}

    def _thresholds(self, config: dict[str, Any]) -> dict[str, Any]:
        return {
            'min_closed_trades': int(config.get('min_closed_trades_for_release') or settings.min_closed_trades_for_release),
            'min_profit_factor': float(config.get('min_profit_factor_for_release') or settings.min_profit_factor_for_release),
            'min_win_rate_percent': float(config.get('min_win_rate_for_release') or settings.min_win_rate_for_release),
            'max_drawdown_percent': float(config.get('max_drawdown_percent_for_release') or settings.max_drawdown_percent_for_release),
            'min_expectancy_per_trade': float(config.get('min_expectancy_per_trade_for_release') or settings.min_expectancy_per_trade_for_release),
            'min_data_quality_score': float(config.get('min_data_quality_score_for_release') or settings.min_data_quality_score),
        }

    def _latest_quality(self) -> dict[str, Any] | None:
        if not self.repository.available:
            return None
        reports = self.repository.list_data_quality_reports(limit=1)
        return reports[0] if reports else None

    def _gate(self, name: str, passed: bool, actual: Any, required: Any, severity: str, message: str) -> dict[str, Any]:
        return {
            'name': name,
            'passed': bool(passed),
            'actual': actual,
            'required': required,
            'severity': severity,
            'message': message,
        }

    def _alert(self, severity: str, code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            'severity': severity,
            'code': code,
            'message': message,
            'details': details or {},
            'created_at': datetime.now(timezone.utc).isoformat(),
        }

    def _release_recommendation(self, released: bool, blocking: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> str:
        if released and not warnings:
            return 'Strategie ist fuer kontrollierte Paper-Automation freigegeben. Echtgeldhandel bleibt gesperrt.'
        if released:
            return 'Keine Blocking-Gates verletzt, aber Warnungen bleiben aktiv. Paper-Automation nur mit kleinen Risiko-Limits.'
        failed = ', '.join(gate['name'] for gate in blocking)
        return f'Nicht freigegeben. Zuerst diese Gates verbessern: {failed}.'

    def _is_recent(self, value: Any, since: datetime) -> bool:
        dt = _parse_dt(value)
        return bool(dt and dt >= since)

    def _persistence(self) -> str:
        return 'postgres' if self.repository.available else 'memory'


validation_monitoring_service = ValidationMonitoringService()
