from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from typing import Any
from uuid import uuid4
import warnings

from app.config import settings
from app.repositories.trading_repository import trading_repository
from app.services.backtest_service import BacktestService
from app.services.bot_runtime_service import bot_runtime_service
from app.services.local_persistence_service import local_persistence_service
from app.services.ml_training_service import MLTrainingService


DEFAULT_ASSET_UNIVERSE = [
    'BTC/USD', 'ETH/USD', 'SOL/USD', 'BNB/USD', 'XRP/USD',
    'AAPL', 'MSFT', 'NVDA', 'TSLA', 'SPY', 'QQQ', 'IWM',
    'EUR/USD', 'GBP/USD', 'USD/JPY', 'XAU/USD', 'XAG/USD',
]


DEFAULT_AUTOMATION_CONFIG: dict[str, Any] = {
    'enabled': False,
    'search_profile': 'auto',
    'interval_minutes': 360,
    'symbols': ['BTC/USD', 'ETH/USD', 'AAPL', 'SPY'],
    'timeframes': ['1h'],
    'strategies': ['trend_atr_v0.7', 'pullback_ema_v0.7', 'breakout_range_v0.7'],
    'model_type': 'random_forest',
    'model_type_candidates': ['random_forest', 'logistic_regression'],
    'limit': 560,
    'training_limit_candidates': [420, 560, 720],
    'lookahead_bars': 12,
    'lookahead_candidates': [6, 12, 24],
    'max_rows': 2600,
    'max_model_candidates': 4,
    'min_warmup_bars': 80,
    'assets_per_run': 2,
    'strategies_per_asset': 2,
    'optimization_limit': 360,
    'max_combinations': 14,
    'objective': 'robust_score',
    'optimization_objectives': ['robust_score', 'profit_factor', 'return_percent'],
    'initial_capital': 10000.0,
    'risk_per_trade': 0.01,
    'auto_expand_assets': True,
    'asset_universe': DEFAULT_ASSET_UNIVERSE,
    'max_auto_assets': 12,
    'full_strategy_search': True,
    'auto_objective_search': True,
    'auto_update_bot_model': True,
    'auto_update_bot_strategy': True,
    'quality_gate_enabled': True,
    'quality_require_beats_rule': True,
    'min_model_accuracy': 0.5,
    'min_model_win_rate_percent': 40.0,
    'min_model_profit_factor': 0.0,
    'paper_only': True,
    'live_trading_enabled': False,
}


