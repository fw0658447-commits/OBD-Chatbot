from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.repositories.trading_repository import trading_repository
from app.services.market_data_service import get_market_data_service

router = APIRouter()
watchlist: list[dict] = []


class WatchlistItem(BaseModel):
    symbol: str
    note: str | None = None
    alert_price: float | None = None
    target_price: float | None = None


@router.get('')
def list_watchlist(enrich: bool = True):
    items = trading_repository.list_watchlist() if trading_repository.available else watchlist
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
    return {'items': items, 'persistence': 'postgres' if trading_repository.available else 'memory'}


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

    existing = next((x for x in watchlist if x.get('symbol') == symbol), None)
    if existing:
        existing.update({'note': item.note, 'alert_price': item.alert_price, 'target_price': item.target_price})
        return {'status': 'updated', 'item': existing, 'persistence': 'memory'}

    payload = {'id': symbol, 'symbol': symbol, 'note': item.note, 'alert_price': item.alert_price, 'target_price': item.target_price}
    watchlist.append(payload)
    return {'status': 'added', 'item': payload, 'persistence': 'memory'}


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

    existing = next((x for x in watchlist if x.get('symbol') == normalized), None)
    if not existing:
        return {'status': 'not_found', 'symbol': normalized, 'persistence': 'memory'}
    existing.update({'note': item.note, 'alert_price': item.alert_price, 'target_price': item.target_price})
    return {'status': 'updated', 'item': existing, 'persistence': 'memory'}


@router.delete('/{symbol:path}')
def delete_watchlist_item(symbol: str):
    normalized = symbol.strip().upper()
    if trading_repository.available:
        deleted = trading_repository.delete_watchlist_item(normalized)
        return {'status': 'deleted' if deleted else 'not_found', 'symbol': normalized, 'persistence': 'postgres'}

    before = len(watchlist)
    watchlist[:] = [item for item in watchlist if item.get('symbol') != normalized]
    return {'status': 'deleted' if len(watchlist) < before else 'not_found', 'symbol': normalized, 'persistence': 'memory'}
