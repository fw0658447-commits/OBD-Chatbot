from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import RLock
from typing import Any

from app.config import settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> dict[str, Any]:
    now = _now()
    return {
        'version': 1,
        'portfolio': {
            'cash_balance': 10000.0,
            'starting_balance': 10000.0,
            'current_equity': 10000.0,
            'total_realized_pnl': 0.0,
            'total_unrealized_pnl': 0.0,
            'created_at': now,
            'updated_at': now,
        },
        'cash_ledger': [],
        'manual_orders': [],
        'watchlist': [],
        'next_order_number': 1,
    }


class LocalPersistenceService:
    def __init__(self) -> None:
        self._order_lock = RLock()

    @property
    def path(self) -> Path:
        return Path(settings.local_state_path)

    def status(self) -> dict[str, Any]:
        state = self._read()
        return {
            'enabled': True,
            'persistence': 'local_file',
            'path': str(self.path),
            'watchlist_items': len(state['watchlist']),
            'paper_orders': len(state['manual_orders']),
            'cash_transactions': len(state['cash_ledger']),
        }

    def list_watchlist(self) -> list[dict[str, Any]]:
        return deepcopy(self._read()['watchlist'])

    def add_watchlist_item(
        self,
        symbol: str,
        note: str | None = None,
        alert_price: float | None = None,
        target_price: float | None = None,
    ) -> dict[str, Any]:
        state = self._read()
        existing = next((item for item in state['watchlist'] if item.get('symbol') == symbol), None)
        payload = {
            'id': symbol,
            'symbol': symbol,
            'note': note,
            'alert_price': alert_price,
            'target_price': target_price,
            'updated_at': _now(),
        }
        if existing:
            existing.update(payload)
            item = existing
        else:
            payload['created_at'] = payload['updated_at']
            state['watchlist'].append(payload)
            item = payload
        self._write(state)
        return deepcopy(item)

    def update_watchlist_item(
        self,
        symbol: str,
        note: str | None = None,
        alert_price: float | None = None,
        target_price: float | None = None,
    ) -> dict[str, Any] | None:
        state = self._read()
        item = next((entry for entry in state['watchlist'] if entry.get('symbol') == symbol), None)
        if item is None:
            return None
        item.update({
            'note': note,
            'alert_price': alert_price,
            'target_price': target_price,
            'updated_at': _now(),
        })
        self._write(state)
        return deepcopy(item)

    def delete_watchlist_item(self, symbol: str) -> bool:
        state = self._read()
        before = len(state['watchlist'])
        state['watchlist'] = [item for item in state['watchlist'] if item.get('symbol') != symbol]
        deleted = len(state['watchlist']) < before
        if deleted:
            self._write(state)
        return deleted

    def portfolio_summary(self) -> dict[str, Any]:
        state = self._read()
        return self._portfolio_summary_from_state(state)

    def list_cash_transactions(self, limit: int = 100) -> list[dict[str, Any]]:
        items = self._read()['cash_ledger'][-limit:]
        return deepcopy(list(reversed(items)))

    def add_cash_transaction(self, transaction_type: str, amount: float, note: str | None = None) -> dict[str, Any]:
        if amount <= 0:
            raise ValueError('Amount must be positive.')
        if transaction_type not in {'deposit', 'withdrawal'}:
            raise ValueError('transaction_type must be deposit or withdrawal.')

        state = self._read()
        portfolio = state['portfolio']
        cash_balance = float(portfolio.get('cash_balance') or 0.0)
        if transaction_type == 'withdrawal' and cash_balance < amount:
            raise ValueError('Auszahlungsbetrag übersteigt das verfügbare Paper-Guthaben.')

        signed_amount = amount if transaction_type == 'deposit' else -amount
        portfolio['cash_balance'] = cash_balance + signed_amount
        portfolio['starting_balance'] = float(portfolio.get('starting_balance') or 0.0) + signed_amount
        portfolio['updated_at'] = _now()
        tx = {
            'id': f"local-cash-{len(state['cash_ledger']) + 1}",
            'transaction_type': transaction_type,
            'amount': amount,
            'balance_after': portfolio['cash_balance'],
            'note': note,
            'created_at': portfolio['updated_at'],
        }
        state['cash_ledger'].append(tx)
        self._write(state)
        return {'portfolio': self._portfolio_summary_from_state(state), 'transaction': deepcopy(tx)}

    def reset_paper_account(
        self,
        balance: float = 10000.0,
        note: str | None = None,
        cancel_open_orders: bool = True,
    ) -> dict[str, Any]:
        if balance < 0:
            raise ValueError('Balance must be >= 0.')
        state = self._read()
        now = _now()
        if cancel_open_orders:
            state['manual_orders'] = []
        state['portfolio'].update({
            'cash_balance': balance,
            'starting_balance': balance,
            'current_equity': balance,
            'total_realized_pnl': 0.0,
            'total_unrealized_pnl': 0.0,
            'updated_at': now,
        })
        tx = {
            'id': f"local-cash-{len(state['cash_ledger']) + 1}",
            'transaction_type': 'reset',
            'amount': balance,
            'balance_after': balance,
            'note': note,
            'created_at': now,
        }
        state['cash_ledger'].append(tx)
        self._write(state)
        return {'portfolio': self._portfolio_summary_from_state(state), 'transaction': deepcopy(tx)}

    def add_manual_order(
        self,
        symbol: str,
        order: dict[str, Any],
        max_open_trades: int | None = None,
    ) -> dict[str, Any]:
        with self._order_lock:
            state = self._read()
            portfolio = state['portfolio']
            open_orders = [item for item in state['manual_orders'] if item.get('status') == 'open']
            if max_open_trades is not None and len(open_orders) >= max_open_trades:
                raise ValueError(f'Positionslimit erreicht: {len(open_orders)}/{max_open_trades} offene Trades.')
            quantity = float(order.get('quantity') or 0.0)
            entry_price = float(order.get('entry_price') or 0.0)
            entry_commission = float(order.get('entry_commission') or 0.0)
            reserved_cash = abs(quantity * entry_price) + entry_commission
            available_cash = float(portfolio.get('cash_balance') or 0.0)
            if available_cash < reserved_cash:
                raise ValueError(
                    f'Orderbetrag {reserved_cash:.2f} übersteigt verfügbares Paper-Guthaben {available_cash:.2f}.'
                )

            order_number = int(state.get('next_order_number') or 1)
            now = _now()
            stored = {
                **deepcopy(order),
                'id': f'local-order-{order_number}',
                'symbol': symbol,
                'decision_mode': order.get('decision_mode') or 'manual',
                'model_source': order.get('model_source') or 'manual',
                'opened_at': now,
                'created_at': now,
            }
            state['next_order_number'] = order_number + 1
            state['manual_orders'].append(stored)
            portfolio['cash_balance'] = available_cash - reserved_cash
            portfolio['updated_at'] = now
            self._write(state)
            return deepcopy(stored)

    def list_orders(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        orders = self._read()['manual_orders']
        if status:
            orders = [order for order in orders if order.get('status') == status]
        return deepcopy(list(reversed(orders[-limit:])))

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        return deepcopy(next((order for order in self._read()['manual_orders'] if order.get('id') == order_id), None))

    def close_order(self, order_id: str, closed_order: dict[str, Any]) -> dict[str, Any] | None:
        with self._order_lock:
            state = self._read()
            for index, order in enumerate(state['manual_orders']):
                if order.get('id') != order_id or order.get('status') != 'open':
                    continue
                updated = {**order, **deepcopy(closed_order), 'closed_at': _now()}
                state['manual_orders'][index] = updated
                entry_notional = abs(float(order.get('quantity') or 0.0) * float(order.get('entry_price') or 0.0))
                entry_commission = float(order.get('entry_commission') or 0.0)
                pnl_amount = float(updated.get('pnl_amount') or 0.0)
                state['portfolio']['cash_balance'] = (
                    float(state['portfolio'].get('cash_balance') or 0.0)
                    + entry_notional
                    + entry_commission
                    + pnl_amount
                )
                state['portfolio']['updated_at'] = updated['closed_at']
                self._write(state)
                return deepcopy(updated)
            return None

    def performance_summary(self) -> dict[str, Any]:
        state = self._read()
        orders = state['manual_orders']
        closed = [order for order in orders if order.get('status') != 'open']
        open_orders = [order for order in orders if order.get('status') == 'open']
        wins = [order for order in closed if float(order.get('pnl_amount') or 0.0) > 0]
        losses = [order for order in closed if float(order.get('pnl_amount') or 0.0) < 0]
        gross_profit = sum(float(order.get('pnl_amount') or 0.0) for order in wins)
        gross_loss = sum(float(order.get('pnl_amount') or 0.0) for order in losses)
        gross_loss_abs = abs(gross_loss)
        total_realized = gross_profit + gross_loss
        closed_count = len(closed)
        return {
            'persistence': 'local_file',
            'total_orders': len(orders),
            'open_orders': len(open_orders),
            'closed_orders': closed_count,
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate_percent': round((len(wins) / closed_count * 100), 2) if closed_count else 0.0,
            'gross_profit': round(gross_profit, 2),
            'gross_loss': round(gross_loss, 2),
            'profit_factor': round(gross_profit / gross_loss_abs, 4) if gross_loss_abs else None,
            'expectancy_per_trade': round(total_realized / closed_count, 2) if closed_count else 0.0,
            'total_realized_pnl': round(total_realized, 2),
        }

    def equity_curve(self) -> dict[str, Any]:
        state = self._read()
        portfolio = state['portfolio']
        starting_balance = float(portfolio.get('starting_balance') or 10000.0)
        equity = starting_balance
        items = [{'timestamp': portfolio.get('created_at') or _now(), 'equity': round(equity, 2), 'event': 'start'}]
        for order in state['manual_orders']:
            if order.get('status') == 'open':
                continue
            equity += float(order.get('pnl_amount') or 0.0)
            items.append({'timestamp': order.get('closed_at') or order.get('opened_at') or _now(), 'equity': round(equity, 2), 'event': order.get('symbol')})
        current = self._portfolio_summary_from_state(state)
        if len(items) == 1:
            items.append({'timestamp': current.get('updated_at') or _now(), 'equity': round(float(current.get('current_equity') or equity), 2), 'event': 'current'})
        return {'items': items, 'persistence': 'local_file'}

    def portfolio_snapshot(self, market_data_service: Any, paper_trading_engine: Any) -> dict[str, Any]:
        state = self._read()
        positions: list[dict[str, Any]] = []
        total_unrealized = 0.0
        for order in state['manual_orders']:
            if order.get('status') != 'open':
                continue
            try:
                quote = market_data_service.get_quote(order['symbol'])
                marked = paper_trading_engine.mark_to_market(order=order, current_price=float(quote['price']))
            except Exception:
                marked = dict(order)
            total_unrealized += float(marked.get('unrealized_pnl_amount') or 0.0)
            positions.append(marked)
        portfolio = self._portfolio_summary_from_state(state, total_unrealized=total_unrealized)
        portfolio['positions'] = positions
        return {
            'status': 'ok',
            'portfolio': portfolio,
            'positions': positions,
            'performance': self.performance_summary(),
            'persistence': 'local_file',
        }

    def _read(self) -> dict[str, Any]:
        path = self.path
        if not path.exists():
            return _default_state()
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            return _default_state()
        state = _default_state()
        for key, value in data.items():
            state[key] = value
        state.setdefault('portfolio', _default_state()['portfolio'])
        state.setdefault('cash_ledger', [])
        state.setdefault('manual_orders', [])
        state.setdefault('watchlist', [])
        state.setdefault('next_order_number', len(state['manual_orders']) + 1)
        return state

    def _write(self, state: dict[str, Any]) -> None:
        path = self.path
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f'{path.suffix}.tmp')
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding='utf-8')
        tmp.replace(path)

    def _portfolio_summary_from_state(self, state: dict[str, Any], total_unrealized: float = 0.0) -> dict[str, Any]:
        portfolio = dict(state['portfolio'])
        open_orders = [order for order in state['manual_orders'] if order.get('status') == 'open']
        closed_orders = [order for order in state['manual_orders'] if order.get('status') != 'open']
        realized = sum(float(order.get('pnl_amount') or 0.0) for order in closed_orders)
        open_notional = sum(abs(float(order.get('quantity') or 0.0) * float(order.get('entry_price') or 0.0)) for order in open_orders)
        open_entry_commissions = sum(float(order.get('entry_commission') or 0.0) for order in open_orders)
        cash = float(portfolio.get('cash_balance') or 0.0)
        portfolio.update({
            'cash_balance': round(cash, 2),
            'current_equity': round(cash + open_notional + open_entry_commissions + total_unrealized, 2),
            'total_realized_pnl': round(realized, 2),
            'total_unrealized_pnl': round(total_unrealized, 2),
            'open_orders_count': len(open_orders),
            'closed_orders_count': len(closed_orders),
            'open_notional': round(open_notional, 2),
            'available_cash': round(cash, 2),
            'orders': deepcopy(open_orders),
            'positions': deepcopy(open_orders),
            'persistence': 'local_file',
        })
        return portfolio


local_persistence_service = LocalPersistenceService()