AUTOMATION_SEARCH_PROFILES: dict[str, dict[str, Any]] = {
    'auto': {
        'label': 'Auto',
        'description': 'Waehlt die Suchbreite anhand der letzten Ergebnisse selbst.',
        'settings': {},
    },
    'fast': {
        'label': 'Schnell',
        'description': 'Kurzer Suchlauf mit wenig Rechenzeit.',
        'settings': {
            'interval_minutes': 180,
            'assets_per_run': 1,
            'max_auto_assets': 6,
            'max_model_candidates': 2,
            'model_type_candidates': ['random_forest'],
            'training_limit_candidates': [360, 560],
            'lookahead_candidates': [6, 12],
            'optimization_limit': 260,
            'max_combinations': 8,
            'full_strategy_search': False,
            'strategies_per_asset': 1,
            'auto_objective_search': False,
            'optimization_objectives': ['robust_score'],
            'min_model_accuracy': 0.5,
            'min_model_win_rate_percent': 40.0,
            'min_model_profit_factor': 0.0,
        },
    },
    'balanced': {
        'label': 'Ausgewogen',
        'description': 'Solide Suche mit moderater Laufzeit.',
        'settings': {
            'interval_minutes': 360,
            'assets_per_run': 2,
            'max_auto_assets': 12,
            'max_model_candidates': 4,
            'model_type_candidates': ['random_forest', 'logistic_regression'],
            'training_limit_candidates': [420, 560, 720],
            'lookahead_candidates': [6, 12, 24],
            'optimization_limit': 360,
            'max_combinations': 14,
            'full_strategy_search': True,
            'strategies_per_asset': 2,
            'auto_objective_search': True,
            'optimization_objectives': ['robust_score', 'profit_factor', 'return_percent'],
            'min_model_accuracy': 0.5,
            'min_model_win_rate_percent': 40.0,
            'min_model_profit_factor': 0.0,
        },
    },
    'deep': {
        'label': 'Gruendlich',
        'description': 'Breitere Suche fuer laengere Optimierungen.',
        'settings': {
            'interval_minutes': 720,
            'assets_per_run': 3,
            'max_auto_assets': 18,
            'max_model_candidates': 8,
            'model_type_candidates': ['random_forest', 'logistic_regression'],
            'training_limit_candidates': [360, 560, 720, 960],
            'lookahead_candidates': [6, 12, 24, 36],
            'optimization_limit': 520,
            'max_combinations': 28,
            'full_strategy_search': True,
            'strategies_per_asset': 3,
            'auto_objective_search': True,
            'optimization_objectives': ['robust_score', 'profit_factor', 'return_percent'],
            'min_model_accuracy': 0.52,
            'min_model_win_rate_percent': 42.0,
            'min_model_profit_factor': 0.0,
        },
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> dict[str, Any]:
    return {
        'version': 1,
        'config': deepcopy(DEFAULT_AUTOMATION_CONFIG),
        'cursor': 0,
        'runs': [],
    }


class ModelAutomationService:
    """Paper-only in-process automation for rolling model maintenance."""

    def __init__(self):
        self._state_lock = threading.Lock()
        self._scheduler_lock = threading.Lock()
        self._run_lock = threading.Lock()
        self._progress_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._cancel_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._started_at: str | None = None
        self._current_run: dict[str, Any] | None = None

    @property
    def path(self) -> Path:
        base = Path(settings.local_state_path)
        return base.with_name('model-automation-state.json')

    def status(self) -> dict[str, Any]:
        with self._state_lock:
            state = self._read_state()
        raw_config = self._normalise_config(state.get('config', {}))
        runs = list(state.get('runs') or [])
        profile_decision = self._profile_decision(raw_config, runs)
        config = self._effective_config(raw_config, profile_decision)
        active_symbols = self._expanded_symbols(config)
        run_config = {**config, 'symbols': active_symbols}
        pairs = self._asset_pairs(run_config)
        next_pairs, _ = self._select_pairs(pairs, int(state.get('cursor') or 0), int(config.get('assets_per_run') or 1))
        run_plan = self._run_plan(run_config, next_pairs)
        thread_alive = bool(self._thread and self._thread.is_alive())
        bot_config = self._bot_model_status()
        current_run = self._current_run_snapshot()
        return {
            'status': 'running' if thread_alive else 'stopped',
            'thread_alive': thread_alive,
            'started_at': self._started_at,
            'paper_only': True,
            'live_trading_enabled': False,
            'config': config,
            'cursor': int(state.get('cursor') or 0),
            'next_pairs': next_pairs,
            'search_profiles': self._search_profile_options(),
            'profile_decision': profile_decision,
            'run_plan': run_plan,
            'asset_expansion': {
                'enabled': bool(config.get('auto_expand_assets')),
                'seed_symbols': config.get('symbols', []),
                'active_symbols': active_symbols,
                'active_count': len(active_symbols),
                'max_auto_assets': config.get('max_auto_assets'),
            },
            'last_run': runs[0] if runs else None,
            'recent_runs': runs[:12],
            'current_run': current_run,
            'bot_model': bot_config,
            'state_path': str(self.path),
        }

    def get_config(self) -> dict[str, Any]:
        with self._state_lock:
            state = self._read_state()
            return self._normalise_config(state.get('config', {}))

    def update_config(self, patch: dict[str, Any]) -> dict[str, Any]:
        with self._state_lock:
            state = self._read_state()
            current = self._normalise_config(state.get('config', {}))
            clean = self._clean_patch(patch)
            profile = clean.get('search_profile')
            if patch.get('apply_search_profile') and profile in AUTOMATION_SEARCH_PROFILES and profile != 'auto':
                current.update(deepcopy(AUTOMATION_SEARCH_PROFILES[profile]['settings']))
            current.update(clean)
            current = self._normalise_config(current)
            state['config'] = current
            self._write_state(state)
            return deepcopy(current)

    def start(self) -> dict[str, Any]:
        self.update_config({'enabled': True})
        with self._scheduler_lock:
            if self._thread and self._thread.is_alive():
                return self.status()
            self._stop_event.clear()
            self._cancel_event.clear()
            self._started_at = _now()
            self._thread = threading.Thread(target=self._loop, name='model-automation-scheduler', daemon=True)
            self._thread.start()
        return self.status()

    def stop(self) -> dict[str, Any]:
        self.update_config({'enabled': False})
        self._stop_event.set()
        self._cancel_event.set()
        return self.status()

    def cancel_current_run(self) -> dict[str, Any]:
        self._cancel_event.set()
        self._update_current_run({
            'status': 'cancelling',
            'cancel_requested': True,
            'phase': 'Stop wird vorbereitet',
        })
        return self.status()

    def run_once(self, source: str = 'manual', config_patch: dict[str, Any] | None = None) -> dict[str, Any]:
        if config_patch:
            self.update_config(config_patch)
        if not self._run_lock.acquire(blocking=False):
            return {
                'status': 'busy',
                'reason': 'Ein Automatiklauf ist bereits aktiv.',
                'paper_only': True,
                'live_trading_enabled': False,
                'current_run': self._current_run_snapshot(),
            }
        try:
            self._cancel_event.clear()
            return self._run_once_locked(source=source)
        finally:
            self._run_lock.release()

    def run_background(self, source: str = 'manual', config_patch: dict[str, Any] | None = None) -> dict[str, Any]:
        if config_patch:
            self.update_config(config_patch)
        if not self._run_lock.acquire(blocking=False):
            return {
                'status': 'busy',
                'reason': 'Ein Automatiklauf ist bereits aktiv.',
                'paper_only': True,
                'live_trading_enabled': False,
                'current_run': self._current_run_snapshot(),
            }

        run_id = f'auto-{uuid4().hex[:10]}'
        self._cancel_event.clear()
        self._set_current_run({
            'id': run_id,
            'status': 'starting',
            'source': source,
            'phase': 'Startet',
            'started_at': _now(),
            'completed_steps': 0,
            'total_steps': 0,
            'current_item': None,
            'cancel_requested': False,
            'paper_only': True,
            'live_trading_enabled': False,
        })

        def target() -> None:
            try:
                self._run_once_locked(source=source, run_id=run_id)
            finally:
                self._run_lock.release()

        thread = threading.Thread(target=target, name='model-automation-manual-run', daemon=True)
        thread.start()
        status = self.status()
        status['status'] = 'started'
        return status

    def list_runs(self, limit: int = 25) -> dict[str, Any]:
        with self._state_lock:
            state = self._read_state()
        return {'items': list(state.get('runs') or [])[:limit], 'persistence': 'local_file'}

    def _set_current_run(self, payload: dict[str, Any] | None) -> None:
        with self._progress_lock:
            self._current_run = deepcopy(payload) if payload else None

    def _update_current_run(self, patch: dict[str, Any]) -> None:
        with self._progress_lock:
            if not self._current_run:
                return
            self._current_run.update(deepcopy(patch))

    def _current_run_snapshot(self) -> dict[str, Any] | None:
        with self._progress_lock:
            return deepcopy(self._current_run) if self._current_run else None

    def _run_once_locked(self, source: str, run_id: str | None = None) -> dict[str, Any]:
        with self._state_lock:
            state = self._read_state()
            raw_config = self._normalise_config(state.get('config', {}))
            cursor = int(state.get('cursor') or 0)
            runs = list(state.get('runs') or [])
        profile_decision = self._profile_decision(raw_config, runs)
        config = self._effective_config(raw_config, profile_decision)

        if source != 'manual' and not config.get('enabled'):
            result = {
                'id': f'auto-{uuid4().hex[:10]}',
                'status': 'skipped',
                'source': source,
                'reason': 'Automatik ist pausiert.',
                'started_at': _now(),
                'finished_at': _now(),
                'paper_only': True,
                'live_trading_enabled': False,
            }
            self._persist_run(result, cursor)
            return result

        active_symbols = self._expanded_symbols(config)
        run_config = {**config, 'symbols': active_symbols}
        pairs = self._asset_pairs(run_config)
        selected_pairs, next_cursor = self._select_pairs(pairs, cursor, int(config.get('assets_per_run') or 1))
        run_id = run_id or f'auto-{uuid4().hex[:10]}'
        started_at = _now()
        errors: list[dict[str, Any]] = []
        model_summary: dict[str, Any] | None = None
        bot_model_update: dict[str, Any] | None = None
        model_candidates: list[dict[str, Any]] = []
        optimizations: list[dict[str, Any]] = []
        training_candidates = self._training_candidates(run_config)
        strategies = self._strategy_candidates(run_config)
        objectives = self._objective_candidates(run_config)
        run_plan = self._run_plan(run_config, selected_pairs)
        total_steps = len(training_candidates) + (len(selected_pairs) * len(strategies) * len(objectives))
        completed_steps = 0
        self._set_current_run({
            'id': run_id,
            'status': 'running',
            'source': source,
            'phase': 'Vorbereitung',
            'started_at': started_at,
            'completed_steps': completed_steps,
            'total_steps': total_steps,
            'current_item': None,
            'cancel_requested': False,
            'paper_only': True,
            'live_trading_enabled': False,
        })

        trainer = MLTrainingService()
        for candidate in training_candidates:
            if self._cancel_event.is_set():
                break
            self._update_current_run({
                'phase': 'Modelltraining',
                'completed_steps': completed_steps,
                'current_item': {
                    'type': 'model',
                    'model_type': candidate.get('model_type'),
                    'limit': candidate.get('limit'),
                    'lookahead_bars': candidate.get('lookahead_bars'),
                },
            })
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', category=RuntimeWarning, module=r'sklearn\..*')
                    model_result = trainer.train(
                        symbols=list(run_config['symbols']),
                        timeframes=list(run_config['timeframes']),
                        strategies=list(run_config['strategies']),
                        limit=int(candidate['limit']),
                        lookahead_bars=int(candidate['lookahead_bars']),
                        max_rows=int(run_config['max_rows']),
                        min_warmup_bars=int(run_config['min_warmup_bars']),
                        model_type=str(candidate['model_type']),
                        test_size=0.25,
                        target_column='target_label',
                    )
                if trading_repository.available:
                    model_result['db_id'] = trading_repository.create_ml_model_version(model_result)
                    model_result['persistence'] = 'postgres'
                else:
                    model_result['db_id'] = None
                    model_result['persistence'] = 'local_file'
                summary = self._model_summary(model_result)
                summary['candidate'] = candidate
                summary['score'] = self._model_candidate_score(summary)
                model_candidates.append(summary)
            except Exception as exc:
                errors.append({'stage': 'training', 'candidate': candidate, 'detail': str(exc)})
            finally:
                completed_steps += 1
                self._update_current_run({'completed_steps': completed_steps})

        model_summary = self._best_model_candidate(model_candidates)

        optimizer = BacktestService()
        for pair in selected_pairs:
            if self._cancel_event.is_set():
                break
            for strategy_name in strategies:
                if self._cancel_event.is_set():
                    break
                for objective in objectives:
                    if self._cancel_event.is_set():
                        break
                    self._update_current_run({
                        'phase': 'Strategieoptimierung',
                        'completed_steps': completed_steps,
                        'current_item': {
                            'type': 'optimization',
                            'symbol': pair['symbol'],
                            'timeframe': pair['timeframe'],
                            'strategy': strategy_name,
                            'objective': objective,
                        },
                    })
                    try:
                        result = optimizer.optimize(
                            symbol=pair['symbol'],
                            timeframe=pair['timeframe'],
                            strategy_name=strategy_name,
                            limit=int(run_config['optimization_limit']),
                            initial_capital=float(run_config['initial_capital']),
                            risk_per_trade=float(run_config['risk_per_trade']),
                            objective=str(objective),
                            max_combinations=int(run_config['max_combinations']),
                            min_warmup_bars=int(run_config['min_warmup_bars']),
                        )
                        if trading_repository.available:
                            result['optimization_id'] = trading_repository.create_optimization_run(result)
                            result['persistence'] = 'postgres'
                        else:
                            result['optimization_id'] = None
                            result['persistence'] = 'local_file'
                        optimizations.append(self._optimization_summary(result))
                    except Exception as exc:
                        errors.append({
                            'stage': 'optimization',
                            'symbol': pair['symbol'],
                            'timeframe': pair['timeframe'],
                            'strategy': strategy_name,
                            'objective': objective,
                            'detail': str(exc),
                        })
                    finally:
                        completed_steps += 1
                        self._update_current_run({'completed_steps': completed_steps})

        cancelled = self._cancel_event.is_set()
        if cancelled:
            errors.append({'stage': 'cancelled', 'detail': 'Lauf wurde gestoppt.'})
        best_optimization = self._best_optimization(optimizations)
        champion = self._champion_summary(model_summary, best_optimization, run_config)
        if model_summary and not cancelled:
            bot_model_update = self._sync_bot_model(model_summary, run_config, best_optimization=best_optimization)
            if bot_model_update.get('status') == 'error':
                errors.append({'stage': 'bot_model_sync', 'detail': bot_model_update.get('detail')})

        if cancelled:
            status = 'cancelled'
        elif model_summary and optimizations and not errors:
            status = 'completed'
        elif model_summary or optimizations:
            status = 'completed_with_warnings'
        else:
            status = 'failed'

        result = {
            'id': run_id,
            'status': status,
            'source': source,
            'started_at': started_at,
            'finished_at': _now(),
            'selected_pairs': selected_pairs,
            'next_cursor': next_cursor,
            'asset_expansion': {
                'enabled': bool(run_config.get('auto_expand_assets')),
                'seed_symbols': config.get('symbols', []),
                'active_symbols': active_symbols,
                'active_count': len(active_symbols),
            },
            'model': model_summary,
            'model_candidates': model_candidates,
            'bot_model_update': bot_model_update,
            'optimizations': optimizations,
            'best': best_optimization,
            'champion': champion,
            'run_plan': run_plan,
            'errors': errors,
            'config_snapshot': {
                'search_profile': run_config['search_profile'],
                'effective_search_profile': run_config.get('effective_search_profile'),
                'profile_reason': profile_decision.get('reason'),
                'symbols': run_config['symbols'],
                'timeframes': run_config['timeframes'],
                'strategies': run_config['strategies'],
                'model_type': run_config['model_type'],
                'assets_per_run': run_config['assets_per_run'],
                'max_combinations': run_config['max_combinations'],
                'model_candidates': len(model_candidates),
                'optimization_objectives': objectives,
                'auto_update_bot_model': run_config['auto_update_bot_model'],
                'auto_update_bot_strategy': run_config['auto_update_bot_strategy'],
                'quality_gate_enabled': run_config['quality_gate_enabled'],
            },
            'paper_only': True,
            'live_trading_enabled': False,
        }
        self._update_current_run({
            'status': status,
            'phase': 'Gestoppt' if cancelled else 'Fertig',
            'completed_steps': completed_steps,
            'finished_at': result['finished_at'],
            'current_item': None,
        })
        self._persist_run(result, next_cursor)
        self._set_current_run(None)
        return result

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            config = self.get_config()
            if not config.get('enabled'):
                break
            self.run_once(source='scheduler')
            config = self.get_config()
            interval_seconds = max(60, int(config.get('interval_minutes') or 360) * 60)
            self._stop_event.wait(interval_seconds)

    def _persist_run(self, result: dict[str, Any], cursor: int) -> None:
        with self._state_lock:
            state = self._read_state()
            state['cursor'] = cursor
            runs = [deepcopy(result)] + list(state.get('runs') or [])
            state['runs'] = runs[:60]
            self._write_state(state)

    def _read_state(self) -> dict[str, Any]:
        if not self.path.exists():
            return _default_state()
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            return _default_state()
        state = _default_state()
        if isinstance(data, dict):
            state.update(data)
        state['config'] = self._normalise_config(state.get('config', {}))
        state.setdefault('cursor', 0)
        state.setdefault('runs', [])
        return state

    def _write_state(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(f'{self.path.suffix}.tmp')
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True, default=str), encoding='utf-8')
        tmp.replace(self.path)

    def _normalise_config(self, config: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(DEFAULT_AUTOMATION_CONFIG)
        merged.update(config or {})
        cleaned = self._clean_patch(merged)
        merged.update(cleaned)
        merged['paper_only'] = True
        merged['live_trading_enabled'] = False
        return merged

    def _clean_patch(self, patch: dict[str, Any]) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key, value in (patch or {}).items():
            if value is None or key in {'paper_only', 'live_trading_enabled'}:
                continue
            if key in {'symbols', 'timeframes', 'strategies', 'asset_universe', 'model_type_candidates', 'optimization_objectives'}:
                items = self._list_value(value)
                if items:
                    clean[key] = items
            elif key == 'enabled':
                clean[key] = bool(value)
            elif key in {'auto_update_bot_model', 'auto_update_bot_strategy', 'auto_expand_assets', 'full_strategy_search', 'auto_objective_search'}:
                clean[key] = bool(value)
            elif key in {'quality_gate_enabled', 'quality_require_beats_rule'}:
                clean[key] = bool(value)
            elif key in {'training_limit_candidates', 'lookahead_candidates'}:
                values = self._int_list_value(value)
                if values:
                    clean[key] = values
            elif key in {'interval_minutes', 'limit', 'lookahead_bars', 'max_rows', 'max_model_candidates', 'min_warmup_bars', 'assets_per_run', 'max_auto_assets', 'strategies_per_asset', 'optimization_limit', 'max_combinations'}:
                clean[key] = int(value)
            elif key in {'initial_capital', 'risk_per_trade', 'min_model_accuracy', 'min_model_win_rate_percent', 'min_model_profit_factor'}:
                clean[key] = float(value)
            elif key == 'search_profile':
                clean[key] = self._normalise_search_profile(value)
            elif key in {'model_type', 'objective'}:
                clean[key] = str(value).strip() or DEFAULT_AUTOMATION_CONFIG[key]
        int_bounds = {
            'interval_minutes': (5, 1440),
            'limit': (180, 2500),
            'lookahead_bars': (1, 120),
            'max_rows': (200, 50000),
            'max_model_candidates': (1, 12),
            'min_warmup_bars': (50, 500),
            'assets_per_run': (1, 12),
            'max_auto_assets': (1, 50),
            'strategies_per_asset': (1, 4),
            'optimization_limit': (160, 1500),
            'max_combinations': (1, 250),
        }
        for key, (minimum, maximum) in int_bounds.items():
            if key in clean:
                clean[key] = max(minimum, min(maximum, int(clean[key])))
        if 'risk_per_trade' in clean:
            clean['risk_per_trade'] = max(0.0001, min(0.05, float(clean['risk_per_trade'])))
        if 'initial_capital' in clean:
            clean['initial_capital'] = max(1.0, float(clean['initial_capital']))
        if 'min_model_accuracy' in clean:
            clean['min_model_accuracy'] = max(0.0, min(1.0, float(clean['min_model_accuracy'])))
        if 'min_model_win_rate_percent' in clean:
            clean['min_model_win_rate_percent'] = max(0.0, min(100.0, float(clean['min_model_win_rate_percent'])))
        if 'min_model_profit_factor' in clean:
            clean['min_model_profit_factor'] = max(0.0, min(10.0, float(clean['min_model_profit_factor'])))
        if 'training_limit_candidates' in clean:
            clean['training_limit_candidates'] = [max(180, min(2500, int(value))) for value in clean['training_limit_candidates']]
        if 'lookahead_candidates' in clean:
            clean['lookahead_candidates'] = [max(1, min(120, int(value))) for value in clean['lookahead_candidates']]
        return clean

    def _normalise_search_profile(self, value: Any) -> str:
        profile = str(value or '').strip().lower()
        if profile in AUTOMATION_SEARCH_PROFILES:
            return profile
        if profile == 'custom':
            return profile
        return 'balanced'

    def _search_profile_options(self) -> list[dict[str, str]]:
        return [
            {
                'id': profile_id,
                'label': str(profile.get('label') or profile_id),
                'description': str(profile.get('description') or ''),
            }
            for profile_id, profile in AUTOMATION_SEARCH_PROFILES.items()
        ]

    def _profile_decision(self, config: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
        requested = self._normalise_search_profile(config.get('search_profile') or 'auto')
        if requested != 'auto':
            return {
                'requested_profile': requested,
                'effective_profile': requested if requested in AUTOMATION_SEARCH_PROFILES else 'balanced',
                'label': self._profile_label(requested),
                'reason': 'Manuell gewaehlt.',
                'auto': False,
            }

        last_run = next((run for run in runs if run.get('status') != 'skipped'), None)
        if not last_run:
            return {
                'requested_profile': 'auto',
                'effective_profile': 'balanced',
                'label': self._profile_label('balanced'),
                'reason': 'Noch keine belastbare Historie; starte ausgewogen.',
                'auto': True,
            }

        status = str(last_run.get('status') or '')
        errors = list(last_run.get('errors') or [])
        bot_update = last_run.get('bot_model_update') or {}
        quality_gate = bot_update.get('quality_gate') or {}
        best = last_run.get('best') or {}
        metrics = best.get('metrics') or {}
        profit_factor = self._float_or_none(metrics.get('profit_factor'))
        win_rate = self._float_or_none(metrics.get('win_rate_percent'))

        if status == 'failed':
            effective = 'balanced'
            reason = 'Letzter Lauf ist fehlgeschlagen; naechster Lauf bleibt stabil und mittelgross.'
        elif bot_update.get('status') == 'blocked' or quality_gate.get('passed') is False:
            effective = 'deep'
            reason = 'Qualitaetspruefung hat blockiert; naechster Lauf sucht breiter.'
        elif profit_factor is not None and profit_factor < 1.0:
            effective = 'deep'
            reason = 'Letzte Optimierung war zu schwach; naechster Lauf sucht gruendlicher.'
        elif errors:
            effective = 'balanced'
            reason = 'Letzter Lauf hatte Hinweise; naechster Lauf bleibt ausgewogen.'
        elif status == 'completed' and profit_factor is not None and profit_factor >= 1.3 and (win_rate or 0.0) >= 50.0:
            effective = 'fast'
            reason = 'Letzter Lauf war stark; naechster Lauf ueberwacht kompakter.'
        else:
            effective = 'balanced'
            reason = 'Keine klare Sondersituation; naechster Lauf bleibt ausgewogen.'

        return {
            'requested_profile': 'auto',
            'effective_profile': effective,
            'label': self._profile_label(effective),
            'reason': reason,
            'auto': True,
        }

    def _effective_config(self, config: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
        effective = deepcopy(config)
        effective_profile = str(decision.get('effective_profile') or config.get('search_profile') or 'balanced')
        if config.get('search_profile') == 'auto' and effective_profile in AUTOMATION_SEARCH_PROFILES:
            effective.update(deepcopy(AUTOMATION_SEARCH_PROFILES[effective_profile].get('settings') or {}))
        effective['search_profile'] = config.get('search_profile') or 'auto'
        effective['effective_search_profile'] = effective_profile
        effective['profile_reason'] = decision.get('reason')
        effective['paper_only'] = True
        effective['live_trading_enabled'] = False
        return self._normalise_config(effective)

    def _profile_label(self, profile: str) -> str:
        item = AUTOMATION_SEARCH_PROFILES.get(profile) or AUTOMATION_SEARCH_PROFILES.get('balanced') or {}
        return str(item.get('label') or profile)

    def _run_plan(self, config: dict[str, Any], selected_pairs: list[dict[str, str]]) -> dict[str, Any]:
        model_tests = len(self._training_candidates(config))
        strategies = self._strategy_candidates(config)
        objectives = self._objective_candidates(config)
        optimization_tests = len(selected_pairs) * len(strategies) * len(objectives)
        return {
            'search_profile': config.get('search_profile') or 'balanced',
            'effective_search_profile': config.get('effective_search_profile') or config.get('search_profile') or 'balanced',
            'profile_reason': config.get('profile_reason'),
            'model_tests': model_tests,
            'asset_tests': len(selected_pairs),
            'strategy_tests': len(strategies),
            'objective_tests': len(objectives),
            'optimization_tests': optimization_tests,
            'total_steps': model_tests + optimization_tests,
            'estimated_parameter_tests': optimization_tests * int(config.get('max_combinations') or 0),
        }

    def _list_value(self, value: Any) -> list[str]:
        if isinstance(value, str):
            raw_items = value.replace('\n', ',').replace(';', ',').split(',')
        else:
            raw_items = list(value or [])
        items: list[str] = []
        for item in raw_items:
            text = str(item).strip()
            if text and text not in items:
                items.append(text)
        return items

    def _int_list_value(self, value: Any) -> list[int]:
        if isinstance(value, str):
            raw_items = value.replace('\n', ',').replace(';', ',').split(',')
        else:
            raw_items = list(value or [])
        items: list[int] = []
        for item in raw_items:
            try:
                number = int(float(str(item).strip()))
            except (TypeError, ValueError):
                continue
            if number not in items:
                items.append(number)
        return items

    def _expanded_symbols(self, config: dict[str, Any]) -> list[str]:
        symbols = self._list_value(config.get('symbols') or [])
        if not config.get('auto_expand_assets'):
            return symbols or ['BTC/USD']

        candidates: list[str] = []
        candidates.extend(symbols)
        try:
            if trading_repository.available:
                candidates.extend(trading_repository.list_watchlist_symbols())
            else:
                candidates.extend([item.get('symbol') for item in local_persistence_service.list_watchlist()])
        except Exception:
            pass
        candidates.extend(self._list_value(config.get('asset_universe') or DEFAULT_ASSET_UNIVERSE))

        unique: list[str] = []
        for symbol in candidates:
            text = str(symbol or '').strip().upper()
            if text and text not in unique:
                unique.append(text)
        return unique[: int(config.get('max_auto_assets') or 12)] or ['BTC/USD']

    def _training_candidates(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        model_types = self._list_value(config.get('model_type_candidates') or [config.get('model_type') or 'random_forest'])
        limits = self._int_list_value(config.get('training_limit_candidates') or [config.get('limit') or 560])
        lookaheads = self._int_list_value(config.get('lookahead_candidates') or [config.get('lookahead_bars') or 12])
        candidates: list[dict[str, Any]] = []
        seen: set[tuple[str, int, int]] = set()
        for limit in limits:
            for lookahead_bars in lookaheads:
                for model_type in model_types:
                    key = (model_type, limit, lookahead_bars)
                    if key in seen:
                        continue
                    seen.add(key)
                    candidates.append({
                        'model_type': model_type,
                        'limit': max(180, min(2500, int(limit))),
                        'lookahead_bars': max(1, min(120, int(lookahead_bars))),
                    })
        return candidates[: int(config.get('max_model_candidates') or 4)] or [{
            'model_type': str(config.get('model_type') or 'random_forest'),
            'limit': int(config.get('limit') or 560),
            'lookahead_bars': int(config.get('lookahead_bars') or 12),
        }]

    def _strategy_candidates(self, config: dict[str, Any]) -> list[str]:
        strategies = self._list_value(config.get('strategies') or [])
        if not config.get('full_strategy_search'):
            return strategies[: int(config.get('strategies_per_asset') or 1)] or ['trend_atr_v0.7']
        return strategies or ['trend_atr_v0.7']

    def _objective_candidates(self, config: dict[str, Any]) -> list[str]:
        if not config.get('auto_objective_search'):
            return [str(config.get('objective') or 'robust_score')]
        return self._list_value(config.get('optimization_objectives') or ['robust_score']) or ['robust_score']

    def _asset_pairs(self, config: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {'symbol': symbol, 'timeframe': timeframe}
            for symbol in config.get('symbols', [])
            for timeframe in config.get('timeframes', [])
        ] or [{'symbol': 'BTC/USD', 'timeframe': '1h'}]

    def _select_pairs(self, pairs: list[dict[str, str]], cursor: int, count: int) -> tuple[list[dict[str, str]], int]:
        if not pairs:
            return [], 0
        selected: list[dict[str, str]] = []
        for offset in range(max(1, count)):
            selected.append(pairs[(cursor + offset) % len(pairs)])
        return selected, (cursor + len(selected)) % len(pairs)

    def _model_summary(self, result: dict[str, Any]) -> dict[str, Any]:
        return {
            'model_id': result.get('model_id'),
            'model_type': result.get('model_type'),
            'created_at': result.get('created_at'),
            'row_count': result.get('row_count'),
            'train_rows': result.get('train_rows'),
            'test_rows': result.get('test_rows'),
            'accuracy': (result.get('metrics') or {}).get('accuracy'),
            'rule_accuracy': (result.get('rule_baseline_metrics') or {}).get('accuracy'),
            'profit_factor': (result.get('trading_metrics') or {}).get('profit_factor'),
            'win_rate_percent': (result.get('trading_metrics') or {}).get('win_rate_percent'),
            'model_path': result.get('model_path'),
            'db_id': result.get('db_id'),
            'persistence': result.get('persistence'),
        }

    def _model_candidate_score(self, summary: dict[str, Any]) -> float:
        accuracy = self._float_or_none(summary.get('accuracy')) or 0.0
        rule_accuracy = self._float_or_none(summary.get('rule_accuracy')) or 0.0
        win_rate = (self._float_or_none(summary.get('win_rate_percent')) or 0.0) / 100.0
        profit_factor = self._float_or_none(summary.get('profit_factor')) or 0.0
        rows = min(float(summary.get('row_count') or 0.0), 5000.0) / 5000.0
        rule_edge = max(0.0, accuracy - rule_accuracy)
        return round((accuracy * 4.0) + (rule_edge * 3.0) + win_rate + min(profit_factor, 3.0) * 0.25 + rows * 0.2, 6)

    def _best_model_candidate(self, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: float(item.get('score') or -999999), reverse=True)[0]

    def _champion_summary(
        self,
        model_summary: dict[str, Any] | None,
        best_optimization: dict[str, Any] | None,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        model_score = float((model_summary or {}).get('score') or 0.0)
        optimization_score = self._optimization_candidate_score(best_optimization or {})
        return {
            'status': 'ready' if model_summary or best_optimization else 'unavailable',
            'score': round(model_score + optimization_score, 6),
            'model_id': (model_summary or {}).get('model_id'),
            'model_type': (model_summary or {}).get('model_type'),
            'model_candidate': (model_summary or {}).get('candidate'),
            'symbol': (best_optimization or {}).get('symbol'),
            'timeframe': (best_optimization or {}).get('timeframe'),
            'strategy': (best_optimization or {}).get('strategy'),
            'objective': (best_optimization or {}).get('objective') or config.get('objective'),
            'best_params': (best_optimization or {}).get('best_params') or {},
            'metrics': (best_optimization or {}).get('metrics') or {},
            'paper_only': True,
        }

    def _sync_bot_model(
        self,
        model_summary: dict[str, Any],
        config: dict[str, Any],
        best_optimization: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        model_id = model_summary.get('model_id')
        if not config.get('auto_update_bot_model') or not model_id:
            return {'enabled': False, 'status': 'skipped', 'model_id': model_id}
        gate = self._model_quality_gate(model_summary, config)
        if not gate.get('passed'):
            return {
                'enabled': True,
                'status': 'blocked',
                'model_id': model_id,
                'reason': gate.get('reason'),
                'quality_gate': gate,
            }
        try:
            patch: dict[str, Any] = {
                'model_id': model_id,
                'allow_degraded_fallback': True,
            }
            if config.get('auto_update_bot_strategy') and best_optimization and best_optimization.get('strategy'):
                patch['strategy_name'] = best_optimization.get('strategy')
            bot_config = bot_runtime_service.update_config(patch)
            return {
                'enabled': True,
                'status': 'updated',
                'model_id': model_id,
                'strategy_name': bot_config.get('strategy_name'),
                'recommended_params': (best_optimization or {}).get('best_params') or {},
                'decision_mode': bot_config.get('decision_mode'),
                'persistence': bot_config.get('persistence'),
                'quality_gate': gate,
            }
        except Exception as exc:
            return {'enabled': True, 'status': 'error', 'model_id': model_id, 'detail': str(exc)}

    def _model_quality_gate(self, model_summary: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        if not config.get('quality_gate_enabled'):
            return {'enabled': False, 'passed': True, 'reason': 'Qualitaetspruefung ist deaktiviert.', 'checks': []}

        accuracy = self._float_or_none(model_summary.get('accuracy'))
        rule_accuracy = self._float_or_none(model_summary.get('rule_accuracy'))
        win_rate = self._float_or_none(model_summary.get('win_rate_percent'))
        profit_factor = self._float_or_none(model_summary.get('profit_factor'))
        checks: list[dict[str, Any]] = []

        min_accuracy = float(config.get('min_model_accuracy') or 0.0)
        checks.append({
            'name': 'Mindest-Accuracy',
            'passed': accuracy is not None and accuracy >= min_accuracy,
            'actual': accuracy,
            'minimum': min_accuracy,
        })

        if config.get('quality_require_beats_rule'):
            checks.append({
                'name': 'Besser als Regelmodell',
                'passed': accuracy is not None and rule_accuracy is not None and accuracy >= rule_accuracy,
                'actual': accuracy,
                'minimum': rule_accuracy,
            })

        min_win_rate = float(config.get('min_model_win_rate_percent') or 0.0)
        checks.append({
            'name': 'Mindest-Trefferquote',
            'passed': win_rate is not None and win_rate >= min_win_rate,
            'actual': win_rate,
            'minimum': min_win_rate,
        })

        min_profit_factor = float(config.get('min_model_profit_factor') or 0.0)
        if min_profit_factor > 0:
            checks.append({
                'name': 'Mindest-Profit-Factor',
                'passed': profit_factor is not None and profit_factor >= min_profit_factor,
                'actual': profit_factor,
                'minimum': min_profit_factor,
            })

        failed = [check for check in checks if not check['passed']]
        return {
            'enabled': True,
            'passed': not failed,
            'reason': 'Alle Qualitaetsregeln erfuellt.' if not failed else f"{failed[0]['name']} nicht erfuellt.",
            'checks': checks,
            'metrics': {
                'accuracy': accuracy,
                'rule_accuracy': rule_accuracy,
                'win_rate_percent': win_rate,
                'profit_factor': profit_factor,
            },
        }

    def _float_or_none(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _bot_model_status(self) -> dict[str, Any]:
        try:
            bot_config = bot_runtime_service.get_config()
            return {
                'model_id': bot_config.get('model_id'),
                'decision_mode': bot_config.get('decision_mode'),
                'persistence': bot_config.get('persistence'),
                'live_trading_enabled': False,
            }
        except Exception as exc:
            return {'model_id': None, 'status': 'unavailable', 'detail': str(exc), 'live_trading_enabled': False}

    def _optimization_summary(self, result: dict[str, Any]) -> dict[str, Any]:
        best = result.get('best') or {}
        metrics = best.get('metrics') or {}
        return {
            'symbol': result.get('symbol'),
            'timeframe': result.get('timeframe'),
            'strategy': result.get('strategy'),
            'objective': result.get('objective'),
            'tested_combinations': result.get('tested_combinations'),
            'best_score': best.get('score'),
            'robust_score': best.get('robust_score'),
            'best_params': best.get('params') or {},
            'metrics': {
                'return_percent': metrics.get('return_percent'),
                'profit_factor': metrics.get('profit_factor'),
                'win_rate_percent': metrics.get('win_rate_percent'),
                'max_drawdown_percent': metrics.get('max_drawdown_percent'),
                'trades': metrics.get('trades') if metrics.get('trades') is not None else metrics.get('total_trades'),
            },
            'optimization_id': result.get('optimization_id'),
            'persistence': result.get('persistence'),
        }

    def _best_optimization(self, items: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not items:
            return None

        return sorted(items, key=self._optimization_candidate_score, reverse=True)[0]

    def _optimization_candidate_score(self, item: dict[str, Any]) -> float:
        metrics = item.get('metrics') or {}
        return_percent = float(metrics.get('return_percent') or 0.0)
        profit_factor = float(metrics.get('profit_factor') or 0.0)
        win_rate = float(metrics.get('win_rate_percent') or 0.0)
        drawdown = float(metrics.get('max_drawdown_percent') or 0.0)
        robust_score = float(item.get('robust_score') or 0.0)
        trades = float(metrics.get('trades') if metrics.get('trades') is not None else metrics.get('total_trades') or 0.0)
        trade_penalty = 8.0 if trades < 3 else 0.0
        return round(robust_score + return_percent + (profit_factor * 2.5) + (win_rate * 0.04) - (drawdown * 0.8) - trade_penalty, 6)


model_automation_service = ModelAutomationService()
