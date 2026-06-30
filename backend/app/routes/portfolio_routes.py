from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.repositories.trading_repository import trading_repository
from app.services.bot_engine import BotEngine
from app.services.market_data_service import get_market_data_service
from app.services.paper_trading_engine import PaperTradingEngine

router = APIRouter()

# Memory fallback for non-Docker/local API tests without PostgreSQL.
_memory_cash_balance = 10000.0
_memory_starting_balance = 10000.0
_memory_cash_ledger: list[dict] = []
_memory_manual_orders: list[dict] = []


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


def _memory_portfolio():
    return {
        'cash_balance': _memory_cash_balance,
        'starting_balance': _memory_starting_balance,
        'current_equity': _memory_cash_balance,
        'total_realized_pnl': 0.0,
        'total_unrealized_pnl': 0.0,
        'positions': _memory_manual_orders,
        'open_orders_count': len(_memory_manual_orders),
        'closed_orders_count': 0,
        'open_notional': sum(abs(float(x.get('quantity', 0)) * float(x.get('entry_price', 0))) for x in _memory_manual_orders),
        'available_cash': _memory_cash_balance,
        'persistence': 'memory',
    }


@router.get('/paper')
def get_paper_portfolio():
    if not trading_repository.available:
        return {
            **_memory_portfolio(),
            'note': 'DATABASE_URL ist nicht gesetzt oder PostgreSQL ist nicht erreichbar. Das Backend nutzt lokale Platzhalterdaten.',
        }
    snapshot = BotEngine().portfolio_snapshot()
    return snapshot.get('portfolio')


@router.get('/paper/orders')
def get_paper_orders(status: str | None = None):
    if not trading_repository.available:
        items = [item for item in _memory_manual_orders if status is None or item.get('status') == status]
        return {'items': items, 'persistence': 'memory'}
    return {'items': trading_repository.list_paper_orders(status=status, limit=200), 'persistence': 'postgres'}


@router.get('/paper/performance')
def get_paper_performance():
    if not trading_repository.available:
        return {
            'persistence': 'memory',
            'total_orders': len(_memory_manual_orders),
            'closed_orders': 0,
            'open_orders': len(_memory_manual_orders),
        }
    return trading_repository.performance_summary()


@router.get('/paper/cash-ledger')
def get_cash_ledger(limit: int = Query(default=100, ge=1, le=500)):
    if not trading_repository.available:
        return {'items': _memory_cash_ledger[-limit:][::-1], 'persistence': 'memory'}
    return {'items': trading_repository.list_cash_transactions(limit=limit), 'persistence': 'postgres'}


@router.post('/paper/deposit')
def deposit_virtual_cash(request: CashTransactionRequest):
    global _memory_cash_balance, _memory_starting_balance
    if not trading_repository.available:
        _memory_cash_balance += request.amount
        _memory_starting_balance += request.amount
        tx = {'transaction_type': 'deposit', 'amount': request.amount, 'balance_after': _memory_cash_balance, 'note': request.note}
        _memory_cash_ledger.append(tx)
        return {'status': 'deposited', 'portfolio': _memory_portfolio(), 'transaction': tx, 'persistence': 'memory'}
    try:
        result = trading_repository.add_cash_transaction('deposit', request.amount, request.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {'status': 'deposited', **(result or {}), 'persistence': 'postgres'}


@router.post('/paper/withdraw')
def withdraw_virtual_cash(request: CashTransactionRequest):
    global _memory_cash_balance, _memory_starting_balance
    if not trading_repository.available:
        if _memory_cash_balance < request.amount:
            raise HTTPException(status_code=400, detail='Withdrawal amount exceeds available cash.')
        _memory_cash_balance -= request.amount
        _memory_starting_balance -= request.amount
        tx = {'transaction_type': 'withdrawal', 'amount': request.amount, 'balance_after': _memory_cash_balance, 'note': request.note}
        _memory_cash_ledger.append(tx)
        return {'status': 'withdrawn', 'portfolio': _memory_portfolio(), 'transaction': tx, 'persistence': 'memory'}
    try:
        result = trading_repository.add_cash_transaction('withdrawal', request.amount, request.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {'status': 'withdrawn', **(result or {}), 'persistence': 'postgres'}


@router.post('/paper/reset')
def reset_paper_account(request: ResetPaperAccountRequest):
    global _memory_cash_balance, _memory_starting_balance, _memory_manual_orders
    if not trading_repository.available:
        _memory_cash_balance = request.balance
        _memory_starting_balance = request.balance
        if request.cancel_open_orders:
            _memory_manual_orders = []
        tx = {'transaction_type': 'reset', 'amount': request.balance, 'balance_after': request.balance, 'note': request.note}
        _memory_cash_ledger.append(tx)
        return {'status': 'reset', 'portfolio': _memory_portfolio(), 'transaction': tx, 'persistence': 'memory'}
    try:
        result = trading_repository.reset_paper_account(request.balance, request.note, request.cancel_open_orders)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {'status': 'reset', **(result or {}), 'persistence': 'postgres'}


@router.post('/paper/manual-order')
def create_manual_paper_order(request: ManualPaperOrderRequest):
    global _memory_cash_balance
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
    }
    if not trading_repository.available:
        order['id'] = f'manual-{len(_memory_manual_orders) + 1}'
        order['symbol'] = symbol
        _memory_manual_orders.append(order)
        _memory_cash_balance -= abs(float(order['quantity']) * float(order['entry_price']))
        return {'status': 'manual_order_opened', 'order': order, 'portfolio': _memory_portfolio(), 'persistence': 'memory'}
    stored = trading_repository.manual_paper_order(symbol=symbol, order=order)
    return {'status': 'manual_order_opened', 'order': stored, 'persistence': 'postgres'}
