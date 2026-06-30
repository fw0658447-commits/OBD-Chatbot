from fastapi import APIRouter, HTTPException, Query

from app.repositories.trading_repository import trading_repository
from app.schemas.ml_schema import MLCompareRequest, MLPredictAssetRequest, MLPredictRequest, MLTrainRequest
from app.services.ml_training_service import MLTrainingService

router = APIRouter()


@router.post('/train')
def train_model(request: MLTrainRequest):
    try:
        service = MLTrainingService()
        result = service.train(
            symbols=request.symbols,
            timeframes=request.timeframes,
            strategies=request.strategies,
            limit=request.limit,
            lookahead_bars=request.lookahead_bars,
            max_rows=request.max_rows,
            min_warmup_bars=request.min_warmup_bars,
            model_type=request.model_type,
            test_size=request.test_size,
            target_column=request.target_column,
        )
        db_id = None
        if request.persist and trading_repository.available:
            db_id = trading_repository.create_ml_model_version(result)
        result['db_id'] = db_id
        result['persistence'] = 'postgres' if db_id else 'memory'
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/predict')
def predict_features(request: MLPredictRequest):
    try:
        return MLTrainingService().predict_from_features(request.model_id, request.features)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/predict-asset')
def predict_asset(request: MLPredictAssetRequest):
    try:
        result = MLTrainingService().predict_asset(
            model_id=request.model_id,
            symbol=request.symbol,
            timeframe=request.timeframe,
            strategy_name=request.strategy_name,
            limit=request.limit,
        )
        prediction_id = None
        if trading_repository.available:
            prediction_id = trading_repository.create_ml_prediction_run(result)
        result['prediction_run_id'] = prediction_id
        result['persistence'] = 'postgres' if prediction_id else 'memory'
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/compare-rule-vs-ml')
def compare_rule_vs_ml(request: MLCompareRequest):
    try:
        return MLTrainingService().compare_rule_vs_ml(
            symbols=request.symbols,
            timeframes=request.timeframes,
            strategies=request.strategies,
            limit=request.limit,
            lookahead_bars=request.lookahead_bars,
            max_rows=request.max_rows,
            min_warmup_bars=80,
            model_type=request.model_type,
            test_size=0.25,
            target_column='target_label',
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get('/models')
def list_models(limit: int = Query(default=25, ge=1, le=200)):
    items = MLTrainingService().list_models()[:limit]
    if trading_repository.available:
        db_items = trading_repository.list_ml_model_versions(limit=limit)
        return {'items': items, 'database_items': db_items, 'persistence': 'postgres'}
    return {'items': items, 'database_items': [], 'persistence': 'memory'}


@router.get('/prediction-runs')
def list_prediction_runs(limit: int = Query(default=25, ge=1, le=200)):
    if not trading_repository.available:
        return {'items': [], 'persistence': 'memory'}
    return {'items': trading_repository.list_ml_prediction_runs(limit=limit), 'persistence': 'postgres'}
