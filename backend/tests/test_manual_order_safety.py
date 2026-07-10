from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from app.config import settings
from app.routes import portfolio_routes
from app.services.bot_runtime_service import bot_runtime_service
from app.services.local_persistence_service import local_persistence_service
from app.services.paper_trading_engine import PaperTradingEngine


class _FixedMarketDataService:
    def get_quote(self, symbol: str) -> dict:
        return {'symbol': symbol, 'price': 100.0, 'provider': 'test', 'cache': 'test'}


class ManualOrderSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self._previous_state_path = settings.local_state_path
        self._previous_market_service = portfolio_routes.get_market_data_service
        self._previous_config = bot_runtime_service.get_config()

        settings.local_state_path = str(Path(self._temporary_directory.name) / 'paper-state.json')
        portfolio_routes.get_market_data_service = lambda: _FixedMarketDataService()
        bot_runtime_service.update_config({'kill_switch_active': False, 'max_open_trades': 1})

    def tearDown(self) -> None:
        settings.local_state_path = self._previous_state_path
        portfolio_routes.get_market_data_service = self._previous_market_service
        bot_runtime_service.update_config(self._previous_config)
        self._temporary_directory.cleanup()

    def test_rejects_order_above_available_cash(self) -> None:
        local_persistence_service.reset_paper_account(balance=100.0)
        request = portfolio_routes.ManualPaperOrderRequest(
            symbol='TEST',
            side='long',
            notional_amount=101.0,
            entry_price=100.0,
        )

        with self.assertRaises(HTTPException) as raised:
            portfolio_routes.create_manual_paper_order(request)

        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn('übersteigt verfügbares Paper-Guthaben', raised.exception.detail)
        self.assertEqual(local_persistence_service.list_orders(status='open'), [])

    def test_rechecks_position_limit_when_order_is_saved(self) -> None:
        local_persistence_service.reset_paper_account(balance=1000.0)
        request = portfolio_routes.ManualPaperOrderRequest(
            symbol='TEST',
            side='long',
            notional_amount=100.0,
            entry_price=100.0,
        )

        result = portfolio_routes.create_manual_paper_order(request)
        self.assertEqual(result['status'], 'manual_order_opened')

        with self.assertRaises(HTTPException) as raised:
            portfolio_routes.create_manual_paper_order(request)

        self.assertEqual(raised.exception.status_code, 429)
        self.assertIn('Positionslimit erreicht', raised.exception.detail)
        self.assertEqual(len(local_persistence_service.list_orders(status='open')), 1)

    def test_open_position_equity_counts_entry_commission_once(self) -> None:
        local_persistence_service.reset_paper_account(balance=10000.0)
        engine = PaperTradingEngine()
        order = engine.execute_order(
            signal={'signal_type': 'long', 'entry_price': 100.0, 'stop_loss': 95.0, 'take_profit': 110.0},
            quantity=10.0,
        )
        local_persistence_service.add_manual_order(symbol='TEST', order=order, max_open_trades=1)

        snapshot = local_persistence_service.portfolio_snapshot(_FixedMarketDataService(), engine)
        portfolio = snapshot['portfolio']

        self.assertAlmostEqual(
            portfolio['current_equity'],
            portfolio['starting_balance'] + portfolio['total_unrealized_pnl'],
            places=2,
        )

    def test_closed_position_cash_matches_realized_equity(self) -> None:
        local_persistence_service.reset_paper_account(balance=10000.0)
        engine = PaperTradingEngine()
        order = engine.execute_order(
            signal={'signal_type': 'long', 'entry_price': 100.0, 'stop_loss': 95.0, 'take_profit': 110.0},
            quantity=10.0,
        )
        stored = local_persistence_service.add_manual_order(symbol='TEST', order=order, max_open_trades=1)
        closed = engine.close_order(order=stored, exit_price=100.0)
        local_persistence_service.close_order(order_id=stored['id'], closed_order=closed)

        portfolio = local_persistence_service.portfolio_summary()

        self.assertAlmostEqual(portfolio['cash_balance'], portfolio['current_equity'], places=2)
        self.assertAlmostEqual(
            portfolio['current_equity'],
            portfolio['starting_balance'] + portfolio['total_realized_pnl'],
            places=2,
        )


if __name__ == '__main__':
    unittest.main()
