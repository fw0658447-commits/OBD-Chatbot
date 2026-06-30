from fastapi import APIRouter, Query

from app.repositories.trading_repository import trading_repository
from app.schemas.backtest_schema import (
    BacktestCompareRequest,
    BacktestRunRequest,
    MLDatasetRequest,
    ParameterOptimizationRequest,
    WalkForwardRequest,
)
from app.services.backtest_service import BacktestConfig, BacktestService

router = APIRouter()


@router.get('/strategies')
def list_strategies():
    return {'items': BacktestService().list_strategies()}


@router.get('/parameter-grid/{strategy_name}')
def parameter_grid(strategy_name: str):
    return {'strategy': strategy_name, 'grid': BacktestService().parameter_grid(strategy_name)}


@router.post('/run')
def run_backtest(request: BacktestRunRequest):
    service = BacktestService()
    result = service.run(
        BacktestConfig(
            symbol=request.symbol,
            timeframe=request.timeframe,
            limit=request.limit,
            initial_capital=request.initial_capital,
            risk_per_trade=request.risk_per_trade,
            max_hold_bars=request.max_hold_bars,
            min_warmup_bars=request.min_warmup_bars,
            min_confidence_score=request.min_confidence_score,
            max_risk_score=request.max_risk_score,
            min_crv=request.min_crv,
            strategy_name=request.strategy_name,
            strategy_params=request.strategy_params,
        )
    )
    backtest_id = None
    if request.persist and trading_repository.available:
        backtest_id = trading_repository.create_backtest_run(result)
    result['backtest_id'] = backtest_id
    result['persistence'] = 'postgres' if backtest_id else 'memory'
    return result


@router.post('/compare')
def compare_backtests(request: BacktestCompareRequest):
    service = BacktestService()
    return service.compare(
        symbols=request.symbols,
        timeframes=request.timeframes,
        strategies=request.strategies,
        limit=request.limit,
        initial_capital=request.initial_capital,
    )


@router.post('/walk-forward')
def walk_forward(request: WalkForwardRequest):
    return BacktestService().walk_forward(
        symbol=request.symbol,
        timeframe=request.timeframe,
        strategy_name=request.strategy_name,
        limit=request.limit,
        initial_capital=request.initial_capital,
        splits=request.splits,
        min_warmup_bars=request.min_warmup_bars,
    )


@router.post('/optimize')
def optimize_parameters(request: ParameterOptimizationRequest):
    service = BacktestService()
    result = service.optimize(
        symbol=request.symbol,
        timeframe=request.timeframe,
        strategy_name=request.strategy_name,
        limit=request.limit,
        initial_capital=request.initial_capital,
        risk_per_trade=request.risk_per_trade,
        objective=request.objective,
        max_combinations=request.max_combinations,
        parameter_grid=request.parameter_grid,
        min_warmup_bars=request.min_warmup_bars,
    )
    optimization_id = None
    if request.persist and trading_repository.available:
        optimization_id = trading_repository.create_optimization_run(result)
    result['optimization_id'] = optimization_id
    result['persistence'] = 'postgres' if optimization_id else 'memory'
    return result


@router.post('/ml-dataset')
def export_ml_dataset(request: MLDatasetRequest):
    result = BacktestService().export_ml_dataset(
        symbols=request.symbols,
        timeframes=request.timeframes,
        strategies=request.strategies,
        limit=request.limit,
        lookahead_bars=request.lookahead_bars,
        max_rows=request.max_rows,
        min_warmup_bars=request.min_warmup_bars,
    )
    if not request.include_csv:
        result.pop('csv', None)
    dataset_id = None
    if request.persist and trading_repository.available:
        dataset_id = trading_repository.create_ml_dataset_export(result)
    result['dataset_id'] = dataset_id
    result['persistence'] = 'postgres' if dataset_id else 'memory'
    return result


@router.get('/optimization-runs')
def list_optimization_runs(limit: int = Query(default=25, ge=1, le=200)):
    if not trading_repository.available:
        return {'items': [], 'persistence': 'memory'}
    return {'items': trading_repository.list_optimization_runs(limit=limit), 'persistence': 'postgres'}


@router.get('/ml-dataset-exports')
def list_ml_dataset_exports(limit: int = Query(default=25, ge=1, le=200)):
    if not trading_repository.available:
        return {'items': [], 'persistence': 'memory'}
    return {'items': trading_repository.list_ml_dataset_exports(limit=limit), 'persistence': 'postgres'}


@router.get('/runs')
def list_backtest_runs(limit: int = Query(default=25, ge=1, le=200)):
    if not trading_repository.available:
        return {'items': [], 'persistence': 'memory'}
    return {'items': trading_repository.list_backtest_runs(limit=limit), 'persistence': 'postgres'}
