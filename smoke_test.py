from app.services.backtest_service import BacktestConfig, BacktestService
from app.services.bot_engine import BotEngine
from app.services.ml_training_service import MLTrainingService

if __name__ == '__main__':
    engine = BotEngine()
    for symbol in ['BTC/USD', 'ETH/USD', 'AAPL', 'SPY', 'XAU/USD']:
        result = engine.run_cycle(
            symbol=symbol,
            timeframe='1h',
            portfolio_value=10000,
            open_trades_count=0,
            daily_pnl_percent=0,
            strategy_name='trend_atr_v0.7',
        )
        prediction = result.get('prediction', {})
        print(symbol, result['status'], prediction.get('direction'), prediction.get('confidence_score'))

    service = BacktestService()
    print('strategies', [item['name'] for item in service.list_strategies()])
    backtest = service.run(BacktestConfig(symbol='BTC/USD', timeframe='1h', limit=220, strategy_name='trend_atr_v0.7'))
    print('backtest', backtest['symbol'], backtest['strategy'], backtest['metrics']['total_trades'], backtest['metrics']['return_percent'])
    comparison = service.compare(
        symbols=['BTC/USD'],
        timeframes=['1h'],
        strategies=['trend_atr_v0.7', 'pullback_ema_v0.7'],
        limit=220,
        initial_capital=10000,
    )
    print('compare', len(comparison['items']), len(comparison['ranking']))

    ml = MLTrainingService()
    trained = ml.train(
        symbols=['BTC/USD', 'ETH/USD'],
        timeframes=['1h'],
        strategies=['trend_atr_v0.7'],
        limit=240,
        lookahead_bars=8,
        max_rows=400,
        min_warmup_bars=80,
        model_type='random_forest',
        test_size=0.25,
        target_column='target_label',
    )
    print('ml', trained['model_id'], trained['metrics']['accuracy'], trained['rule_baseline_metrics']['accuracy'])
    prediction = ml.predict_asset(trained['model_id'], 'BTC/USD', '1h', 'trend_atr_v0.7', 220)
    print('ml_predict', prediction['ml_prediction']['prediction_direction'])
