from fastapi import APIRouter, Query

from app.repositories.trading_repository import trading_repository
from app.schemas.prediction_schema import PredictionRequest
from app.services.ai_prediction_service import AIPredictionService
from app.services.indicator_service import IndicatorService
from app.services.market_data_service import get_market_data_service

router = APIRouter()


@router.post('/create')
def create_prediction(request: PredictionRequest):
    market = get_market_data_service()
    candles = market.get_candles(request.symbol, request.timeframe, 200)
    indicators = IndicatorService().calculate(candles)
    prediction = AIPredictionService().predict(request.symbol, request.timeframe, indicators)
    if trading_repository.available:
        asset_id = trading_repository.get_or_create_asset(symbol=request.symbol)
        prediction_id = trading_repository.create_prediction(asset_id=asset_id, prediction=prediction)
    else:
        asset_id = None
        prediction_id = None
    return {
        'prediction': prediction,
        'prediction_id': prediction_id,
        'indicators': indicators,
        'persistence': {
            'enabled': trading_repository.enabled,
            'database_reachable': trading_repository.available if trading_repository.enabled else False,
        },
    }


@router.get('')
def list_predictions(limit: int = Query(default=50, ge=1, le=200)):
    if not trading_repository.available:
        return {'items': [], 'persistence': 'memory'}
    return {'items': trading_repository.list_predictions(limit=limit), 'persistence': 'postgres'}
