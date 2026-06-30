from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.identifier_service import identifier_service
from app.services.internet_analysis_service import internet_analysis_service
from app.services.recommendation_service import recommendation_service
from app.services.strategy_engine import StrategyEngine

router = APIRouter()


@router.get('/providers/status')
def provider_status():
    return {
        'identifier': identifier_service.provider_status(),
        'internet_analysis': internet_analysis_service.provider_status(),
    }


@router.get('/instrument/lookup')
def instrument_lookup(
    query: str = Query(..., min_length=1),
    query_type: str = Query('auto'),
    exchange: str | None = None,
):
    return identifier_service.lookup(query=query, query_type=query_type, exchange=exchange)


@router.get('/internet-analysis')
def internet_analysis(symbol: str = Query(...), query: str | None = None, max_items: int = Query(default=8, ge=1, le=20)):
    return internet_analysis_service.analyze(symbol=symbol, query=query, max_items=max_items)


@router.get('/recommendation')
def recommendation(
    symbol: str = Query(...),
    timeframe: str = '1h',
    strategy_name: str = StrategyEngine.DEFAULT_STRATEGY,
    include_internet: bool = True,
):
    return recommendation_service.recommend(
        symbol=symbol,
        timeframe=timeframe,
        strategy_name=strategy_name,
        include_internet=include_internet,
    )
