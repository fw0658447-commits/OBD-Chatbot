from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import settings
from app.repositories.trading_repository import trading_repository
from app.services.bot_runtime_service import bot_runtime_service
from app.services.bot_engine import BotEngine
from app.services.local_persistence_service import local_persistence_service
from app.services.market_data_service import get_market_data_service
from app.services.paper_trading_engine import PaperTradingEngine

router = APIRouter()


class CashTransactionRequest(BaseModel):
    amount: float = Field(gt=0)
    note: str | None = None


class ResetPaperAccountRequest(BaseModel):
    balance: float = Field(default=10000, ge=0)
    note: str | None = None
    cancel_open_orders: bool = True


class ManualPaperOrderRequest(BaseModel):
    symbol: str
    side: str = Field(pattern='^(long|short)$')
    quantity: float | None = Field(default=None, gt=0)
    notional_amount: float | None = Field(default=None, gt=0)
    entry_price: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit: float | None = Field(default=None, gt=0)
    note: str | None = None


def _open_order_count() -> int:
    if not trading_repository.available:
        return len(local_persistence_service.list_orders(status='open', limit=500))
    return trading_repository.count_open_orders()


def _validate_manual_order_guard() -> dict:
    config = bot_runtime_service.get_config()
    if settings.bot_mode != 'paper' or settings.live_trading_enabled or not settings.live_trading_hard_locked:
        raise HTTPException(status_code=403, detail='Manuelle Orders sind nur im gesicherten Paper-Modus erlaubt.')
    if config.get('kill_switch_active'):
        raise HTTPException(status_code=423, detail='Schutzstopp ist aktiv. Manuelle Paper-Trades sind blockiert.')
    max_open_trades = int(config.get('max_open_trades') or settings.max_open_trades)
    open_orders = _open_order_count()
    if open_orders >= max_open_trades:
        raise HTTPException(status_code=429, detail=f'Positionslimit erreicht: {open_orders}/{max_open_trades} offene Trades.')
    return {'open_orders': open_orders, 'max_open_trades': max_open_trades}


def _manual_order_http_error(exc: ValueError) -> HTTPException:
    detail = str(exc)
    status_code = 429 if detail.startswith('Positionslimit erreicht:') else 400
    return HTTPException(status_code=status_code, detail=detail)


@router.get('/paper')
def get_paper_portfolio():
    if not trading_repository.available:
        return {
            **local_persistence_service.portfolio_summary(),
            'note': 'PostgreSQL ist nicht erreichbar. Das Backend nutzt lokale Dateiablage.',
        }
    snapshot = BotEngine().portfolio_snapshot()
    return snapshot.get('portfolio')


@router.get('/paper/orders')
def get_paper_orders(status: str | None = None):
    if not trading_repository.available:
        return {'items': local_persistence_service.list_orders(status=status, limit=200), 'persistence': 'local_file'}
    return {'items': trading_repository.list_paper_orders(status=status, limit=200), 'persistence': 'postgres'}


@router.get('/paper/performance')
def get_paper_performance():
    if not trading_repository.available:
        return local_persistence_service.performance_summary()
    return trading_repository.performance_summary()


@router.get('/paper/cash-ledger')
def get_cash_ledger(limit: int = Query(default=100, ge=1, le=500)):
    if not trading_repository.available:
        return {'items': local_persistence_service.list_cash_transactions(limit=limit), 'persistence': 'local_file'}
    return {'items': trading_repository.list_cash_transactions(limit=limit), 'persistence': 'postgres'}


@router.post('/paper/deposit')
def deposit_virtual_cash(request: CashTransactionRequest):
    if not trading_repository.available:
        result = local_persistence_service.add_cash_transaction('deposit', request.amount, request.note)
        return {'status': 'deposited', **result, 'persistence': 'local_file'}
    try:
        result = trading_repository.add_cash_transaction('deposit', request.amount, request.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {'status': 'deposited', **(result or {}), 'persistence': 'postgres'}


@router.post('/paper/withdraw')
def withdraw_virtual_cash(request: CashTransactionRequest):
    if not trading_repository.available:
        try:
            result = local_persistence_service.add_cash_transaction('withdrawal', request.amount, request.note)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {'status': 'withdrawn', **result, 'persistence': 'local_file'}
    try:
        result = trading_repository.add_cash_transaction('withdrawal', request.amount, request.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {'status': 'withdrawn', **(result or {}), 'persistence': 'postgres'}


@router.post('/paper/reset')
def reset_paper_account(request: ResetPaperAccountRequest):
    if not trading_repository.available:
        result = local_persistence_service.reset_paper_account(request.balance, request.note, request.cancel_open_orders)
        return {'status': 'reset', **result, 'persistence': 'local_file'}
    try:
        result = trading_repository.reset_paper_account(request.balance, request.note, request.cancel_open_orders)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {'status': 'reset', **(result or {}), 'persistence': 'postgres'}


@router.post('/paper/manual-order')
def create_manual_paper_order(request: ManualPaperOrderRequest):
    guard = _validate_manual_order_guard()
    symbol = request.symbol.strip().upper()
    market = get_market_data_service()
    quote = market.get_quote(symbol)
    requested_entry = float(request.entry_price or quote.get('price') or 0)
    if requested_entry <= 0:
        raise HTTPException(status_code=400, detail='Entry price is invalid.')
    quantity = request.quantity
    if quantity is None:
        if request.notional_amount is None:
            raise HTTPException(status_code=400, detail='Either quantity or notional_amount is required.')
        quantity = request.notional_amount / requested_entry
    stop_loss = request.stop_loss
    take_profit = request.take_profit
    if request.side == 'long':
        stop_loss = stop_loss or requested_entry * 0.98
        take_profit = take_profit or requested_entry * 1.04
    else:
        stop_loss = stop_loss or requested_entry * 1.02
        take_profit = take_profit or requested_entry * 0.96
    signal = {
        'signal_type': request.side,
        'entry_price': requested_entry,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
    }
    order = PaperTradingEngine().execute_order(signal=signal, quantity=float(quantity))
    order['decision_details'] = {
        'source': 'manual_order',
        'note': request.note,
        'quote_provider': quote.get('provider'),
        'quote_cache': quote.get('cache'),
        'guard': guard,
    }
    if not trading_repository.available:
        try:
            stored = local_persistence_service.add_manual_order(
                symbol=symbol,
                order=order,
                max_open_trades=guard['max_open_trades'],
            )
        except ValueError as exc:
            raise _manual_order_http_error(exc) from exc
        return {
            'status': 'manual_order_opened',
            'order': stored,
            'portfolio': local_persistence_service.portfolio_summary(),
            'persistence': 'local_file',
        }
    try:
        stored = trading_repository.manual_paper_order(
            symbol=symbol,
            order=order,
            max_open_trades=guard['max_open_trades'],
        )
    except ValueError as exc:
        raise _manual_order_http_error(exc) from exc
    return {'status': 'manual_order_opened', 'order': stored, 'persistence': 'postgres'}
