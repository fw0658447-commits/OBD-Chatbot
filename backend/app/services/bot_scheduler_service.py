from __future__ import annotations

from datetime import datetime, timezone
import threading
import time
from typing import Any

from app.repositories.trading_repository import trading_repository
from app.services.bot_engine import BotEngine
from app.services.bot_runtime_service import bot_runtime_service


class BotSchedulerService:
    """Very small in-process scheduler for the MVP.

    It is intentionally paper-only. For production this should move to a real
    worker queue such as Celery, RQ, Dramatiq or a Kubernetes CronJob.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_run: dict[str, Any] | None = None
        self._started_at: str | None = None

    def status(self) -> dict[str, Any]:
        config = bot_runtime_service.get_config()
        alive = bool(self._thread and self._thread.is_alive())
        return {
            'status': 'running' if alive else 'stopped',
            'thread_alive': alive,
            'started_at': self._started_at,
            'last_run': self._last_run,
            'config': config,
            'live_trading_enabled': False,
        }

    def start(self) -> dict[str, Any]:
        config = bot_runtime_service.get_config()
        if config.get('kill_switch_active'):
            return {'status': 'blocked', 'reason': 'Kill-Switch is active.', 'config': config}
        bot_runtime_service.update_config({'bot_enabled': True, 'scheduler_enabled': True})
        with self._lock:
            if self._thread and self._thread.is_alive():
                return self.status()
            self._stop_event.clear()
            self._started_at = datetime.now(timezone.utc).isoformat()
            self._thread = threading.Thread(target=self._loop, name='paper-bot-scheduler', daemon=True)
            self._thread.start()
        return self.status()

    def stop(self) -> dict[str, Any]:
        bot_runtime_service.update_config({'scheduler_enabled': False})
        self._stop_event.set()
        return self.status()

    def run_once(self, source: str = 'manual') -> dict[str, Any]:
        config = bot_runtime_service.get_config()
        if config.get('kill_switch_active'):
            result = {'status': 'blocked', 'reason': 'Kill-Switch is active.', 'config': config}
            self._persist_run(source, result)
            return result
        if not config.get('bot_enabled') and source != 'manual':
            result = {'status': 'skipped', 'reason': 'Bot is disabled.', 'config': config}
            self._persist_run(source, result)
            return result

        symbols = config.get('symbols') or []
        timeframes = config.get('timeframes') or ['1h']
        if trading_repository.available:
            watchlist_symbols = trading_repository.list_watchlist_symbols()
            if watchlist_symbols:
                symbols = watchlist_symbols
        if not symbols:
            symbols = ['BTC/USD']

        results: list[dict[str, Any]] = []
        engine = BotEngine()
        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    result = engine.run_cycle(
                        symbol=symbol,
                        timeframe=timeframe,
                        portfolio_value=10000,
                        open_trades_count=0,
                        daily_pnl_percent=0,
                        strategy_name=str(config.get('strategy_name') or 'trend_atr_v0.7'),
                        decision_mode=str(config.get('decision_mode') or 'rule'),
                        model_id=config.get('model_id'),
                        min_ml_probability=float(config.get('min_ml_probability') or 0.52),
                        min_model_profit_factor=float(config.get('min_model_profit_factor') or 1.0),
                        min_model_win_rate=float(config.get('min_model_win_rate') or 45.0),
                        allow_degraded_fallback=bool(config.get('allow_degraded_fallback', True)),
                    )
                    results.append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'status': result.get('status'),
                        'order_id': result.get('order_id'),
                        'signal_id': result.get('signal_id'),
                        'reason': result.get('reason'),
                    })
                except Exception as exc:
                    results.append({'symbol': symbol, 'timeframe': timeframe, 'status': 'error', 'error': str(exc)})

        evaluation = engine.evaluate_open_orders()
        summary = {
            'status': 'completed',
            'source': source,
            'symbols': symbols,
            'timeframes': timeframes,
            'strategy_name': config.get('strategy_name'),
            'decision_mode': config.get('decision_mode'),
            'results': results,
            'order_evaluation': {
                'status': evaluation.get('status'),
                'count': evaluation.get('count', 0),
            },
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        self._last_run = summary
        self._persist_run(source, summary)
        return summary

    def list_runs(self, limit: int = 25) -> dict[str, Any]:
        if trading_repository.available:
            return {'items': trading_repository.list_scheduler_runs(limit=limit), 'persistence': 'postgres'}
        return {'items': [self._last_run] if self._last_run else [], 'persistence': 'memory'}

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            config = bot_runtime_service.get_config()
            if config.get('kill_switch_active') or not config.get('scheduler_enabled'):
                break
            self.run_once(source='scheduler')
            interval = max(10, int(config.get('scheduler_interval_seconds') or 60))
            self._stop_event.wait(interval)

    def _persist_run(self, source: str, result: dict[str, Any]) -> None:
        if trading_repository.available:
            trading_repository.create_scheduler_run({
                'source': source,
                'status': result.get('status'),
                'symbols': result.get('symbols') or (result.get('config') or {}).get('symbols') or [],
                'timeframes': result.get('timeframes') or (result.get('config') or {}).get('timeframes') or [],
                'strategy': result.get('strategy_name') or (result.get('config') or {}).get('strategy_name'),
                'decision_mode': result.get('decision_mode') or (result.get('config') or {}).get('decision_mode'),
                'result': result,
            })


bot_scheduler_service = BotSchedulerService()
