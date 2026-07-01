from fastapi import APIRouter, Query

from app.config import settings
from app.repositories.trading_repository import trading_repository
from app.schemas.bot_schema import BotConfigPatch, BotRunRequest, BotStatusResponse, ManualCloseOrderRequest
from app.services.bot_engine import BotEngine
from app.services.bot_runtime_service import bot_runtime_service
from app.services.bot_scheduler_service import bot_scheduler_service
from app.services.journal_service import journal_service
from app.services.local_persistence_service import local_persistence_service
from app.services.validation_monitoring_service import validation_monitoring_service

router = APIRouter()


@router.get('/status', response_model=BotStatusResponse)
def get_bot_status():
    config = bot_runtime_service.get_config()
    return {
        'status': 'paper_only_kill_switch' if config.get('kill_switch_active') else 'paper_only',
        'mode': 'paper',
        'live_trading_enabled': False,
        'max_risk_per_trade': config.get('max_risk_per_trade', settings.max_risk_per_trade),
        'max_daily_loss': config.get('max_daily_loss', settings.max_daily_loss),
        'max_open_trades': config.get('max_open_trades', settings.max_open_trades),
        'min_crv': config.get('min_crv', settings.min_crv),
        'min_confidence_score': config.get('min_confidence_score', settings.min_confidence_score),
        'max_risk_score': config.get('max_risk_score', settings.max_risk_score),
        'supported_decision_modes': ['rule', 'ml', 'ensemble'],
        'default_decision_mode': config.get('decision_mode', 'rule'),
        'validation_gate': {
            'enforce_validation_gate': bool(config.get('enforce_validation_gate')),
            'min_closed_trades_for_release': config.get('min_closed_trades_for_release'),
            'min_profit_factor_for_release': config.get('min_profit_factor_for_release'),
            'min_win_rate_for_release': config.get('min_win_rate_for_release'),
            'max_drawdown_percent_for_release': config.get('max_drawdown_percent_for_release'),
            'min_expectancy_per_trade_for_release': config.get('min_expectancy_per_trade_for_release'),
            'min_data_quality_score_for_release': config.get('min_data_quality_score_for_release'),
        },
        'paper_execution_model': {
            'spread_bps': settings.paper_spread_bps,
            'slippage_bps': settings.paper_slippage_bps,
            'commission_bps': settings.paper_commission_bps,
            'min_commission': settings.paper_min_commission,
        },
    }


@router.get('/persistence')
def get_persistence_status():
    return {
        'database_configured': trading_repository.enabled,
        'database_reachable': trading_repository.available if trading_repository.enabled else False,
        'local_file': local_persistence_service.status(),
    }


@router.get('/config')
def get_bot_config():
    return bot_runtime_service.get_config()


@router.patch('/config')
def update_bot_config(request: BotConfigPatch):
    return bot_runtime_service.update_config(request.model_dump(exclude_unset=True))


@router.post('/enable')
def enable_bot():
    return bot_runtime_service.update_config({'bot_enabled': True})


@router.post('/disable')
def disable_bot():
    return bot_runtime_service.update_config({'bot_enabled': False, 'scheduler_enabled': False})


@router.post('/kill-switch/reset')
def reset_kill_switch():
    return bot_runtime_service.reset_kill_switch()


@router.get('/scheduler/status')
def get_scheduler_status():
    return bot_scheduler_service.status()


@router.post('/scheduler/start')
def start_scheduler():
    return bot_scheduler_service.start()


@router.post('/scheduler/stop')
def stop_scheduler():
    return bot_scheduler_service.stop()


@router.post('/scheduler/run-once')
def run_scheduler_once():
    return bot_scheduler_service.run_once(source='manual')


@router.get('/scheduler/runs')
def get_scheduler_runs(limit: int = Query(default=25, ge=1, le=200)):
    return bot_scheduler_service.list_runs(limit=limit)


@router.post('/run-cycle')
def run_bot_cycle(request: BotRunRequest):
    engine = BotEngine()
    return engine.run_cycle(
        symbol=request.symbol,
        timeframe=request.timeframe,
        portfolio_value=request.portfolio_value,
        open_trades_count=request.open_trades_count,
        daily_pnl_percent=request.daily_pnl_percent,
        strategy_name=request.strategy_name,
        decision_mode=request.decision_mode,
        model_id=request.model_id,
        min_ml_probability=request.min_ml_probability,
        min_model_profit_factor=request.min_model_profit_factor,
        min_model_win_rate=request.min_model_win_rate,
        allow_degraded_fallback=request.allow_degraded_fallback,
    )


