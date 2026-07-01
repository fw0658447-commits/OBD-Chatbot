from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.repositories.trading_repository import trading_repository
from app.services.market_data_service import get_market_data_service
from app.services.local_persistence_service import local_persistence_service

router = APIRouter()


class WatchlistItem(BaseModel):
    symbol: str
    note: str | None = None
    alert_price: float | None = None
    target_price: float | None = None


@router.get('')
def list_watchlist(enrich: bool = True):
    items = trading_repository.list_watchlist() if trading_repository.available else local_persistence_service.list_watchlist()
    if enrich:
        market = get_market_data_service()
        enriched = []
        for item in items:
            symbol = item.get('symbol')
            quote = None
            try:
                quote = market.get_quote(symbol) if symbol else None
            except Exception as exc:
                quote = {'error': str(exc)}
            enriched.append({**item, 'quote': quote})
        items = enriched
    return {'items': items, 'persistence': 'postgres' if trading_repository.available else 'local_file'}


@router.post('')
def add_watchlist_item(item: WatchlistItem):
    symbol = item.symbol.strip().upper()
    if trading_repository.available:
        stored = trading_repository.add_watchlist_item(
            symbol=symbol,
            note=item.note,
            alert_price=item.alert_price,
            target_price=item.target_price,
        )
        return {'status': 'added', 'item': stored, 'persistence': 'postgres'}

    stored = local_persistence_service.add_watchlist_item(
        symbol=symbol,
        note=item.note,
        alert_price=item.alert_price,
        target_price=item.target_price,
    )
    return {'status': 'added', 'item': stored, 'persistence': 'local_file'}


@router.patch('/{symbol:path}')
def update_watchlist_item(symbol: str, item: WatchlistItem):
    normalized = symbol.strip().upper()
    if trading_repository.available:
        updated = trading_repository.update_watchlist_item(
            normalized,
            note=item.note,
            alert_price=item.alert_price,
            target_price=item.target_price,
        )
        return {'status': 'updated' if updated else 'not_found', 'item': updated, 'persistence': 'postgres'}

    updated = local_persistence_service.update_watchlist_item(
        normalized,
        note=item.note,
        alert_price=item.alert_price,
        target_price=item.target_price,
    )
    return {'status': 'updated' if updated else 'not_found', 'item': updated, 'persistence': 'local_file'}


@router.delete('/{symbol:path}')
def delete_watchlist_item(symbol: str):
    normalized = symbol.strip().upper()
    if trading_repository.available:
        deleted = trading_repository.delete_watchlist_item(normalized)
        return {'status': 'deleted' if deleted else 'not_found', 'symbol': normalized, 'persistence': 'postgres'}

    deleted = local_persistence_service.delete_watchlist_item(normalized)
    return {'status': 'deleted' if deleted else 'not_found', 'symbol': normalized, 'persistence': 'local_file'}
