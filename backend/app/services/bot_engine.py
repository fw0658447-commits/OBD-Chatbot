from __future__ import annotations

from typing import Any

from app.config import settings
from app.repositories.trading_repository import trading_repository
from app.services.ai_prediction_service import AIPredictionService
from app.services.bot_decision_service import BotDecisionService
from app.services.bot_runtime_service import bot_runtime_service
from app.services.data_quality_service import data_quality_service
from app.services.indicator_service import IndicatorService
from app.services.journal_service import journal_service
from app.services.local_persistence_service import local_persistence_service
from app.services.market_data_service import get_market_data_service
from app.services.ml_training_service import MLTrainingService
from app.services.paper_trading_engine import PaperTradingEngine
from app.services.risk_engine import RiskEngine
from app.services.strategy_engine import StrategyEngine
from app.services.validation_monitoring_service import validation_monitoring_service


class BotEngine:
    def __init__(self):
        self.market_data_service = get_market_data_service()
        self.indicator_service = IndicatorService()
        self.ai_prediction_service = AIPredictionService()
        self.strategy_engine = StrategyEngine()
        self.risk_engine = RiskEngine()
        self.paper_trading_engine = PaperTradingEngine()
        self.journal_service = journal_service
        self.repository = trading_repository
        self.decision_service = BotDecisionService()

    def run_cycle(
        self,
        symbol: str,
        timeframe: str,
        portfolio_value: float,
        open_trades_count: int,
        daily_pnl_percent: float,
        strategy_name: str = StrategyEngine.DEFAULT_STRATEGY,
        decision_mode: str = 'rule',
        model_id: str | None = None,
        min_ml_probability: float = 0.52,
        min_model_profit_factor: float = 1.0,
        min_model_win_rate: float = 45.0,
        allow_degraded_fallback: bool = True,
    ) -> dict:
        runtime_config = bot_runtime_service.get_config()
        if runtime_config.get('kill_switch_active'):
            if self.repository.available:
                self.repository.log_risk_event(
                    event_type='cycle_blocked_kill_switch',
                    severity='critical',
                    message=f'{symbol} cycle blocked because Kill-Switch is active.',
                )
                self._audit_decision(
                    symbol=symbol,
                    timeframe=timeframe,
                    strategy=strategy_name,
                    decision_mode=decision_mode,
                    allowed=False,
                    reason='Kill-Switch is active.',
                    details={'runtime_config': runtime_config},
                )
            return {
                'status': 'blocked_by_kill_switch',
                'reason': 'Kill-Switch is active. Reset it before running paper bot cycles.',
                'runtime_config': runtime_config,
                'persistence': self._persistence_status(),
            }

        strategy_name = self.strategy_engine.resolve_strategy_name(strategy_name or runtime_config.get('strategy_name'))
        decision_mode = (decision_mode or runtime_config.get('decision_mode') or 'rule').lower().strip()
        effective_limits = {
            'live_trading_enabled': False,
            'max_risk_per_trade': runtime_config.get('max_risk_per_trade'),
            'max_daily_loss': runtime_config.get('max_daily_loss'),
            'max_open_trades': runtime_config.get('max_open_trades'),
            'min_crv': runtime_config.get('min_crv'),
            'min_confidence_score': runtime_config.get('min_confidence_score'),
            'max_risk_score': runtime_config.get('max_risk_score'),
        }

        candles = self.market_data_service.get_candles(symbol=symbol, timeframe=timeframe, limit=220)
        quote_for_provider = self.market_data_service.get_quote(symbol)
        provider = quote_for_provider.get('provider') or 'unknown'
        data_quality = data_quality_service.assess_candles(candles=candles, timeframe=timeframe, provider=provider)

        database_available = self.repository.available
        asset_id = self.repository.get_or_create_asset(symbol=symbol, provider=provider) if database_available else None
        data_quality_report_id = None
        if database_available:
            self.repository.upsert_market_candles(symbol=symbol, timeframe=timeframe, candles=candles, provider=provider)
            data_quality_report_id = self.repository.create_data_quality_report(symbol=symbol, timeframe=timeframe, provider=provider, report=data_quality)

        if settings.block_trades_on_data_quality_fail and (not data_quality.get('trade_allowed') or float(data_quality.get('quality_score') or 0) < settings.min_data_quality_score):
            if database_available:
                self.repository.log_risk_event(
                    event_type='data_quality_block',
                    severity='warning',
                    message=f'{symbol} {timeframe} blocked: data quality score {data_quality.get("quality_score")}',
                )
            self._audit_decision(
                symbol=symbol,
                timeframe=timeframe,
                strategy=strategy_name,
                decision_mode=decision_mode,
                allowed=False,
                reason='Data quality gate blocked this cycle.',
                details={'data_quality': data_quality, 'data_quality_report_id': data_quality_report_id},
            )
            return {
                'status': 'blocked_by_data_quality',
                'reason': 'Data quality gate blocked this cycle.',
                'symbol': symbol,
                'timeframe': timeframe,
                'strategy_name': strategy_name,
                'decision_mode': decision_mode,
                'data_quality': data_quality,
                'data_quality_report_id': data_quality_report_id,
                'persistence': self._persistence_status(),
            }

        indicators = self.indicator_service.calculate(candles)
        prediction = self.ai_prediction_service.predict(symbol=symbol, timeframe=timeframe, indicators=indicators)

        prediction_id = self.repository.create_prediction(asset_id=asset_id, prediction=prediction) if database_available else None

        if database_available:
            portfolio = self.repository.get_or_create_portfolio()
            if portfolio:
                portfolio_value = float(portfolio.get('current_equity') or portfolio_value)
            open_trades_count = self.repository.count_open_orders()
            daily_pnl_percent = self.repository.daily_pnl_percent()

        signal = self.strategy_engine.create_signal(prediction=prediction, indicators=indicators, strategy_name=strategy_name)
        ml_asset_result = self._safe_ml_prediction(
            enabled=decision_mode in {'ml', 'ensemble'},
            model_id=model_id,
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy_name,
        )
        decision = self.decision_service.decide(
            mode=decision_mode,
            signal=signal,
            rule_prediction=prediction,
            ml_asset_result=ml_asset_result,
            min_ml_probability=min_ml_probability,
            min_model_profit_factor=min_model_profit_factor,
            min_model_win_rate=min_model_win_rate,
            allow_degraded_fallback=allow_degraded_fallback,
        )

        if signal is None:
            self._audit_decision(
                symbol=symbol,
                timeframe=timeframe,
                strategy=strategy_name,
                decision_mode=decision_mode,
                allowed=False,
                reason=decision.reason,
                decision=decision.as_dict(),
                details={'prediction': prediction, 'ml_result': ml_asset_result},
            )
            return {
                'status': 'no_signal',
                'symbol': symbol,
                'timeframe': timeframe,
                'strategy_name': strategy_name,
                'decision_mode': decision_mode,
                'indicators': indicators,
                'data_quality': data_quality,
                'data_quality_report_id': data_quality_report_id,
                'prediction': prediction,
                'prediction_id': prediction_id,
                'ml_result': ml_asset_result,
                'decision': decision.as_dict(),
                'persistence': self._persistence_status(),
            }

        signal['decision_mode'] = decision.mode
        signal['decision_score'] = decision.decision_score
        signal['model_source'] = decision.model_source
        signal['ml_model_id'] = decision.ml_model_id
        signal['ml_direction'] = decision.ml_direction
        signal['ml_probability'] = decision.ml_probability
        signal['decision_details'] = decision.as_dict()

        if not decision.allowed:
            signal_id = None
            if database_available:
                signal_id = self.repository.create_signal(
                    asset_id=asset_id,
                    prediction_id=prediction_id,
                    signal=signal,
                    status='blocked',
                    reason=decision.reason,
                )
                self.repository.log_risk_event(
                    event_type='decision_blocked',
                    severity='warning',
                    message=f'{symbol} {signal["signal_type"]} blocked by {decision.mode}: {decision.reason}',
                )
            self.journal_service.log_blocked_signal(signal=signal, prediction=prediction, reason=decision.reason)
            self._audit_decision(
                symbol=symbol,
                timeframe=timeframe,
                strategy=strategy_name,
                decision_mode=decision.mode,
                allowed=False,
                reason=decision.reason,
                decision=decision.as_dict(),
                details={'signal': signal, 'prediction': prediction, 'ml_result': ml_asset_result},
            )
            return {
                'status': 'blocked_by_decision',
                'reason': decision.reason,
                'symbol': symbol,
                'timeframe': timeframe,
                'strategy_name': strategy_name,
                'decision_mode': decision_mode,
                'signal': signal,
                'signal_id': signal_id,
                'data_quality': data_quality,
                'data_quality_report_id': data_quality_report_id,
                'prediction': prediction,
                'prediction_id': prediction_id,
                'ml_result': ml_asset_result,
                'decision': decision.as_dict(),
                'persistence': self._persistence_status(),
            }

        risk_result = self.risk_engine.validate(
            signal=signal,
            prediction=prediction,
            portfolio_value=portfolio_value,
            open_trades_count=open_trades_count,
            daily_pnl_percent=daily_pnl_percent,
            limits=effective_limits,
        )

        if not risk_result.allowed:
            signal_id = None
            if database_available:
                signal_id = self.repository.create_signal(
                    asset_id=asset_id,
                    prediction_id=prediction_id,
                    signal=signal,
                    status='blocked',
                    reason=risk_result.reason,
                )
                self.repository.log_risk_event(
                    event_type='signal_blocked',
                    severity='warning',
                    message=f'{symbol} {signal["signal_type"]} blocked by risk engine: {risk_result.reason}',
                )
            self.journal_service.log_blocked_signal(signal=signal, prediction=prediction, reason=risk_result.reason)
            self._audit_decision(
                symbol=symbol,
                timeframe=timeframe,
                strategy=strategy_name,
                decision_mode=decision.mode,
                allowed=False,
                reason=risk_result.reason,
                decision=decision.as_dict(),
                details={'signal': signal, 'prediction': prediction, 'risk': risk_result.__dict__},
            )
            return {
                'status': 'blocked',
                'reason': risk_result.reason,
                'symbol': symbol,
                'timeframe': timeframe,
                'strategy_name': strategy_name,
                'decision_mode': decision_mode,
                'signal': signal,
                'signal_id': signal_id,
                'data_quality': data_quality,
                'data_quality_report_id': data_quality_report_id,
                'prediction': prediction,
                'prediction_id': prediction_id,
                'ml_result': ml_asset_result,
                'decision': decision.as_dict(),
                'risk': risk_result.__dict__,
                'persistence': self._persistence_status(),
            }

        if runtime_config.get('enforce_validation_gate'):
            gate_status = validation_monitoring_service.validation_gates(
                strategy_name=strategy_name,
                decision_mode=decision.mode,
            )
            if not gate_status.get('released_for_paper_automation'):
                if database_available:
                    self.repository.log_risk_event(
                        event_type='validation_gate_block',
                        severity='critical',
                        message=f'{symbol} blocked by validation gate: {gate_status.get("recommendation")}',
                    )
                    self.repository.create_signal(
                        asset_id=asset_id,
                        prediction_id=prediction_id,
                        signal=signal,
                        status='blocked',
                        reason='Validation gate is enforced and the strategy is not released.',
                    )
                self._audit_decision(
                    symbol=symbol,
                    timeframe=timeframe,
                    strategy=strategy_name,
                    decision_mode=decision.mode,
                    allowed=False,
                    reason='Validation gate is enforced and the strategy is not released.',
                    decision=decision.as_dict(),
                    details={'signal': signal, 'prediction': prediction, 'validation_gate': gate_status},
                )
                return {
                    'status': 'blocked_by_validation_gate',
                    'reason': 'Validation gate is enforced and the strategy is not released.',
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'strategy_name': strategy_name,
                    'decision_mode': decision.mode,
                    'validation_gate': gate_status,
                    'signal': signal,
                    'prediction': prediction,
                    'prediction_id': prediction_id,
                    'decision': decision.as_dict(),
                    'risk': risk_result.__dict__,
                    'persistence': self._persistence_status(),
                }

        signal_id = None
        if database_available:
            signal_id = self.repository.create_signal(
                asset_id=asset_id,
                prediction_id=prediction_id,
                signal=signal,
                status='executed',
                reason=f'{decision.reason} {risk_result.reason}',
            )
        order = self.paper_trading_engine.execute_order(signal=signal, quantity=risk_result.quantity)
        order.update({
            'decision_mode': decision.mode,
            'decision_score': decision.decision_score,
            'model_source': decision.model_source,
            'ml_model_id': decision.ml_model_id,
            'ml_direction': decision.ml_direction,
            'ml_probability': decision.ml_probability,
            'decision_details': {**decision.as_dict(), 'strategy_name': strategy_name},
        })
        order_id = self.repository.create_paper_order(asset_id=asset_id, signal_id=signal_id, order=order) if database_available else None
        if order_id:
            order['id'] = order_id
        self.journal_service.log_executed_paper_order(order=order, signal=signal, prediction=prediction)
        self._audit_decision(
            symbol=symbol,
            timeframe=timeframe,
            strategy=strategy_name,
            decision_mode=decision.mode,
            allowed=True,
            reason=f'{decision.reason} {risk_result.reason}',
            decision=decision.as_dict(),
            details={'signal': signal, 'prediction': prediction, 'risk': risk_result.__dict__, 'order': order},
        )

        return {
            'status': 'paper_order_executed',
            'symbol': symbol,
            'timeframe': timeframe,
            'strategy_name': strategy_name,
            'decision_mode': decision_mode,
            'order': order,
            'order_id': order_id,
            'data_quality': data_quality,
            'data_quality_report_id': data_quality_report_id,
            'signal': signal,
            'signal_id': signal_id,
            'prediction': prediction,
            'prediction_id': prediction_id,
            'ml_result': ml_asset_result,
            'decision': decision.as_dict(),
            'risk': risk_result.__dict__,
            'persistence': self._persistence_status(),
        }

    def model_health(self, model_id: str | None = None, min_profit_factor: float = 1.0, min_win_rate: float = 45.0) -> dict[str, Any]:
        try:
            service = MLTrainingService()
            models = service.list_models()
            if not models:
                return {'status': 'no_model', 'healthy': False, 'reason': 'No trained ML model available.'}
            metadata = next((item for item in models if item.get('model_id') == model_id), models[0])
            health = self.decision_service.model_health(metadata, min_profit_factor, min_win_rate)
            return {'status': 'ok', 'selected_model': metadata, 'health': health}
        except Exception as exc:
            return {'status': 'error', 'healthy': False, 'reason': str(exc)}

    def evaluate_open_orders(self) -> dict:
        if not self.repository.available:
            evaluated: list[dict] = []
            open_orders = local_persistence_service.list_orders(status='open', limit=500)
            for order in open_orders:
                quote = self.market_data_service.get_quote(order['symbol'])
                current_price = float(quote['price'])
                updated = self.paper_trading_engine.evaluate_open_order(order=order, current_price=current_price)
                if updated.get('status') != order.get('status'):
                    stored = local_persistence_service.close_order(order_id=order['id'], closed_order=updated)
                    evaluated.append({
                        'symbol': order['symbol'],
                        'order_id': order['id'],
                        'current_price': current_price,
                        'status': updated['status'],
                        'pnl_amount': updated.get('pnl_amount'),
                        'pnl_percent': updated.get('pnl_percent'),
                        'stored': stored,
                    })
                else:
                    mark = self.paper_trading_engine.mark_to_market(order=order, current_price=current_price)
                    evaluated.append({
                        'symbol': order['symbol'],
                        'order_id': order['id'],
                        'current_price': current_price,
                        'status': 'still_open',
                        'unrealized_pnl_amount': mark.get('unrealized_pnl_amount'),
                        'unrealized_pnl_percent': mark.get('unrealized_pnl_percent'),
                    })

            snapshot = self.portfolio_snapshot()
            return {
                'status': 'evaluated',
                'count': len(evaluated),
                'evaluated': evaluated,
                'portfolio': snapshot.get('portfolio'),
                'performance': snapshot.get('performance'),
                'persistence': 'local_file',
            }

        evaluated: list[dict] = []
        open_orders = self.repository.list_paper_orders(status='open', limit=500)
        for order in open_orders:
            quote = self.market_data_service.get_quote(order['symbol'])
            current_price = float(quote['price'])
            updated = self.paper_trading_engine.evaluate_open_order(order=order, current_price=current_price)
            if updated.get('status') != order.get('status'):
                stored = self.repository.close_paper_order(order_id=order['id'], closed_order=updated)
                self.repository.log_risk_event(
                    event_type='paper_order_closed',
                    severity='info',
                    message=f'{order["symbol"]} {order["side"]} closed as {updated["status"]} with P/L {updated.get("pnl_amount")}',
                )
                evaluated.append({
                    'symbol': order['symbol'],
                    'order_id': order['id'],
                    'current_price': current_price,
                    'status': updated['status'],
                    'pnl_amount': updated.get('pnl_amount'),
                    'pnl_percent': updated.get('pnl_percent'),
                    'decision_mode': order.get('decision_mode'),
                    'stored': stored,
                })
            else:
                mark = self.paper_trading_engine.mark_to_market(order=order, current_price=current_price)
                evaluated.append({
                    'symbol': order['symbol'],
                    'order_id': order['id'],
                    'current_price': current_price,
                    'status': 'still_open',
                    'unrealized_pnl_amount': mark.get('unrealized_pnl_amount'),
                    'unrealized_pnl_percent': mark.get('unrealized_pnl_percent'),
                    'decision_mode': order.get('decision_mode'),
                })

        snapshot = self.portfolio_snapshot()
        return {
            'status': 'evaluated',
            'count': len(evaluated),
            'evaluated': evaluated,
            'portfolio': snapshot.get('portfolio'),
            'performance': snapshot.get('performance'),
        }

    def close_order(self, order_id: str, exit_price: float | None = None, reason: str = 'closed_manual') -> dict:
        if not self.repository.available:
            order = local_persistence_service.get_order(order_id=order_id)
            if order is None:
                return {'status': 'not_found', 'order_id': order_id, 'persistence': 'local_file'}
            if order.get('status') != 'open':
                return {'status': 'not_open', 'order': order, 'persistence': 'local_file'}
            if exit_price is None:
                quote = self.market_data_service.get_quote(order['symbol'])
                exit_price = float(quote['price'])
            updated = self.paper_trading_engine.close_order(order=order, exit_price=exit_price, status=reason)
            stored = local_persistence_service.close_order(order_id=order_id, closed_order=updated)
            return {
                'status': 'closed',
                'order_id': order_id,
                'closed_order': stored,
                'portfolio_snapshot': self.portfolio_snapshot(),
                'persistence': 'local_file',
            }
        order = self.repository.get_paper_order(order_id=order_id)
        if order is None:
            return {'status': 'not_found', 'order_id': order_id}
        if order.get('status') != 'open':
            return {'status': 'not_open', 'order': order}
        if exit_price is None:
            quote = self.market_data_service.get_quote(order['symbol'])
            exit_price = float(quote['price'])
        updated = self.paper_trading_engine.close_order(order=order, exit_price=exit_price, status=reason)
        stored = self.repository.close_paper_order(order_id=order_id, closed_order=updated)
        self.repository.log_risk_event(
            event_type='paper_order_closed_manual',
            severity='info',
            message=f'{order["symbol"]} {order["side"]} manually closed with P/L {updated.get("pnl_amount")}',
        )
        return {
            'status': 'closed',
            'order_id': order_id,
            'closed_order': stored,
            'portfolio_snapshot': self.portfolio_snapshot(),
        }

    def portfolio_snapshot(self) -> dict:
        if not self.repository.available:
            return local_persistence_service.portfolio_snapshot(
                market_data_service=self.market_data_service,
                paper_trading_engine=self.paper_trading_engine,
            )

        positions: list[dict] = []
        total_unrealized = 0.0
        open_orders = self.repository.list_paper_orders(status='open', limit=500)
        for order in open_orders:
            quote = self.market_data_service.get_quote(order['symbol'])
            current_price = float(quote['price'])
            mark = self.paper_trading_engine.mark_to_market(order=order, current_price=current_price)
            total_unrealized += float(mark.get('unrealized_pnl_amount') or 0.0)
            positions.append(mark)

        portfolio = self.repository.update_unrealized_pnl(total_unrealized)
        summary = self.repository.portfolio_summary() or {}
        summary['positions'] = positions
        summary['open_orders_count'] = len(positions)
        return {
            'status': 'ok',
            'portfolio': summary if summary else portfolio,
            'positions': positions,
            'performance': self.repository.performance_summary(),
        }


    def _audit_decision(
        self,
        symbol: str,
        timeframe: str,
        strategy: str,
        decision_mode: str,
        allowed: bool,
        reason: str,
        decision: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ) -> str | None:
        if not self.repository.available:
            return None
        decision = decision or {}
        return self.repository.create_decision_audit({
            'symbol': symbol,
            'timeframe': timeframe,
            'strategy': strategy,
            'decision_mode': decision_mode,
            'model_source': decision.get('model_source'),
            'ml_model_id': decision.get('ml_model_id'),
            'allowed': allowed,
            'decision_score': decision.get('decision_score'),
            'reason': reason,
            'details': details or {},
        })

    def _safe_ml_prediction(
        self,
        enabled: bool,
        model_id: str | None,
        symbol: str,
        timeframe: str,
        strategy_name: str,
    ) -> dict[str, Any] | None:
        if not enabled:
            return None
        try:
            result = MLTrainingService().predict_asset(
                model_id=model_id,
                symbol=symbol,
                timeframe=timeframe,
                strategy_name=strategy_name,
                limit=220,
            )
            if self.repository.available:
                prediction_run_id = self.repository.create_ml_prediction_run(result)
                result['prediction_run_id'] = prediction_run_id
                result['persistence'] = 'postgres' if prediction_run_id else 'memory'
            return result
        except Exception as exc:
            return {
                'status': 'ml_unavailable',
                'error': str(exc),
                'note': 'Train a model with /api/ml/train before using ml or ensemble decision mode.',
            }

    def _persistence_status(self) -> dict:
        return {
            'database_configured': self.repository.enabled,
            'database_reachable': self.repository.available if self.repository.enabled else False,
        }
