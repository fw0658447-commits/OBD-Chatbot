from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Any
import csv
import io

from app.config import settings
from app.services.ai_prediction_service import AIPredictionService
from app.services.indicator_service import IndicatorService
from app.services.market_data_service import get_market_data_service
from app.services.strategy_engine import StrategyEngine


@dataclass
class BacktestConfig:
    symbol: str
    timeframe: str = '1h'
    limit: int = 420
    initial_capital: float = 10000.0
    risk_per_trade: float = settings.max_risk_per_trade
    max_hold_bars: int | None = None
    min_warmup_bars: int = 80
    min_confidence_score: float = settings.min_confidence_score
    max_risk_score: float = settings.max_risk_score
    min_crv: float = settings.min_crv
    strategy_name: str = StrategyEngine.DEFAULT_STRATEGY
    strategy_params: dict[str, Any] = field(default_factory=dict)


class BacktestService:
    """Deterministic paper backtester for the MVP strategy catalogue."""

    def __init__(self):
        self.market_data_service = get_market_data_service()
        self.indicator_service = IndicatorService()
        self.ai_prediction_service = AIPredictionService()
        self.strategy_engine = StrategyEngine()

    def list_strategies(self) -> list[dict[str, Any]]:
        return self.strategy_engine.list_strategies()

    def parameter_grid(self, strategy_name: str) -> dict[str, list[Any]]:
        return self.strategy_engine.get_parameter_grid(strategy_name)

    def run(self, config: BacktestConfig) -> dict[str, Any]:
        candles = self.market_data_service.get_candles(
            symbol=config.symbol,
            timeframe=config.timeframe,
            limit=config.limit,
        )
        config.strategy_name = self.strategy_engine.resolve_strategy_name(config.strategy_name)
        return self._run_on_candles(config=config, candles=candles, sample_label='full_sample')

    def compare(
        self,
        symbols: list[str],
        timeframes: list[str],
        strategies: list[str],
        limit: int,
        initial_capital: float,
    ) -> dict[str, Any]:
        runs: list[dict[str, Any]] = []
        for symbol in symbols:
            for timeframe in timeframes:
                for strategy_name in strategies:
                    config = BacktestConfig(
                        symbol=symbol,
                        timeframe=timeframe,
                        limit=limit,
                        initial_capital=initial_capital,
                        strategy_name=self.strategy_engine.resolve_strategy_name(strategy_name),
                        max_hold_bars=self._default_hold_bars(strategy_name),
                    )
                    try:
                        result = self.run(config)
                        runs.append({
                            'symbol': result['symbol'],
                            'timeframe': result['timeframe'],
                            'strategy': result['strategy'],
                            'metrics': result['metrics'],
                            'final_equity': result['final_equity'],
                            'signals_count': result['signals_count'],
                            'blocked_signals_count': result['blocked_signals_count'],
                        })
                    except Exception as exc:
                        runs.append({
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'strategy': strategy_name,
                            'error': str(exc),
                        })
        ranked = sorted(
            [run for run in runs if 'metrics' in run],
            key=lambda row: (
                row['metrics'].get('profit_factor') or 0,
                row['metrics'].get('return_percent') or 0,
                -(row['metrics'].get('max_drawdown_percent') or 0),
            ),
            reverse=True,
        )
        return {'items': runs, 'ranking': ranked, 'strategies': strategies}

    def optimize(
        self,
        symbol: str,
        timeframe: str,
        strategy_name: str,
        limit: int,
        initial_capital: float,
        risk_per_trade: float,
        objective: str = 'robust_score',
        max_combinations: int = 60,
        parameter_grid: dict[str, list[Any]] | None = None,
        min_warmup_bars: int = 80,
    ) -> dict[str, Any]:
        strategy_name = self.strategy_engine.resolve_strategy_name(strategy_name)
        grid = parameter_grid or self.parameter_grid(strategy_name)
        if not grid:
            raise ValueError(f'No optimization grid configured for {strategy_name}')

        keys = list(grid.keys())
        combinations = [dict(zip(keys, values)) for values in product(*(grid[key] for key in keys))]
        combinations = combinations[:max_combinations]
        config_keys = {'min_confidence_score', 'max_risk_score', 'min_crv', 'max_hold_bars', 'risk_per_trade'}
        runs: list[dict[str, Any]] = []

        for params in combinations:
            strategy_params = {key: value for key, value in params.items() if key not in config_keys}
            config = BacktestConfig(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                initial_capital=initial_capital,
                risk_per_trade=float(params.get('risk_per_trade', risk_per_trade)),
                max_hold_bars=int(params['max_hold_bars']) if 'max_hold_bars' in params else self._default_hold_bars(strategy_name),
                min_warmup_bars=min_warmup_bars,
                min_confidence_score=float(params.get('min_confidence_score', settings.min_confidence_score)),
                max_risk_score=float(params.get('max_risk_score', settings.max_risk_score)),
                min_crv=float(params.get('min_crv', settings.min_crv)),
                strategy_name=strategy_name,
                strategy_params=strategy_params,
            )
            try:
                result = self.run(config)
                metrics = result['metrics']
                item = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'strategy': strategy_name,
                    'params': params,
                    'strategy_params': strategy_params,
                    'metrics': metrics,
                    'final_equity': result['final_equity'],
                    'signals_count': result['signals_count'],
                    'blocked_signals_count': result['blocked_signals_count'],
                    'score': self._optimization_score(metrics, objective),
                    'robust_score': self._optimization_score(metrics, 'robust_score'),
                }
                runs.append(item)
            except Exception as exc:
                runs.append({'params': params, 'strategy': strategy_name, 'error': str(exc), 'score': -999999})

        ranked = sorted([run for run in runs if 'metrics' in run], key=lambda row: row.get('score', -999999), reverse=True)
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'strategy': strategy_name,
            'objective': objective,
            'tested_combinations': len(combinations),
            'items': runs,
            'ranking': ranked,
            'best': ranked[0] if ranked else None,
        }

    def export_ml_dataset(
        self,
        symbols: list[str],
        timeframes: list[str],
        strategies: list[str],
        limit: int = 500,
        lookahead_bars: int = 12,
        max_rows: int = 5000,
        min_warmup_bars: int = 80,
    ) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        for symbol in symbols:
            for timeframe in timeframes:
                candles = self.market_data_service.get_candles(symbol=symbol, timeframe=timeframe, limit=limit)
                upper = min(len(candles) - lookahead_bars, limit)
                if upper <= min_warmup_bars:
                    continue
                for i in range(min_warmup_bars, upper):
                    if len(rows) >= max_rows:
                        break
                    lookback = candles[: i + 1]
                    indicators = self.indicator_service.calculate(lookback)
                    prediction = self.ai_prediction_service.predict(symbol=symbol, timeframe=timeframe, indicators=indicators)
                    future_close = float(candles[i + lookahead_bars]['close'])
                    current_close = float(candles[i]['close'])
                    future_return_percent = (future_close - current_close) / current_close * 100 if current_close else 0.0
                    target_label = 1 if future_return_percent > 0.25 else (-1 if future_return_percent < -0.25 else 0)
                    base = {
                        'timestamp': candles[i]['timestamp'],
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'lookahead_bars': lookahead_bars,
                        'close': round(current_close, 6),
                        'future_close': round(future_close, 6),
                        'future_return_percent': round(future_return_percent, 6),
                        'target_label': target_label,
                        'rsi': round(float(indicators.get('rsi') or 0), 6),
                        'atr_percent': round(float(indicators.get('atr_percent') or 0), 6),
                        'trend_strength': round(float(indicators.get('trend_strength') or 0), 6),
                        'price_above_sma50': int(bool(indicators.get('price_above_sma50'))),
                        'sma20_above_sma50': int(bool(indicators.get('sma20_above_sma50'))),
                        'volume_confirmation': int(bool(indicators.get('volume_confirmation'))),
                        'probability_long': round(float(prediction.get('probability_long') or 0), 6),
                        'probability_short': round(float(prediction.get('probability_short') or 0), 6),
                        'probability_neutral': round(float(prediction.get('probability_neutral') or 0), 6),
                        'confidence_score': round(float(prediction.get('confidence_score') or 0), 6),
                        'risk_score': round(float(prediction.get('risk_score') or 0), 6),
                        'prediction_direction': prediction.get('direction'),
                    }
                    for strategy_name in strategies:
                        resolved = self.strategy_engine.resolve_strategy_name(strategy_name)
                        try:
                            signal = self.strategy_engine.create_signal(prediction, indicators, strategy_name=resolved)
                        except Exception:
                            signal = None
                        row = dict(base)
                        row.update({
                            'strategy': resolved,
                            'signal_type': signal.get('signal_type') if signal else 'none',
                            'signal_score': round(float(signal.get('signal_score') or 0), 6) if signal else 0.0,
                            'crv': round(float(signal.get('crv') or 0), 6) if signal else 0.0,
                            'entry_price': signal.get('entry_price') if signal else None,
                            'stop_loss': signal.get('stop_loss') if signal else None,
                            'take_profit': signal.get('take_profit') if signal else None,
                        })
                        rows.append(row)
                        if len(rows) >= max_rows:
                            break
                if len(rows) >= max_rows:
                    break
            if len(rows) >= max_rows:
                break

        feature_columns = [
            'rsi', 'atr_percent', 'trend_strength', 'price_above_sma50', 'sma20_above_sma50',
            'volume_confirmation', 'probability_long', 'probability_short', 'probability_neutral',
            'confidence_score', 'risk_score', 'crv', 'signal_score',
        ]
        return {
            'rows': rows,
            'row_count': len(rows),
            'feature_columns': feature_columns,
            'target_columns': ['future_return_percent', 'target_label'],
            'csv': self._rows_to_csv(rows),
            'note': 'Zielvariable: future_return_percent nach lookahead_bars; target_label 1=up, 0=neutral, -1=down.',
        }

    def walk_forward(
        self,
        symbol: str,
        timeframe: str,
        strategy_name: str,
        limit: int,
        initial_capital: float,
        splits: int = 3,
        min_warmup_bars: int = 80,
    ) -> dict[str, Any]:
        candles = self.market_data_service.get_candles(symbol=symbol, timeframe=timeframe, limit=limit)
        if len(candles) < (min_warmup_bars + splits * 25):
            raise ValueError('Not enough candles for walk-forward test')

        available = len(candles) - min_warmup_bars
        segment_size = max(25, available // splits)
        windows: list[dict[str, Any]] = []
        rolling_equity = float(initial_capital)

        for split_index in range(splits):
            test_start = min_warmup_bars + split_index * segment_size
            test_end = len(candles) if split_index == splits - 1 else min(len(candles), test_start + segment_size)
            if test_end - test_start < 10:
                continue
            # Include warmup data before the test segment so indicators are valid,
            # but label the run as out-of-sample because trades begin after warmup.
            segment = candles[:test_end]
            config = BacktestConfig(
                symbol=symbol,
                timeframe=timeframe,
                limit=len(segment),
                initial_capital=rolling_equity,
                strategy_name=strategy_name,
                max_hold_bars=self._default_hold_bars(strategy_name),
                min_warmup_bars=test_start,
            )
            result = self._run_on_candles(config=config, candles=segment, sample_label=f'walk_forward_{split_index + 1}')
            rolling_equity = float(result['final_equity'])
            windows.append({
                'window': split_index + 1,
                'test_start_time': candles[test_start]['timestamp'],
                'test_end_time': candles[test_end - 1]['timestamp'],
                'initial_capital': result['initial_capital'],
                'final_equity': result['final_equity'],
                'metrics': result['metrics'],
                'trades': result['trades'],
                'signals_count': result['signals_count'],
                'blocked_signals_count': result['blocked_signals_count'],
            })

        aggregate_trades = [trade for window in windows for trade in window.get('trades', [])]
        aggregate_curve = [{'timestamp': candles[min_warmup_bars - 1]['timestamp'], 'equity': round(initial_capital, 2), 'event': 'start'}]
        for window in windows:
            aggregate_curve.append({
                'timestamp': window['test_end_time'],
                'equity': round(float(window['final_equity']), 2),
                'event': f'window_{window["window"]}',
            })
        aggregate_metrics = self._calculate_metrics(aggregate_trades, aggregate_curve, initial_capital, rolling_equity)
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'strategy': strategy_name,
            'sample': 'walk_forward',
            'splits': splits,
            'initial_capital': round(initial_capital, 2),
            'final_equity': round(rolling_equity, 2),
            'windows': windows,
            'metrics': aggregate_metrics,
            'equity_curve': aggregate_curve,
        }

    def _run_on_candles(self, config: BacktestConfig, candles: list[dict[str, Any]], sample_label: str) -> dict[str, Any]:
        config.strategy_name = self.strategy_engine.resolve_strategy_name(config.strategy_name)
        if config.strategy_name not in StrategyEngine.STRATEGIES:
            raise ValueError(f'Unknown strategy: {config.strategy_name}')
        if len(candles) < config.min_warmup_bars + 2:
            raise ValueError('Not enough candle data for backtest')

        max_hold_bars = config.max_hold_bars or self._default_hold_bars(config.strategy_name)
        equity = float(config.initial_capital)
        equity_curve: list[dict[str, Any]] = [
            {'timestamp': candles[config.min_warmup_bars - 1]['timestamp'], 'equity': round(equity, 2), 'event': 'start'}
        ]
        trades: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        predictions_count = 0
        signal_count = 0
        i = config.min_warmup_bars

        while i < len(candles) - 2:
            lookback = candles[: i + 1]
            indicators = self.indicator_service.calculate(lookback)
            prediction = self.ai_prediction_service.predict(
                symbol=config.symbol,
                timeframe=config.timeframe,
                indicators=indicators,
            )
            predictions_count += 1
            signal = self.strategy_engine.create_signal(
                prediction=prediction,
                indicators=indicators,
                strategy_name=config.strategy_name,
                strategy_params=config.strategy_params,
            )

            if signal is None:
                i += 1
                continue

            signal_count += 1
            allowed, reason = self._validate_signal(signal, prediction, config)
            if not allowed:
                blocked.append({
                    'timestamp': candles[i]['timestamp'],
                    'reason': reason,
                    'strategy': config.strategy_name,
                    'signal_type': signal.get('signal_type'),
                    'confidence_score': prediction.get('confidence_score'),
                    'risk_score': prediction.get('risk_score'),
                    'crv': signal.get('crv'),
                })
                i += 1
                continue

            trade, exit_index = self._simulate_trade(
                candles=candles,
                start_index=i,
                signal=signal,
                equity=equity,
                config=config,
                prediction=prediction,
                max_hold_bars=max_hold_bars,
            )
            equity += trade['pnl_amount']
            trade['equity_after'] = round(equity, 2)
            trades.append(trade)
            equity_curve.append({
                'timestamp': trade['exit_time'],
                'equity': round(equity, 2),
                'event': trade['exit_reason'],
            })
            i = max(exit_index + 1, i + 1)

        metrics = self._calculate_metrics(trades, equity_curve, config.initial_capital, equity)
        return {
            'symbol': config.symbol,
            'timeframe': config.timeframe,
            'strategy': config.strategy_name,
            'strategy_label': StrategyEngine.STRATEGIES[config.strategy_name].label,
            'strategy_params': config.strategy_params,
            'sample': sample_label,
            'initial_capital': round(config.initial_capital, 2),
            'final_equity': round(equity, 2),
            'risk_per_trade': config.risk_per_trade,
            'max_hold_bars': max_hold_bars,
            'candles_used': len(candles),
            'predictions_count': predictions_count,
            'signals_count': signal_count,
            'blocked_signals_count': len(blocked),
            'trades': trades,
            'blocked_signals': blocked[:100],
            'equity_curve': equity_curve,
            'metrics': metrics,
        }

    def _default_hold_bars(self, strategy_name: str) -> int:
        strategy_name = self.strategy_engine.resolve_strategy_name(strategy_name)
        definition = StrategyEngine.STRATEGIES.get(strategy_name)
        if definition:
            return definition.default_max_hold_bars
        return 48

    def _validate_signal(self, signal: dict[str, Any], prediction: dict[str, Any], config: BacktestConfig) -> tuple[bool, str]:
        config.strategy_name = self.strategy_engine.resolve_strategy_name(config.strategy_name)
        definition = StrategyEngine.STRATEGIES.get(config.strategy_name)
        min_confidence = min(config.min_confidence_score, definition.min_confidence if definition else config.min_confidence_score)
        max_risk_score = max(config.max_risk_score, definition.max_risk_score if definition else config.max_risk_score)
        if float(signal.get('crv') or 0.0) < config.min_crv:
            return False, 'CRV below minimum'
        if float(prediction.get('confidence_score') or 0.0) < min_confidence:
            return False, 'Confidence below strategy minimum'
        if float(prediction.get('risk_score') or 100.0) > max_risk_score:
            return False, 'Risk score above strategy maximum'
        if float(signal.get('entry_price') or 0.0) <= 0:
            return False, 'Invalid entry price'
        if abs(float(signal['entry_price']) - float(signal['stop_loss'])) <= 0:
            return False, 'Invalid stop loss'
        return True, 'allowed'

    def _simulate_trade(
        self,
        candles: list[dict[str, Any]],
        start_index: int,
        signal: dict[str, Any],
        equity: float,
        config: BacktestConfig,
        prediction: dict[str, Any],
        max_hold_bars: int,
    ) -> tuple[dict[str, Any], int]:
        entry_price = float(signal['entry_price'])
        stop_loss = float(signal['stop_loss'])
        take_profit = float(signal['take_profit'])
        side = signal['signal_type']
        risk_per_unit = abs(entry_price - stop_loss)
        max_risk_amount = equity * float(config.risk_per_trade)
        quantity = max_risk_amount / risk_per_unit if risk_per_unit else 0.0

        exit_price = float(candles[start_index]['close'])
        exit_reason = 'closed_max_hold'
        exit_index = min(start_index + max_hold_bars, len(candles) - 1)

        for j in range(start_index + 1, min(len(candles), start_index + max_hold_bars + 1)):
            candle = candles[j]
            high = float(candle['high'])
            low = float(candle['low'])
            close = float(candle['close'])

            if side == 'long':
                stop_hit = low <= stop_loss
                target_hit = high >= take_profit
                if stop_hit and target_hit:
                    exit_price = stop_loss
                    exit_reason = 'closed_ambiguous_stop_first'
                    exit_index = j
                    break
                if stop_hit:
                    exit_price = stop_loss
                    exit_reason = 'closed_stop_loss'
                    exit_index = j
                    break
                if target_hit:
                    exit_price = take_profit
                    exit_reason = 'closed_take_profit'
                    exit_index = j
                    break
                exit_price = close
                exit_index = j
            else:
                stop_hit = high >= stop_loss
                target_hit = low <= take_profit
                if stop_hit and target_hit:
                    exit_price = stop_loss
                    exit_reason = 'closed_ambiguous_stop_first'
                    exit_index = j
                    break
                if stop_hit:
                    exit_price = stop_loss
                    exit_reason = 'closed_stop_loss'
                    exit_index = j
                    break
                if target_hit:
                    exit_price = take_profit
                    exit_reason = 'closed_take_profit'
                    exit_index = j
                    break
                exit_price = close
                exit_index = j

        if side == 'long':
            pnl_amount = (exit_price - entry_price) * quantity
            pnl_percent = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_amount = (entry_price - exit_price) * quantity
            pnl_percent = (entry_price - exit_price) / entry_price * 100

        return {
            'symbol': config.symbol,
            'timeframe': config.timeframe,
            'strategy': config.strategy_name,
            'side': side,
            'entry_time': candles[start_index]['timestamp'],
            'exit_time': candles[exit_index]['timestamp'],
            'entry_price': round(entry_price, 6),
            'exit_price': round(exit_price, 6),
            'stop_loss': round(stop_loss, 6),
            'take_profit': round(take_profit, 6),
            'quantity': round(quantity, 8),
            'risk_amount': round(max_risk_amount, 2),
            'pnl_amount': round(pnl_amount, 2),
            'pnl_percent': round(pnl_percent, 2),
            'exit_reason': exit_reason,
            'confidence_score': round(float(prediction.get('confidence_score') or 0), 2),
            'risk_score': round(float(prediction.get('risk_score') or 0), 2),
            'crv': round(float(signal.get('crv') or 0), 2),
        }, exit_index

    def _calculate_metrics(
        self,
        trades: list[dict[str, Any]],
        equity_curve: list[dict[str, Any]],
        initial_capital: float,
        final_equity: float,
    ) -> dict[str, Any]:
        closed_count = len(trades)
        wins = [trade for trade in trades if float(trade.get('pnl_amount') or 0) > 0]
        losses = [trade for trade in trades if float(trade.get('pnl_amount') or 0) < 0]
        gross_profit = sum(float(trade.get('pnl_amount') or 0) for trade in wins)
        gross_loss = sum(float(trade.get('pnl_amount') or 0) for trade in losses)
        gross_loss_abs = abs(gross_loss)
        total_pnl = gross_profit + gross_loss

        peak = initial_capital
        max_drawdown = 0.0
        for point in equity_curve:
            equity = float(point['equity'])
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        max_drawdown_percent = (max_drawdown / peak * 100) if peak else 0.0

        return {
            'total_trades': closed_count,
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate_percent': round(len(wins) / closed_count * 100, 2) if closed_count else 0.0,
            'gross_profit': round(gross_profit, 2),
            'gross_loss': round(gross_loss, 2),
            'profit_factor': round(gross_profit / gross_loss_abs, 4) if gross_loss_abs else None,
            'average_win': round(gross_profit / len(wins), 2) if wins else 0.0,
            'average_loss': round(gross_loss / len(losses), 2) if losses else 0.0,
            'expectancy_per_trade': round(total_pnl / closed_count, 2) if closed_count else 0.0,
            'total_pnl': round(total_pnl, 2),
            'return_percent': round((final_equity - initial_capital) / initial_capital * 100, 2) if initial_capital else 0.0,
            'max_drawdown_amount': round(max_drawdown, 2),
            'max_drawdown_percent': round(max_drawdown_percent, 2),
            'final_equity': round(final_equity, 2),
        }


    def _optimization_score(self, metrics: dict[str, Any], objective: str) -> float:
        return_percent = float(metrics.get('return_percent') or 0.0)
        profit_factor = float(metrics.get('profit_factor') or 0.0)
        drawdown = float(metrics.get('max_drawdown_percent') or 0.0)
        trades = float(metrics.get('total_trades') or 0.0)
        expectancy = float(metrics.get('expectancy_per_trade') or 0.0)
        if objective == 'return_percent':
            return return_percent
        if objective == 'profit_factor':
            return profit_factor
        if objective == 'expectancy_per_trade':
            return expectancy
        # Robust default: reward return/profit factor/trade count, penalise drawdown
        trade_penalty = 10.0 if trades < 5 else 0.0
        return round(return_percent + (profit_factor * 3.0) - (drawdown * 1.25) - trade_penalty, 6)

    def _rows_to_csv(self, rows: list[dict[str, Any]]) -> str:
        if not rows:
            return ''
        output = io.StringIO()
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()
