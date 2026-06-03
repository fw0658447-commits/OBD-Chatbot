from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import backtest_routes, bot_routes, data_routes, export_routes, market_routes, ml_routes, monitoring_routes, ops_routes, prediction_routes, portfolio_routes, watchlist_routes
from app.repositories.trading_repository import trading_repository

app = FastAPI(title='Trading Cockpit API', version='1.2.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(market_routes.router, prefix='/api/market', tags=['Market'])
app.include_router(backtest_routes.router, prefix='/api/backtest', tags=['Backtest'])
app.include_router(ml_routes.router, prefix='/api/ml', tags=['ML'])
app.include_router(data_routes.router, prefix='/api/data', tags=['Data Quality'])
app.include_router(export_routes.router, prefix='/api/export', tags=['Export'])
app.include_router(ops_routes.router, prefix='/api/ops', tags=['Operations'])
app.include_router(monitoring_routes.router, prefix='/api/monitoring', tags=['Monitoring'])
app.include_router(prediction_routes.router, prefix='/api/predictions', tags=['Predictions'])
app.include_router(bot_routes.router, prefix='/api/bot', tags=['Bot'])
app.include_router(portfolio_routes.router, prefix='/api/portfolio', tags=['Portfolio'])
app.include_router(watchlist_routes.router, prefix='/api/watchlist', tags=['Watchlist'])


@app.get('/health')
def health_check() -> dict:
    return {
        'status': 'ok',
        'service': 'trading-cockpit-api',
        'version': '1.2.0-validation-monitoring',
        'database_configured': trading_repository.enabled,
        'database_reachable': trading_repository.available if trading_repository.enabled else False,
    }