@router.get('/journal')
def get_bot_journal():
    if trading_repository.available:
        persisted = {
            'predictions': trading_repository.list_predictions(limit=25),
            'signals': trading_repository.list_signals(limit=25),
            'orders': trading_repository.list_paper_orders(limit=25),
            'risk_events': trading_repository.list_risk_events(limit=25),
        }
    else:
        persisted = {'predictions': [], 'signals': [], 'orders': local_persistence_service.list_orders(limit=25), 'risk_events': []}
    return {
        'in_memory_events': journal_service.list_events(),
        'persisted': persisted,
    }


@router.get('/signals')
def get_bot_signals(limit: int = Query(default=50, ge=1, le=200)):
    if not trading_repository.available:
        return {'items': [], 'persistence': 'memory'}
    return {'items': trading_repository.list_signals(limit=limit), 'persistence': 'postgres'}


@router.get('/orders')
def get_paper_orders(status: str | None = None, limit: int = Query(default=100, ge=1, le=500)):
    if not trading_repository.available:
        return {'items': local_persistence_service.list_orders(status=status, limit=limit), 'persistence': 'local_file'}
    return {'items': trading_repository.list_paper_orders(status=status, limit=limit), 'persistence': 'postgres'}


@router.get('/predictions')
def get_predictions(limit: int = Query(default=50, ge=1, le=200)):
    if not trading_repository.available:
        return {'items': [], 'persistence': 'memory'}
    return {'items': trading_repository.list_predictions(limit=limit), 'persistence': 'postgres'}


@router.get('/risk-events')
def get_risk_events(limit: int = Query(default=50, ge=1, le=200)):
    if not trading_repository.available:
        return {'items': [], 'persistence': 'memory'}
    return {'items': trading_repository.list_risk_events(limit=limit), 'persistence': 'postgres'}


@router.post('/evaluate-open-orders')
def evaluate_open_orders():
    engine = BotEngine()
    return engine.evaluate_open_orders()


@router.post('/close-order/{order_id}')
def close_order(order_id: str, request: ManualCloseOrderRequest | None = None):
    request = request or ManualCloseOrderRequest()
    engine = BotEngine()
    return engine.close_order(order_id=order_id, exit_price=request.exit_price, reason=request.reason)


@router.get('/portfolio-snapshot')
def get_portfolio_snapshot():
    return BotEngine().portfolio_snapshot()


@router.get('/performance')
def get_performance():
    if not trading_repository.available:
        return local_persistence_service.performance_summary()
    return trading_repository.performance_summary()




@router.get('/validation-gates')
def get_bot_validation_gates(strategy_name: str | None = None, decision_mode: str | None = None):
    return validation_monitoring_service.validation_gates(strategy_name=strategy_name, decision_mode=decision_mode)

@router.get('/model-health')
def get_model_health(
    model_id: str | None = None,
    min_profit_factor: float = Query(default=1.0, ge=0.0),
    min_win_rate: float = Query(default=45.0, ge=0.0, le=100.0),
):
    return BotEngine().model_health(model_id=model_id, min_profit_factor=min_profit_factor, min_win_rate=min_win_rate)


@router.get('/performance-by-mode')
def get_performance_by_mode():
    if not trading_repository.available:
        return {'items': [], 'persistence': 'memory'}
    return {'items': trading_repository.performance_by_decision_mode(), 'persistence': 'postgres'}


@router.get('/decision-audits')
def get_decision_audits(limit: int = Query(default=100, ge=1, le=500)):
    if not trading_repository.available:
        return {'items': [], 'persistence': 'memory'}
    return {'items': trading_repository.list_decision_audits(limit=limit), 'persistence': 'postgres'}


@router.get('/equity-curve')
def get_equity_curve():
    return trading_repository.equity_curve_from_orders() if trading_repository.available else local_persistence_service.equity_curve()


@router.post('/kill-switch')
def activate_kill_switch():
    config = bot_runtime_service.activate_kill_switch()
    try:
        bot_scheduler_service.stop()
    except Exception:
        pass
    return {
        'status': 'kill_switch_activated',
        'message': 'Neue Bot-Trades wurden deaktiviert. Live-Trading ist in diesem MVP grundsaetzlich gesperrt.',
        'config': config,
    }
