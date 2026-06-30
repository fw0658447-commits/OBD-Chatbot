from __future__ import annotations

from app.config import settings


class PaperTradingEngine:
    """Paper execution with simple but explicit spread, slippage and commission.

    It is still a simulation, but less optimistic than filling every trade exactly
    at the signal price. Long entries pay the ask, short entries receive the bid;
    exits are treated the opposite way.
    """

    def execute_order(self, signal: dict, quantity: float) -> dict:
        side = signal['signal_type']
        requested_entry = float(signal['entry_price'])
        fill_price = self._apply_entry_costs(requested_entry, side)
        notional = abs(fill_price * float(quantity))
        commission = self._commission(notional)
        return {
            'side': side,
            'order_type': 'market',
            'quantity': quantity,
            'requested_entry_price': requested_entry,
            'entry_price': round(fill_price, 8),
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'status': 'open',
            'entry_slippage_bps': settings.paper_slippage_bps,
            'spread_bps': settings.paper_spread_bps,
            'entry_commission': round(commission, 4),
            'total_commission': round(commission, 4),
        }

    def evaluate_open_order(self, order: dict, current_price: float) -> dict:
        side = order['side']
        if side == 'long':
            if current_price <= float(order['stop_loss']):
                return self.close_order(order, current_price, 'closed_stop_loss')
            if current_price >= float(order['take_profit']):
                return self.close_order(order, current_price, 'closed_take_profit')
        if side == 'short':
            if current_price >= float(order['stop_loss']):
                return self.close_order(order, current_price, 'closed_stop_loss')
            if current_price <= float(order['take_profit']):
                return self.close_order(order, current_price, 'closed_take_profit')
        return order

    def mark_to_market(self, order: dict, current_price: float) -> dict:
        executable_price = self._apply_exit_costs(float(current_price), order['side'])
        pnl, pnl_percent, gross_pnl, exit_commission = self._calculate_pnl(order, executable_price)
        updated_order = dict(order)
        updated_order['current_price'] = current_price
        updated_order['current_executable_price'] = round(executable_price, 8)
        updated_order['unrealized_gross_pnl_amount'] = round(gross_pnl, 2)
        updated_order['unrealized_pnl_amount'] = round(pnl, 2)
        updated_order['unrealized_pnl_percent'] = round(pnl_percent, 2)
        updated_order['estimated_exit_commission'] = round(exit_commission, 4)
        return updated_order

    def close_order(self, order: dict, exit_price: float, status: str = 'closed_manual') -> dict:
        executable_exit = self._apply_exit_costs(float(exit_price), order['side'])
        pnl, pnl_percent, gross_pnl, exit_commission = self._calculate_pnl(order, executable_exit)
        updated_order = dict(order)
        updated_order['status'] = status
        updated_order['requested_exit_price'] = exit_price
        updated_order['exit_price'] = round(executable_exit, 8)
        updated_order['gross_pnl_amount'] = round(gross_pnl, 2)
        updated_order['pnl_amount'] = round(pnl, 2)
        updated_order['pnl_percent'] = round(pnl_percent, 2)
        updated_order['exit_commission'] = round(exit_commission, 4)
        updated_order['total_commission'] = round(float(order.get('entry_commission') or 0.0) + exit_commission, 4)
        updated_order['exit_slippage_bps'] = settings.paper_slippage_bps
        updated_order['spread_bps'] = settings.paper_spread_bps
        return updated_order

    def _calculate_pnl(self, order: dict, executable_exit_price: float) -> tuple[float, float, float, float]:
        entry_price = float(order['entry_price'])
        quantity = float(order['quantity'])
        entry_commission = float(order.get('entry_commission') or 0.0)
        exit_commission = self._commission(abs(executable_exit_price * quantity))
        if order['side'] == 'long':
            gross_pnl = (executable_exit_price - entry_price) * quantity
            pnl_percent = (executable_exit_price - entry_price) / entry_price * 100
        else:
            gross_pnl = (entry_price - executable_exit_price) * quantity
            pnl_percent = (entry_price - executable_exit_price) / entry_price * 100
        net_pnl = gross_pnl - entry_commission - exit_commission
        return net_pnl, pnl_percent, gross_pnl, exit_commission

    def _apply_entry_costs(self, price: float, side: str) -> float:
        half_spread = settings.paper_spread_bps / 2 / 10000
        slippage = settings.paper_slippage_bps / 10000
        factor = 1 + half_spread + slippage if side == 'long' else 1 - half_spread - slippage
        return max(price * factor, 0.00000001)

    def _apply_exit_costs(self, price: float, side: str) -> float:
        half_spread = settings.paper_spread_bps / 2 / 10000
        slippage = settings.paper_slippage_bps / 10000
        factor = 1 - half_spread - slippage if side == 'long' else 1 + half_spread + slippage
        return max(price * factor, 0.00000001)

    def _commission(self, notional: float) -> float:
        raw = notional * settings.paper_commission_bps / 10000
        return max(settings.paper_min_commission, raw)
