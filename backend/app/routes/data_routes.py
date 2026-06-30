from __future__ import annotations

from fastapi import APIRouter, Query

from app.repositories.trading_repository import trading_repository
from app.services.data_quality_service import data_quality_service
from app.services.market_cache_service import market_cache_service
from app.services.market_data_service import get_market_data_service

router = APIRouter()


@router.get('/cache/status')
def cache_status():
    return market_cache_service.status()


@router.get('/quality')
def assess_data_quality(
    symbol: str = Query(...),
    timeframe: str = '1h',
    limit: int = Query(default=220, ge=80, le=1000),
    persist: bool = True,
):
    market = get_market_data_service()
    candles = market.get_candles(symbol=symbol, timeframe=timeframe, limit=limit)
    quote = market.get_quote(symbol)
    provider = quote.get('provider') or 'unknown'
    report = data_quality_service.assess_candles(candles=candles, timeframe=timeframe, provider=provider)
    report_id = None
    if persist and trading_repository.available:
        report_id = trading_repository.create_data_quality_report(symbol=symbol, timeframe=timeframe, provider=provider, report=report)
    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'provider': provider,
        'report': report,
        'report_id': report_id,
        'persistence': 'postgres' if report_id else 'memory',
    }


@router.post('/persist-candles')
def persist_candles(
    symbol: str = Query(...),
    timeframe: str = '1h',
    limit: int = Query(default=500, ge=80, le=5000),
):
    market = get_market_data_service()
    candles = market.get_candles(symbol=symbol, timeframe=timeframe, limit=limit)
    quote = market.get_quote(symbol)
    provider = quote.get('provider') or 'unknown'
    report = data_quality_service.assess_candles(candles=candles, timeframe=timeframe, provider=provider)
    stored = trading_repository.upsert_market_candles(symbol=symbol, timeframe=timeframe, candles=candles, provider=provider) if trading_repository.available else 0
    report_id = trading_repository.create_data_quality_report(symbol=symbol, timeframe=timeframe, provider=provider, report=report) if trading_repository.available else None
    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'provider': provider,
        'stored_candles': stored,
        'quality_report': report,
        'quality_report_id': report_id,
        'persistence': 'postgres' if trading_repository.available else 'memory',
    }


@router.get('/stored-candles')
def stored_candles(symbol: str = Query(...), timeframe: str = '1h', limit: int = Query(default=500, ge=1, le=5000)):
    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'items': trading_repository.list_market_candles(symbol=symbol, timeframe=timeframe, limit=limit),
        'persistence': 'postgres' if trading_repository.available else 'memory',
    }


@router.get('/quality/reports')
def quality_reports(symbol: str | None = None, limit: int = Query(default=100, ge=1, le=1000)):
    return {
        'items': trading_repository.list_data_quality_reports(symbol=symbol, limit=limit),
        'persistence': 'postgres' if trading_repository.available else 'memory',
    }
