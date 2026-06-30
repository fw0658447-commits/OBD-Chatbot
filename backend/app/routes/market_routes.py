from __future__ import annotations

from fastapi import APIRouter, Query

from app.repositories.trading_repository import trading_repository
from app.services.ai_prediction_service import AIPredictionService
from app.services.data_quality_service import data_quality_service
from app.services.indicator_service import IndicatorService
from app.services.market_data_service import get_market_data_service
from app.services.strategy_engine import StrategyEngine

router = APIRouter()

DEFAULT_MARKET_SYMBOLS = ['BTC/USD', 'ETH/USD', 'AAPL', 'MSFT', 'SPY', 'EUR/USD', 'XAU/USD']


def _market_service():
    return get_market_data_service()


@router.get('/assets/search')
def search_assets(q: str = Query(..., min_length=1)):
    service = _market_service()
    return {'results': service.search_assets(q)}


@router.get('/overview')
def get_market_overview(symbols: str | None = None):
    service = _market_service()
    requested_symbols = [s.strip() for s in symbols.split(',')] if symbols else DEFAULT_MARKET_SYMBOLS
    items = []
    for symbol in requested_symbols:
        if not symbol:
            continue
        try:
            items.append(service.get_quote(symbol))
        except Exception as exc:
            items.append({'symbol': symbol, 'error': str(exc), 'provider': 'unavailable'})
    return {'items': items}


@router.get('/quote')
def get_quote_query(symbol: str = Query(...)):
    service = _market_service()
    return service.get_quote(symbol)


@router.get('/quote/{symbol:path}')
def get_quote(symbol: str):
    service = _market_service()
    return service.get_quote(symbol)


@router.get('/candles')
def get_candles_query(symbol: str = Query(...), timeframe: str = '1h', limit: int = Query(default=200, ge=50, le=500)):
    service = _market_service()
    return {'symbol': symbol, 'timeframe': timeframe, 'candles': service.get_candles(symbol, timeframe, limit)}


@router.get('/candles/{symbol:path}')
def get_candles(symbol: str, timeframe: str = '1h', limit: int = 200):
    service = _market_service()
    return {'symbol': symbol, 'timeframe': timeframe, 'candles': service.get_candles(symbol, timeframe, limit)}


@router.get('/indicators')
def get_indicators_query(symbol: str = Query(...), timeframe: str = '1h'):
    market = _market_service()
    candles = market.get_candles(symbol, timeframe, 200)
    indicators = IndicatorService().calculate(candles)
    return {'symbol': symbol, 'timeframe': timeframe, 'indicators': indicators}


@router.get('/indicators/{symbol:path}')
def get_indicators(symbol: str, timeframe: str = '1h'):
    market = _market_service()
    candles = market.get_candles(symbol, timeframe, 200)
    indicators = IndicatorService().calculate(candles)
    return {'symbol': symbol, 'timeframe': timeframe, 'indicators': indicators}


@router.get('/analysis')
def get_asset_analysis(
    symbol: str = Query(...),
    timeframe: str = '1h',
    limit: int = Query(default=200, ge=50, le=500),
    persist_prediction: bool = False,
    strategy_name: str = StrategyEngine.DEFAULT_STRATEGY,
):
    market = _market_service()
    quote = market.get_quote(symbol)
    candles = market.get_candles(symbol, timeframe, limit)
    data_quality = data_quality_service.assess_candles(candles=candles, timeframe=timeframe, provider=quote.get('provider'))
    indicators = IndicatorService().calculate(candles)
    prediction = AIPredictionService().predict(symbol, timeframe, indicators)
    signal = StrategyEngine().create_signal(prediction=prediction, indicators=indicators, strategy_name=strategy_name)

    prediction_id = None
    if persist_prediction and trading_repository.available:
        asset_id = trading_repository.get_or_create_asset(symbol=symbol)
        prediction_id = trading_repository.create_prediction(asset_id=asset_id, prediction=prediction)

    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'quote': quote,
        'candles': candles,
        'data_quality': data_quality,
        'indicators': indicators,
        'prediction': prediction,
        'signal_preview': signal,
        'strategy_name': strategy_name,
        'available_strategies': StrategyEngine().list_strategies(),
        'prediction_id': prediction_id,
        'persistence': 'postgres' if trading_repository.available else 'memory',
    }
