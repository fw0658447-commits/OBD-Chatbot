from __future__ import annotations

from decimal import Decimal
import json
from typing import Any
from uuid import UUID

from app.database import get_connection, is_database_configured


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _serialise_row(row: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            result[key] = float(value)
        elif isinstance(value, UUID):
            result[key] = str(value)
        elif hasattr(value, 'isoformat'):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


class TradingRepository:
    @property
    def enabled(self) -> bool:
        return is_database_configured()

    def ping(self) -> bool:
        if not self.enabled:
            return False
        try:
            with get_connection() as connection:
                connection.execute('SELECT 1')
            return True
        except Exception:
            return False

    @property
    def available(self) -> bool:
        return self.ping()

    def get_or_create_asset(
        self,
        symbol: str,
        name: str | None = None,
        asset_type: str = 'unknown',
        provider: str = 'mock',
        provider_symbol: str | None = None,
        exchange: str | None = None,
        currency: str | None = None,
    ) -> str | None:
        if not self.enabled:
            return None
        provider_symbol = provider_symbol or symbol
        name = name or symbol
        with get_connection() as connection:
            row = connection.execute(
                'SELECT id FROM assets WHERE symbol = %s ORDER BY created_at LIMIT 1',
                (symbol,),
            ).fetchone()
            if row:
                return str(row['id'])

            inserted = connection.execute(
                '''
                INSERT INTO assets (symbol, name, asset_type, exchange, currency, provider, provider_symbol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                ''',
                (symbol, name, asset_type, exchange, currency, provider, provider_symbol),
            ).fetchone()
            connection.commit()
            return str(inserted['id'])

    def get_or_create_portfolio(self) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        with get_connection() as connection:
            row = connection.execute(
                'SELECT * FROM paper_portfolio ORDER BY created_at LIMIT 1'
            ).fetchone()
            if row:
                return _serialise_row(row)
            inserted = connection.execute(
                '''
                INSERT INTO paper_portfolio (cash_balance, starting_balance, current_equity)
                VALUES (10000, 10000, 10000)
                RETURNING *
                '''
            ).fetchone()
            connection.commit()
            return _serialise_row(inserted)

    def create_prediction(self, asset_id: str | None, prediction: dict[str, Any]) -> str | None:
        if not self.enabled or asset_id is None:
            return None
        with get_connection() as connection:
            row = connection.execute(
                '''
                INSERT INTO ai_predictions (
                    asset_id, timeframe, horizon, direction,
                    probability_long, probability_short, probability_neutral,
                    expected_return_percent, confidence_score, risk_score,
                    explanation, model_version
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                ''',
                (
                    asset_id,
                    prediction['timeframe'],
                    prediction['horizon'],
                    prediction['direction'],
                    prediction['probability_long'],
                    prediction['probability_short'],
                    prediction['probability_neutral'],
                    prediction.get('expected_return_percent'),
                    prediction['confidence_score'],
                    prediction['risk_score'],
                    prediction.get('explanation'),
                    prediction['model_version'],
                ),
            ).fetchone()
            connection.commit()
            return str(row['id'])

    def create_signal(
        self,
        asset_id: str | None,
        prediction_id: str | None,
        signal: dict[str, Any],
        status: str,
        reason: str | None = None,
    ) -> str | None:
        if not self.enabled or asset_id is None:
            return None
        with get_connection() as connection:
            try:
                row = connection.execute(
                    '''
                    INSERT INTO bot_signals (
                        asset_id, prediction_id, signal_type, signal_score,
                        entry_price, stop_loss, take_profit, crv, status, reason,
                        decision_mode, model_source, ml_model_id, ml_direction,
                        ml_probability, decision_score, decision_details
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    RETURNING id
                    ''',
                    (
                        asset_id,
                        prediction_id,
                        signal['signal_type'],
                        signal['signal_score'],
                        signal['entry_price'],
                        signal['stop_loss'],
                        signal['take_profit'],
                        signal['crv'],
                        status,
                        reason or signal.get('reason'),
                        signal.get('decision_mode', 'rule'),
                        signal.get('model_source', 'rule'),
                        signal.get('ml_model_id'),
                        signal.get('ml_direction'),
                        signal.get('ml_probability'),
                        signal.get('decision_score'),
                        json.dumps(signal.get('decision_details') or {}, default=str),
                    ),
                ).fetchone()
            except Exception:
                connection.rollback()
                row = connection.execute(
                    '''
                    INSERT INTO bot_signals (
                        asset_id, prediction_id, signal_type, signal_score,
                        entry_price, stop_loss, take_profit, crv, status, reason
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    ''',
                    (
                        asset_id,
                        prediction_id,
                        signal['signal_type'],
                        signal['signal_score'],
                        signal['entry_price'],
                        signal['stop_loss'],
                        signal['take_profit'],
                        signal['crv'],
                        status,
                        reason or signal.get('reason'),
                    ),
                ).fetchone()
            connection.commit()
            return str(row['id'])

    def create_paper_order(
        self,
        asset_id: str | None,
        signal_id: str | None,
        order: dict[str, Any],
    ) -> str | None:
        if not self.enabled or asset_id is None:
            return None
        with get_connection() as connection:
            try:
                row = connection.execute(
                    '''
                    INSERT INTO paper_orders (
                        signal_id, asset_id, side, order_type, quantity,
                        entry_price, stop_loss, take_profit, status,
                        decision_mode, model_source, ml_model_id, ml_direction,
                        ml_probability, decision_score, decision_details,
                        requested_entry_price, entry_slippage_bps, spread_bps,
                        entry_commission, total_commission
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                    RETURNING id
                    ''',
                    (
                        signal_id,
                        asset_id,
                        order['side'],
                        order['order_type'],
                        order['quantity'],
                        order['entry_price'],
                        order['stop_loss'],
                        order['take_profit'],
                        order['status'],
                        order.get('decision_mode', 'rule'),
                        order.get('model_source', 'rule'),
                        order.get('ml_model_id'),
                        order.get('ml_direction'),
                        order.get('ml_probability'),
                        order.get('decision_score'),
                        json.dumps(order.get('decision_details') or {}, default=str),
                        order.get('requested_entry_price'),
                        order.get('entry_slippage_bps'),
                        order.get('spread_bps'),
                        order.get('entry_commission'),
                        order.get('total_commission'),
                    ),
                ).fetchone()
            except Exception:
                connection.rollback()
                row = connection.execute(
                    '''
                    INSERT INTO paper_orders (
                        signal_id, asset_id, side, order_type, quantity,
                        entry_price, stop_loss, take_profit, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    ''',
                    (
                        signal_id,
                        asset_id,
                        order['side'],
                        order['order_type'],
                        order['quantity'],
                        order['entry_price'],
                        order['stop_loss'],
                        order['take_profit'],
                        order['status'],
                    ),
                ).fetchone()
            self._refresh_portfolio_metrics(connection)
            connection.commit()
            return str(row['id'])

    def log_risk_event(self, event_type: str, severity: str, message: str) -> str | None:
        if not self.enabled:
            return None
        with get_connection() as connection:
            row = connection.execute(
                '''
                INSERT INTO risk_events (event_type, severity, message)
                VALUES (%s, %s, %s)
                RETURNING id
                ''',
                (event_type, severity, message),
            ).fetchone()
            connection.commit()
            return str(row['id'])

    def count_open_orders(self) -> int:
        if not self.enabled:
            return 0
        with get_connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM paper_orders WHERE status = 'open'"
            ).fetchone()
            return int(row['count'])

    def daily_pnl_percent(self) -> float:
        if not self.enabled:
            return 0.0
        with get_connection() as connection:
            portfolio = connection.execute(
                'SELECT current_equity, starting_balance FROM paper_portfolio ORDER BY created_at LIMIT 1'
            ).fetchone()
            pnl = connection.execute(
                '''
                SELECT COALESCE(SUM(pnl_amount), 0) AS pnl
                FROM paper_orders
                WHERE closed_at::date = CURRENT_DATE
                '''
            ).fetchone()
        base = _to_float(portfolio['current_equity'] if portfolio else None) or 10000.0
        return float(pnl['pnl']) / base if base else 0.0

    def list_predictions(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        with get_connection() as connection:
            rows = connection.execute(
                '''
                SELECT p.*, a.symbol, a.name, a.asset_type
                FROM ai_predictions p
                JOIN assets a ON a.id = p.asset_id
                ORDER BY p.created_at DESC
                LIMIT %s
                ''',
                (limit,),
            ).fetchall()
            return [_serialise_row(row) for row in rows]

    def list_signals(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        with get_connection() as connection:
            rows = connection.execute(
                '''
                SELECT s.*, a.symbol, a.name, a.asset_type
                FROM bot_signals s
                JOIN assets a ON a.id = s.asset_id
                ORDER BY s.created_at DESC
                LIMIT %s
                ''',
                (limit,),
            ).fetchall()
            return [_serialise_row(row) for row in rows]

    def list_paper_orders(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        with get_connection() as connection:
            if status:
                rows = connection.execute(
                    '''
                    SELECT o.*, a.symbol, a.name, a.asset_type
                    FROM paper_orders o
                    JOIN assets a ON a.id = o.asset_id
                    WHERE o.status = %s
                    ORDER BY o.opened_at DESC
                    LIMIT %s
                    ''',
                    (status, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    '''
                    SELECT o.*, a.symbol, a.name, a.asset_type
                    FROM paper_orders o
                    JOIN assets a ON a.id = o.asset_id
                    ORDER BY o.opened_at DESC
                    LIMIT %s
                    ''',
                    (limit,),
                ).fetchall()
            return [_serialise_row(row) for row in rows]

    def get_paper_order(self, order_id: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        with get_connection() as connection:
            row = connection.execute(
                '''
                SELECT o.*, a.symbol, a.name, a.asset_type
                FROM paper_orders o
                JOIN assets a ON a.id = o.asset_id
                WHERE o.id = %s
                ''',
                (order_id,),
            ).fetchone()
            return _serialise_row(row) if row else None

    def close_paper_order(self, order_id: str, closed_order: dict[str, Any]) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        with get_connection() as connection:
            try:
                row = connection.execute(
                    '''
                    UPDATE paper_orders
                    SET status = %s,
                        closed_at = NOW(),
                        exit_price = %s,
                        pnl_amount = %s,
                        pnl_percent = %s,
                        requested_exit_price = %s,
                        gross_pnl_amount = %s,
                        exit_commission = %s,
                        total_commission = %s,
                        exit_slippage_bps = %s,
                        spread_bps = %s
                    WHERE id = %s AND status = 'open'
                    RETURNING *
                    ''',
                    (
                        closed_order['status'],
                        closed_order.get('exit_price'),
                        closed_order.get('pnl_amount'),
                        closed_order.get('pnl_percent'),
                        closed_order.get('requested_exit_price'),
                        closed_order.get('gross_pnl_amount'),
                        closed_order.get('exit_commission'),
                        closed_order.get('total_commission'),
                        closed_order.get('exit_slippage_bps'),
                        closed_order.get('spread_bps'),
                        order_id,
                    ),
                ).fetchone()
            except Exception:
                connection.rollback()
                row = connection.execute(
                    '''
                    UPDATE paper_orders
                    SET status = %s,
                        closed_at = NOW(),
                        exit_price = %s,
                        pnl_amount = %s,
                        pnl_percent = %s
                    WHERE id = %s AND status = 'open'
                    RETURNING *
                    ''',
                    (
                        closed_order['status'],
                        closed_order.get('exit_price'),
                        closed_order.get('pnl_amount'),
                        closed_order.get('pnl_percent'),
                        order_id,
                    ),
                ).fetchone()
            self._refresh_portfolio_metrics(connection)
            connection.commit()
            return _serialise_row(row) if row else None

    def update_unrealized_pnl(self, total_unrealized_pnl: float) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        with get_connection() as connection:
            portfolio = self._ensure_portfolio(connection)
            realized = _to_float(portfolio.get('total_realized_pnl')) or 0.0
            starting_balance = _to_float(portfolio.get('starting_balance')) or 10000.0
            open_totals = connection.execute(
                '''
                SELECT COALESCE(SUM(ABS(quantity * entry_price)), 0) AS open_notional
                FROM paper_orders
                WHERE status = 'open'
                '''
            ).fetchone()
            open_notional = _to_float(open_totals['open_notional']) or 0.0
            current_equity = starting_balance + realized + total_unrealized_pnl
            cash_balance = current_equity - open_notional
            row = connection.execute(
                '''
                UPDATE paper_portfolio
                SET total_unrealized_pnl = %s,
                    current_equity = %s,
                    cash_balance = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING *
                ''',
                (total_unrealized_pnl, current_equity, cash_balance, portfolio['id']),
            ).fetchone()
            connection.commit()
            return _serialise_row(row) if row else None

    def list_risk_events(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        with get_connection() as connection:
            rows = connection.execute(
                'SELECT * FROM risk_events ORDER BY created_at DESC LIMIT %s',
                (limit,),
            ).fetchall()
            return [_serialise_row(row) for row in rows]

    def list_watchlist(self) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        with get_connection() as connection:
            rows = connection.execute(
                '''
                SELECT w.*, a.symbol, a.name, a.asset_type, a.exchange, a.currency
                FROM watchlist_items w
                JOIN assets a ON a.id = w.asset_id
                ORDER BY w.created_at DESC
                '''
            ).fetchall()
            return [_serialise_row(row) for row in rows]

    def add_watchlist_item(
        self,
        symbol: str,
        note: str | None,
        alert_price: float | None,
        target_price: float | None = None,
    ) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        asset_id = self.get_or_create_asset(symbol=symbol)
        with get_connection() as connection:
            try:
                connection.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlist_items_asset_unique ON watchlist_items(asset_id)"
                )
                row = connection.execute(
                    '''
                    INSERT INTO watchlist_items (asset_id, note, alert_price, target_price)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (asset_id)
                    DO UPDATE SET note = EXCLUDED.note,
                                  alert_price = EXCLUDED.alert_price,
                                  target_price = EXCLUDED.target_price
                    RETURNING *
                    ''',
                    (asset_id, note, alert_price, target_price),
                ).fetchone()
            except Exception:
                connection.rollback()
                row = connection.execute(
                    '''
                    SELECT w.* FROM watchlist_items w WHERE w.asset_id = %s LIMIT 1
                    ''',
                    (asset_id,),
                ).fetchone()
                if row:
                    row = connection.execute(
                        '''
                        UPDATE watchlist_items
                        SET note = %s, alert_price = %s, target_price = %s
                        WHERE id = %s
                        RETURNING *
                        ''',
                        (note, alert_price, target_price, row['id']),
                    ).fetchone()
                else:
                    row = connection.execute(
                        '''
                        INSERT INTO watchlist_items (asset_id, note, alert_price, target_price)
                        VALUES (%s, %s, %s, %s)
                        RETURNING *
                        ''',
                        (asset_id, note, alert_price, target_price),
                    ).fetchone()
            connection.commit()
            # return the same enriched shape as list_watchlist
            with get_connection() as read_connection:
                enriched = read_connection.execute(
                    '''
                    SELECT w.*, a.symbol, a.name, a.asset_type, a.exchange, a.currency
                    FROM watchlist_items w
                    JOIN assets a ON a.id = w.asset_id
                    WHERE w.id = %s
                    ''',
                    (row['id'],),
                ).fetchone()
            return _serialise_row(enriched) if enriched else _serialise_row(row)

    def update_watchlist_item(
        self,
        symbol: str,
        note: str | None = None,
        alert_price: float | None = None,
        target_price: float | None = None,
    ) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        with get_connection() as connection:
            row = connection.execute(
                '''
                UPDATE watchlist_items w
                SET note = COALESCE(%s, w.note),
                    alert_price = COALESCE(%s, w.alert_price),
                    target_price = COALESCE(%s, w.target_price)
                FROM assets a
                WHERE w.asset_id = a.id AND a.symbol = %s
                RETURNING w.*
                ''',
                (note, alert_price, target_price, symbol),
            ).fetchone()
            connection.commit()
            return _serialise_row(row) if row else None

    def delete_watchlist_item(self, symbol: str) -> bool:
        if not self.enabled:
            return False
        with get_connection() as connection:
            row = connection.execute(
                '''
                DELETE FROM watchlist_items w
                USING assets a
                WHERE w.asset_id = a.id AND a.symbol = %s
                RETURNING w.id
                ''',
                (symbol,),
            ).fetchone()
            connection.commit()
            return row is not None

    def performance_summary(self) -> dict[str, Any]:
        if not self.enabled:
            return {
                'persistence': 'memory',
                'total_orders': 0,
                'closed_orders': 0,
                'open_orders': 0,
            }
        with get_connection() as connection:
            orders = connection.execute(
                '''
                SELECT o.*, a.symbol
                FROM paper_orders o
                JOIN assets a ON a.id = o.asset_id
                ORDER BY COALESCE(o.closed_at, o.opened_at) ASC
                '''
            ).fetchall()
            portfolio = self._ensure_portfolio(connection)

        serialised = [_serialise_row(row) for row in orders]
        closed = [order for order in serialised if order['status'] != 'open']
        open_orders = [order for order in serialised if order['status'] == 'open']
        wins = [order for order in closed if float(order.get('pnl_amount') or 0.0) > 0]
        losses = [order for order in closed if float(order.get('pnl_amount') or 0.0) < 0]
        breakeven = [order for order in closed if float(order.get('pnl_amount') or 0.0) == 0]
        gross_profit = sum(float(order.get('pnl_amount') or 0.0) for order in wins)
        gross_loss = sum(float(order.get('pnl_amount') or 0.0) for order in losses)
        gross_loss_abs = abs(gross_loss)
        total_realized = gross_profit + gross_loss
        closed_count = len(closed)
        starting_balance = _to_float(portfolio.get('starting_balance')) or 10000.0

        equity = starting_balance
        peak = starting_balance
        max_drawdown_amount = 0.0
        for order in closed:
            equity += float(order.get('pnl_amount') or 0.0)
            peak = max(peak, equity)
            drawdown = peak - equity
            max_drawdown_amount = max(max_drawdown_amount, drawdown)

        max_drawdown_percent = (max_drawdown_amount / peak * 100) if peak else 0.0

        return {
            'persistence': 'postgres',
            'total_orders': len(serialised),
            'open_orders': len(open_orders),
            'closed_orders': closed_count,
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'breakeven_trades': len(breakeven),
            'win_rate_percent': round((len(wins) / closed_count * 100), 2) if closed_count else 0.0,
            'gross_profit': round(gross_profit, 2),
            'gross_loss': round(gross_loss, 2),
            'profit_factor': round(gross_profit / gross_loss_abs, 4) if gross_loss_abs else None,
            'average_win': round(gross_profit / len(wins), 2) if wins else 0.0,
            'average_loss': round(gross_loss / len(losses), 2) if losses else 0.0,
            'expectancy_per_trade': round(total_realized / closed_count, 2) if closed_count else 0.0,
            'total_realized_pnl': round(total_realized, 2),
            'realized_return_percent': round((total_realized / starting_balance * 100), 2) if starting_balance else 0.0,
            'max_drawdown_amount': round(max_drawdown_amount, 2),
            'max_drawdown_percent': round(max_drawdown_percent, 2),
        }

    def performance_by_decision_mode(self) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        try:
            with get_connection() as connection:
                rows = connection.execute(
                    '''
                    SELECT COALESCE(decision_mode, 'rule') AS decision_mode,
                           COUNT(*) AS total_orders,
                           COUNT(*) FILTER (WHERE status = 'open') AS open_orders,
                           COUNT(*) FILTER (WHERE status <> 'open') AS closed_orders,
                           COUNT(*) FILTER (WHERE status <> 'open' AND COALESCE(pnl_amount, 0) > 0) AS winning_trades,
                           COUNT(*) FILTER (WHERE status <> 'open' AND COALESCE(pnl_amount, 0) < 0) AS losing_trades,
                           COALESCE(SUM(pnl_amount) FILTER (WHERE status <> 'open' AND COALESCE(pnl_amount, 0) > 0), 0) AS gross_profit,
                           COALESCE(SUM(pnl_amount) FILTER (WHERE status <> 'open' AND COALESCE(pnl_amount, 0) < 0), 0) AS gross_loss,
                           COALESCE(SUM(pnl_amount) FILTER (WHERE status <> 'open'), 0) AS total_realized_pnl,
                           AVG(decision_score) AS avg_decision_score
                    FROM paper_orders
                    GROUP BY COALESCE(decision_mode, 'rule')
                    ORDER BY total_orders DESC
                    '''
                ).fetchall()
        except Exception:
            return []

        items: list[dict[str, Any]] = []
        for row in rows:
            item = _serialise_row(row)
            closed = int(item.get('closed_orders') or 0)
            wins = int(item.get('winning_trades') or 0)
            gross_profit = float(item.get('gross_profit') or 0.0)
            gross_loss = float(item.get('gross_loss') or 0.0)
            gross_loss_abs = abs(gross_loss)
            item['win_rate_percent'] = round(wins / closed * 100, 2) if closed else 0.0
            item['profit_factor'] = round(gross_profit / gross_loss_abs, 4) if gross_loss_abs else None
            item['expectancy_per_trade'] = round(float(item.get('total_realized_pnl') or 0.0) / closed, 2) if closed else 0.0
            item['avg_decision_score'] = round(float(item.get('avg_decision_score') or 0.0), 2)
            items.append(item)
        return items

    def _ensure_portfolio(self, connection) -> dict[str, Any]:
        row = connection.execute('SELECT * FROM paper_portfolio ORDER BY created_at LIMIT 1').fetchone()
        if row:
            return _serialise_row(row)
        row = connection.execute(
            '''
            INSERT INTO paper_portfolio (cash_balance, starting_balance, current_equity)
            VALUES (10000, 10000, 10000)
            RETURNING *
            '''
        ).fetchone()
        return _serialise_row(row)

    def _refresh_portfolio_metrics(self, connection) -> None:
        portfolio = self._ensure_portfolio(connection)
        totals = connection.execute(
            '''
            SELECT COALESCE(SUM(pnl_amount), 0) AS realized_pnl
            FROM paper_orders
            WHERE status <> 'open'
            '''
        ).fetchone()
        open_totals = connection.execute(
            '''
            SELECT COALESCE(SUM(ABS(quantity * entry_price)), 0) AS open_notional
            FROM paper_orders
            WHERE status = 'open'
            '''
        ).fetchone()
        realized_pnl = _to_float(totals['realized_pnl']) or 0.0
        starting_balance = _to_float(portfolio.get('starting_balance')) or 10000.0
        unrealized_pnl = _to_float(portfolio.get('total_unrealized_pnl')) or 0.0
        open_notional = _to_float(open_totals['open_notional']) or 0.0
        current_equity = starting_balance + realized_pnl + unrealized_pnl
        cash_balance = current_equity - open_notional
        connection.execute(
            '''
            UPDATE paper_portfolio
            SET cash_balance = %s,
                current_equity = %s,
                total_realized_pnl = %s,
                updated_at = NOW()
            WHERE id = %s
            ''',
            (cash_balance, current_equity, realized_pnl, portfolio['id']),
        )


    def _ensure_cash_ledger_table(self, connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_cash_transactions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                transaction_type TEXT NOT NULL,
                amount NUMERIC NOT NULL,
                balance_after NUMERIC,
                note TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_paper_cash_transactions_created_at
            ON paper_cash_transactions(created_at DESC)
            """
        )

    def add_cash_transaction(self, transaction_type: str, amount: float, note: str | None = None) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        if amount <= 0:
            raise ValueError('Amount must be positive.')
        if transaction_type not in {'deposit', 'withdrawal'}:
            raise ValueError('transaction_type must be deposit or withdrawal.')
        signed_amount = amount if transaction_type == 'deposit' else -amount
        with get_connection() as connection:
            self._ensure_cash_ledger_table(connection)
            portfolio = self._ensure_portfolio(connection)
            current_equity = _to_float(portfolio.get('current_equity')) or 0.0
            cash_balance = _to_float(portfolio.get('cash_balance')) or 0.0
            starting_balance = _to_float(portfolio.get('starting_balance')) or 0.0
            if transaction_type == 'withdrawal' and cash_balance < amount:
                raise ValueError('Withdrawal amount exceeds available cash.')
            new_cash = cash_balance + signed_amount
            new_equity = current_equity + signed_amount
            new_starting = starting_balance + signed_amount
            updated = connection.execute(
                """
                UPDATE paper_portfolio
                SET cash_balance = %s,
                    starting_balance = %s,
                    current_equity = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING *
                """,
                (new_cash, new_starting, new_equity, portfolio['id']),
            ).fetchone()
            ledger = connection.execute(
                """
                INSERT INTO paper_cash_transactions (transaction_type, amount, balance_after, note)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (transaction_type, amount, new_cash, note),
            ).fetchone()
            connection.commit()
            return {'portfolio': _serialise_row(updated), 'transaction': _serialise_row(ledger)}

    def reset_paper_account(self, balance: float = 10000.0, note: str | None = None, cancel_open_orders: bool = True) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        if balance < 0:
            raise ValueError('Balance must be >= 0.')
        with get_connection() as connection:
            self._ensure_cash_ledger_table(connection)
            portfolio = self._ensure_portfolio(connection)
            if cancel_open_orders:
                connection.execute("UPDATE paper_orders SET status = 'cancelled', closed_at = NOW() WHERE status = 'open'")
            updated = connection.execute(
                """
                UPDATE paper_portfolio
                SET cash_balance = %s,
                    starting_balance = %s,
                    current_equity = %s,
                    total_realized_pnl = 0,
                    total_unrealized_pnl = 0,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING *
                """,
                (balance, balance, balance, portfolio['id']),
            ).fetchone()
            ledger = connection.execute(
                """
                INSERT INTO paper_cash_transactions (transaction_type, amount, balance_after, note)
                VALUES ('reset', %s, %s, %s)
                RETURNING *
                """,
                (balance, balance, note),
            ).fetchone()
            connection.commit()
            return {'portfolio': _serialise_row(updated), 'transaction': _serialise_row(ledger)}

    def list_cash_transactions(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        with get_connection() as connection:
            self._ensure_cash_ledger_table(connection)
            rows = connection.execute(
                """
                SELECT * FROM paper_cash_transactions
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
            return [_serialise_row(row) for row in rows]

    def manual_paper_order(self, symbol: str, order: dict[str, Any]) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        asset_id = self.get_or_create_asset(symbol=symbol)
        with get_connection() as connection:
            row = connection.execute(
                """
                INSERT INTO paper_orders (
                    signal_id, asset_id, side, order_type, quantity,
                    entry_price, stop_loss, take_profit, status,
                    decision_mode, model_source, requested_entry_price,
                    entry_slippage_bps, spread_bps, entry_commission, total_commission,
                    decision_details
                )
                VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, 'open',
                        'manual', 'manual', %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING *
                """,
                (
                    asset_id,
                    order['side'],
                    order.get('order_type', 'market'),
                    order['quantity'],
                    order['entry_price'],
                    order['stop_loss'],
                    order['take_profit'],
                    order.get('requested_entry_price', order['entry_price']),
                    order.get('entry_slippage_bps'),
                    order.get('spread_bps'),
                    order.get('entry_commission', 0),
                    order.get('total_commission', order.get('entry_commission', 0)),
                    json.dumps(order.get('decision_details') or {}, default=str),
                ),
            ).fetchone()
            self._refresh_portfolio_metrics(connection)
            connection.commit()
            return _serialise_row(row)

    def portfolio_summary(self) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        portfolio = self.get_or_create_portfolio()
        open_orders = self.list_paper_orders(status='open', limit=500)
        all_orders = self.list_paper_orders(status=None, limit=1000)
        closed_orders = [order for order in all_orders if order['status'] != 'open']
        realized_pnl = sum(float(order.get('pnl_amount') or 0.0) for order in closed_orders)
        open_notional = sum(abs(float(order.get('quantity') or 0.0) * float(order.get('entry_price') or 0.0)) for order in open_orders)
        summary = dict(portfolio or {})
        summary['open_orders_count'] = len(open_orders)
        summary['closed_orders_count'] = len(closed_orders)
        summary['total_realized_pnl'] = realized_pnl
        summary['open_notional'] = round(open_notional, 2)
        summary['available_cash'] = round(float(summary.get('cash_balance') or 0.0), 2)
        summary['orders'] = open_orders
        summary['positions'] = open_orders
        return summary



    def create_backtest_run(self, result: dict[str, Any]) -> str | None:
        if not self.enabled:
            return None
        with get_connection() as connection:
            row = connection.execute(
                '''
                INSERT INTO backtest_runs (
                    symbol, timeframe, strategy, initial_capital, final_equity,
                    total_trades, win_rate_percent, profit_factor,
                    total_pnl, return_percent, max_drawdown_percent,
                    metrics, equity_curve, trades
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
                RETURNING id
                ''',
                (
                    result.get('symbol'),
                    result.get('timeframe'),
                    result.get('strategy'),
                    result.get('initial_capital'),
                    result.get('final_equity'),
                    result.get('metrics', {}).get('total_trades'),
                    result.get('metrics', {}).get('win_rate_percent'),
                    result.get('metrics', {}).get('profit_factor'),
                    result.get('metrics', {}).get('total_pnl'),
                    result.get('metrics', {}).get('return_percent'),
                    result.get('metrics', {}).get('max_drawdown_percent'),
                    json.dumps(result.get('metrics', {})),
                    json.dumps(result.get('equity_curve', [])),
                    json.dumps(result.get('trades', [])),
                ),
            ).fetchone()
            connection.commit()
            return str(row['id'])

    def list_backtest_runs(self, limit: int = 25) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        with get_connection() as connection:
            rows = connection.execute(
                '''
                SELECT *
                FROM backtest_runs
                ORDER BY created_at DESC
                LIMIT %s
                ''',
                (limit,),
            ).fetchall()
            return [_serialise_row(row) for row in rows]

    def create_optimization_run(self, result: dict[str, Any]) -> str | None:
        if not self.enabled:
            return None
        with get_connection() as connection:
            row = connection.execute(
                '''
                INSERT INTO parameter_optimization_runs (
                    symbol, timeframe, strategy, objective, tested_combinations,
                    best_score, best_params, results
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                RETURNING id
                ''',
                (
                    result.get('symbol'),
                    result.get('timeframe'),
                    result.get('strategy'),
                    result.get('objective'),
                    result.get('tested_combinations'),
                    (result.get('best') or {}).get('score'),
                    json.dumps((result.get('best') or {}).get('params', {})),
                    json.dumps(result),
                ),
            ).fetchone()
            connection.commit()
            return str(row['id'])

    def list_optimization_runs(self, limit: int = 25) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        with get_connection() as connection:
            rows = connection.execute(
                '''
                SELECT *
                FROM parameter_optimization_runs
                ORDER BY created_at DESC
                LIMIT %s
                ''',
                (limit,),
            ).fetchall()
            return [_serialise_row(row) for row in rows]

    def create_ml_dataset_export(self, result: dict[str, Any]) -> str | None:
        if not self.enabled:
            return None
        with get_connection() as connection:
            row = connection.execute(
                '''
                INSERT INTO ml_dataset_exports (
                    row_count, feature_columns, target_columns, note, sample_rows
                )
                VALUES (%s, %s::jsonb, %s::jsonb, %s, %s::jsonb)
                RETURNING id
                ''',
                (
                    result.get('row_count'),
                    json.dumps(result.get('feature_columns', [])),
                    json.dumps(result.get('target_columns', [])),
                    result.get('note'),
                    json.dumps(result.get('rows', [])[:100]),
                ),
            ).fetchone()
            connection.commit()
            return str(row['id'])

    def list_ml_dataset_exports(self, limit: int = 25) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        with get_connection() as connection:
            rows = connection.execute(
                '''
                SELECT *
                FROM ml_dataset_exports
                ORDER BY created_at DESC
                LIMIT %s
                ''',
                (limit,),
            ).fetchall()
            return [_serialise_row(row) for row in rows]


    def create_ml_model_version(self, result: dict[str, Any]) -> str | None:
        if not self.enabled:
            return None
        with get_connection() as connection:
            row = connection.execute(
                """
                INSERT INTO ml_model_versions (
                    model_id, model_type, model_path, symbols, timeframes, strategies,
                    lookahead_bars, row_count, train_rows, test_rows,
                    feature_columns, class_labels, metrics, rule_baseline_metrics,
                    trading_metrics, rule_trading_metrics, feature_importance, metadata
                )
                VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s, %s,
                        %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb)
                RETURNING id
                """,
                (
                    result.get('model_id'),
                    result.get('model_type'),
                    result.get('model_path'),
                    json.dumps(result.get('symbols', [])),
                    json.dumps(result.get('timeframes', [])),
                    json.dumps(result.get('strategies', [])),
                    result.get('lookahead_bars'),
                    result.get('row_count'),
                    result.get('train_rows'),
                    result.get('test_rows'),
                    json.dumps(result.get('feature_columns', [])),
                    json.dumps(result.get('class_labels', [])),
                    json.dumps(result.get('metrics', {})),
                    json.dumps(result.get('rule_baseline_metrics', {})),
                    json.dumps(result.get('trading_metrics', {})),
                    json.dumps(result.get('rule_trading_metrics', {})),
                    json.dumps(result.get('feature_importance', [])),
                    json.dumps({key: value for key, value in result.items() if key not in {'prediction_preview'}}, default=str),
                ),
            ).fetchone()
            connection.commit()
            return str(row['id'])

    def list_ml_model_versions(self, limit: int = 25) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM ml_model_versions
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
            return [_serialise_row(row) for row in rows]

    def create_ml_prediction_run(self, result: dict[str, Any]) -> str | None:
        if not self.enabled:
            return None
        with get_connection() as connection:
            row = connection.execute(
                """
                INSERT INTO ml_prediction_runs (
                    model_id, symbol, timeframe, strategy, prediction_label,
                    prediction_direction, probabilities, features, result
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
                RETURNING id
                """,
                (
                    result.get('ml_prediction', {}).get('model_id') or result.get('model_id'),
                    result.get('symbol'),
                    result.get('timeframe'),
                    result.get('strategy_name') or result.get('strategy'),
                    result.get('ml_prediction', {}).get('prediction_label') or result.get('prediction_label'),
                    result.get('ml_prediction', {}).get('prediction_direction') or result.get('prediction_direction'),
                    json.dumps(result.get('ml_prediction', {}).get('probabilities', result.get('probabilities', {}))),
                    json.dumps(result.get('ml_prediction', {}).get('features_used', result.get('features_used', {}))),
                    json.dumps(result, default=str),
                ),
            ).fetchone()
            connection.commit()
            return str(row['id'])

    def list_ml_prediction_runs(self, limit: int = 25) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM ml_prediction_runs
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
            return [_serialise_row(row) for row in rows]


    def get_bot_config(self) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM bot_runtime_config
                WHERE config_name = 'default'
                LIMIT 1
                """
            ).fetchone()
            if not row:
                row = connection.execute(
                    """
                    INSERT INTO bot_runtime_config (config_name)
                    VALUES ('default')
                    RETURNING *
                    """
                ).fetchone()
                connection.commit()
            return _serialise_row(row)

    def update_bot_config(self, patch: dict[str, Any]) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        allowed = {
            'bot_enabled', 'scheduler_enabled', 'scheduler_interval_seconds', 'symbols', 'timeframes',
            'strategy_name', 'decision_mode', 'model_id', 'max_risk_per_trade', 'max_daily_loss',
            'max_open_trades', 'min_crv', 'min_confidence_score', 'max_risk_score', 'min_ml_probability',
            'min_model_profit_factor', 'min_model_win_rate', 'allow_degraded_fallback', 'enforce_validation_gate',
            'min_closed_trades_for_release', 'min_profit_factor_for_release', 'min_win_rate_for_release',
            'max_drawdown_percent_for_release', 'min_expectancy_per_trade_for_release',
            'min_data_quality_score_for_release', 'kill_switch_active'
        }
        if not patch:
            return self.get_bot_config()
        assignments = []
        values: list[Any] = []
        for key, value in patch.items():
            if key not in allowed:
                continue
            if key in {'symbols', 'timeframes'}:
                assignments.append(f"{key} = %s::jsonb")
                values.append(json.dumps(value or []))
            else:
                assignments.append(f"{key} = %s")
                values.append(value)
        if not assignments:
            return self.get_bot_config()
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO bot_runtime_config (config_name)
                VALUES ('default')
                ON CONFLICT (config_name) DO NOTHING
                """
            )
            query = f"""
                UPDATE bot_runtime_config
                SET {', '.join(assignments)}, updated_at = NOW()
                WHERE config_name = 'default'
                RETURNING *
            """
            row = connection.execute(query, tuple(values)).fetchone()
            connection.commit()
            return _serialise_row(row) if row else None

    def list_watchlist_symbols(self) -> list[str]:
        if not self.enabled:
            return []
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT a.symbol
                FROM watchlist_items w
                JOIN assets a ON a.id = w.asset_id
                ORDER BY a.symbol
                """
            ).fetchall()
            return [str(row['symbol']) for row in rows]

    def create_scheduler_run(self, result: dict[str, Any]) -> str | None:
        if not self.enabled:
            return None
        with get_connection() as connection:
            row = connection.execute(
                """
                INSERT INTO scheduler_runs (
                    source, status, symbols, timeframes, strategy, decision_mode, result
                )
                VALUES (%s, %s, %s::jsonb, %s::jsonb, %s, %s, %s::jsonb)
                RETURNING id
                """,
                (
                    result.get('source'),
                    result.get('status'),
                    json.dumps(result.get('symbols', [])),
                    json.dumps(result.get('timeframes', [])),
                    result.get('strategy'),
                    result.get('decision_mode'),
                    json.dumps(result.get('result', result), default=str),
                ),
            ).fetchone()
            connection.commit()
            return str(row['id'])

    def list_scheduler_runs(self, limit: int = 25) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM scheduler_runs
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
            return [_serialise_row(row) for row in rows]

    def create_decision_audit(self, audit: dict[str, Any]) -> str | None:
        if not self.enabled:
            return None
        with get_connection() as connection:
            row = connection.execute(
                """
                INSERT INTO bot_decision_audit (
                    symbol, timeframe, strategy, decision_mode, model_source, ml_model_id,
                    allowed, decision_score, reason, details
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING id
                """,
                (
                    audit.get('symbol'),
                    audit.get('timeframe'),
                    audit.get('strategy'),
                    audit.get('decision_mode'),
                    audit.get('model_source'),
                    audit.get('ml_model_id'),
                    audit.get('allowed'),
                    audit.get('decision_score'),
                    audit.get('reason'),
                    json.dumps(audit.get('details', {}), default=str),
                ),
            ).fetchone()
            connection.commit()
            return str(row['id'])

    def list_decision_audits(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM bot_decision_audit
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
            return [_serialise_row(row) for row in rows]

    def equity_curve_from_orders(self) -> dict[str, Any]:
        if not self.enabled:
            return {'items': [], 'persistence': 'memory'}
        with get_connection() as connection:
            portfolio = self._ensure_portfolio(connection)
            rows = connection.execute(
                """
                SELECT o.*, a.symbol
                FROM paper_orders o
                JOIN assets a ON a.id = o.asset_id
                WHERE o.status <> 'open'
                ORDER BY COALESCE(o.closed_at, o.opened_at) ASC
                """
            ).fetchall()
        starting = _to_float(portfolio.get('starting_balance')) or 10000.0
        equity = starting
        items: list[dict[str, Any]] = [{'timestamp': None, 'equity': round(equity, 2), 'pnl': 0.0, 'symbol': 'START'}]
        for row in rows:
            order = _serialise_row(row)
            pnl = float(order.get('pnl_amount') or 0.0)
            equity += pnl
            items.append({
                'timestamp': order.get('closed_at') or order.get('opened_at'),
                'equity': round(equity, 2),
                'pnl': round(pnl, 2),
                'symbol': order.get('symbol'),
                'status': order.get('status'),
                'decision_mode': order.get('decision_mode'),
            })
        return {'items': items, 'persistence': 'postgres'}


    def upsert_market_candles(self, symbol: str, timeframe: str, candles: list[dict[str, Any]], provider: str = 'unknown') -> int:
        if not self.enabled:
            return 0
        asset_id = self.get_or_create_asset(symbol=symbol, provider=provider)
        inserted_or_updated = 0
        with get_connection() as connection:
            for candle in candles:
                timestamp = candle.get('timestamp') or candle.get('candle_time')
                connection.execute(
                    """
                    INSERT INTO market_candles (asset_id, timeframe, open, high, low, close, volume, candle_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (asset_id, timeframe, candle_time)
                    DO UPDATE SET open = EXCLUDED.open,
                                  high = EXCLUDED.high,
                                  low = EXCLUDED.low,
                                  close = EXCLUDED.close,
                                  volume = EXCLUDED.volume
                    """,
                    (
                        asset_id,
                        timeframe,
                        candle.get('open'),
                        candle.get('high'),
                        candle.get('low'),
                        candle.get('close'),
                        candle.get('volume'),
                        timestamp,
                    ),
                )
                inserted_or_updated += 1
            connection.commit()
        return inserted_or_updated

    def list_market_candles(self, symbol: str, timeframe: str, limit: int = 500) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT c.*, a.symbol
                FROM market_candles c
                JOIN assets a ON a.id = c.asset_id
                WHERE a.symbol = %s AND c.timeframe = %s
                ORDER BY c.candle_time DESC
                LIMIT %s
                """,
                (symbol, timeframe, limit),
            ).fetchall()
        items = [_serialise_row(row) for row in rows]
        return list(reversed(items))

    def create_data_quality_report(self, symbol: str, timeframe: str, provider: str, report: dict[str, Any]) -> str | None:
        if not self.enabled:
            return None
        asset_id = self.get_or_create_asset(symbol=symbol, provider=provider)
        try:
            with get_connection() as connection:
                row = connection.execute(
                    """
                    INSERT INTO data_quality_reports (
                        asset_id, symbol, timeframe, provider, quality_score, trade_allowed,
                        issue_count, warning_count, largest_gap_ratio, latest_candle_age_minutes, report
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    RETURNING id
                    """,
                    (
                        asset_id,
                        symbol,
                        timeframe,
                        provider,
                        report.get('quality_score'),
                        report.get('trade_allowed'),
                        len(report.get('issues') or []),
                        len(report.get('warnings') or []),
                        report.get('largest_gap_ratio'),
                        report.get('latest_candle_age_minutes'),
                        json.dumps(report, default=str),
                    ),
                ).fetchone()
                connection.commit()
                return str(row['id'])
        except Exception:
            return None

    def list_data_quality_reports(self, symbol: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        try:
            with get_connection() as connection:
                if symbol:
                    rows = connection.execute(
                        """
                        SELECT * FROM data_quality_reports
                        WHERE symbol = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (symbol, limit),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        """
                        SELECT * FROM data_quality_reports
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (limit,),
                    ).fetchall()
            return [_serialise_row(row) for row in rows]
        except Exception:
            return []

    def export_table_rows(self, table_name: str, limit: int = 5000) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        allowed = {
            'orders': """
                SELECT o.*, a.symbol, a.asset_type
                FROM paper_orders o JOIN assets a ON a.id = o.asset_id
                ORDER BY o.opened_at DESC
            """,
            'signals': """
                SELECT s.*, a.symbol, a.asset_type
                FROM bot_signals s JOIN assets a ON a.id = s.asset_id
                ORDER BY s.created_at DESC
            """,
            'predictions': """
                SELECT p.*, a.symbol, a.asset_type
                FROM ai_predictions p JOIN assets a ON a.id = p.asset_id
                ORDER BY p.created_at DESC
            """,
            'decision_audits': """
                SELECT * FROM bot_decision_audit ORDER BY created_at DESC
            """,
            'backtests': """
                SELECT * FROM backtest_runs ORDER BY created_at DESC
            """,
            'data_quality': """
                SELECT * FROM data_quality_reports ORDER BY created_at DESC
            """,
        }
        if table_name not in allowed:
            raise ValueError(f'Unsupported export table: {table_name}')
        try:
            with get_connection() as connection:
                rows = connection.execute(allowed[table_name] + ' LIMIT %s', (limit,)).fetchall()
            return [_serialise_row(row) for row in rows]
        except Exception:
            return []

    def ops_readiness_snapshot(self) -> dict[str, Any]:
        snapshot: dict[str, Any] = {
            'persistence_enabled': self.enabled,
            'persistence_reachable': self.available if self.enabled else False,
        }
        if not self.enabled:
            snapshot['ready_for_realistic_paper_trading'] = False
            snapshot['blocking_reasons'] = ['PostgreSQL persistence is not configured.']
            return snapshot
        try:
            with get_connection() as connection:
                counts = connection.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM assets) AS assets,
                        (SELECT COUNT(*) FROM watchlist_items) AS watchlist_items,
                        (SELECT COUNT(*) FROM market_candles) AS stored_candles,
                        (SELECT COUNT(*) FROM paper_orders) AS paper_orders,
                        (SELECT COUNT(*) FROM bot_decision_audit) AS decision_audits,
                        (SELECT COUNT(*) FROM data_quality_reports) AS data_quality_reports
                    """
                ).fetchone()
                latest_quality = connection.execute(
                    """
                    SELECT * FROM data_quality_reports
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ).fetchone()
        except Exception as exc:
            snapshot['ready_for_realistic_paper_trading'] = False
            snapshot['blocking_reasons'] = [f'Readiness SQL check failed: {exc}']
            return snapshot
        snapshot.update(_serialise_row(counts))
        snapshot['latest_data_quality'] = _serialise_row(latest_quality) if latest_quality else None
        blocking = []
        warnings = []
        if int(snapshot.get('watchlist_items') or 0) == 0:
            warnings.append('No watchlist symbols configured; scheduler will use config symbols only.')
        if int(snapshot.get('stored_candles') or 0) == 0:
            warnings.append('No candles persisted yet; run /api/data/persist-candles for production-like operation.')
        if not latest_quality:
            warnings.append('No data-quality report exists yet.')
        elif not latest_quality.get('trade_allowed'):
            blocking.append('Latest data-quality report is not trade-allowed.')
        snapshot['blocking_reasons'] = blocking
        snapshot['warnings'] = warnings
        snapshot['ready_for_realistic_paper_trading'] = not blocking and snapshot['persistence_reachable']
        return snapshot



trading_repository = TradingRepository()
