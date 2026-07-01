from __future__ import annotations

from app.config import settings
from fastapi import APIRouter, Query

from app.repositories.trading_repository import trading_repository
from app.services.market_cache_service import market_cache_service
from app.services.validation_monitoring_service import validation_monitoring_service
from app.services.identifier_service import identifier_service
from app.services.internet_analysis_service import internet_analysis_service
from app.services.local_persistence_service import local_persistence_service

router = APIRouter()


@router.get('/readiness')
def readiness():
    snapshot = trading_repository.ops_readiness_snapshot()
    checks = {
        'live_trading_hard_locked': settings.live_trading_hard_locked and not settings.live_trading_enabled,
        'paper_cost_model_enabled': settings.paper_spread_bps > 0 or settings.paper_slippage_bps > 0 or settings.paper_commission_bps > 0,
        'cache': market_cache_service.status(),
        'market_provider': settings.market_data_provider,
        'fallback_enabled': settings.market_provider_fallback_enabled,
        'block_trades_on_data_quality_fail': settings.block_trades_on_data_quality_fail,
    }
    blocking = list(snapshot.get('blocking_reasons') or [])
    if not checks['live_trading_hard_locked']:
        blocking.append('Live trading hard lock is not active.')
    if not checks['paper_cost_model_enabled']:
        blocking.append('Paper cost model is disabled; results are too optimistic.')
    validation = validation_monitoring_service.validation_gates()
    if not validation.get('released_for_paper_automation'):
        blocking.append('Validation gates are not fully released for production-like paper automation.')
    ready = not blocking and bool(snapshot.get('persistence_reachable'))
    return {
        'status': 'ready' if ready else 'not_ready',
        'ready_for_realistic_paper_trading': ready,
        'blocking_reasons': blocking,
        'warnings': snapshot.get('warnings', []),
        'repository': snapshot,
        'checks': checks,
        'validation': validation,
        'recommended_next_gate': 'Pass v1.2 validation gates: >=100 closed paper trades, adequate Profit Factor, controlled Drawdown and clean data-quality reports.',
    }


@router.get('/status')
def system_status():
    provider = (settings.market_data_provider or 'free').lower()
    has_api_key = bool(settings.market_data_api_key)
    cache_status = market_cache_service.status()
    database_reachable = trading_repository.available if trading_repository.enabled else False
    local_persistence = local_persistence_service.status()
    market_check = {
        'status': 'unknown',
        'symbol': 'BTC/USD',
        'provider': provider,
        'price': None,
        'error': None,
        'fallback_used': False,
    }
    try:
        from app.services.market_data_service import get_market_data_service
        quote = get_market_data_service().get_quote('BTC/USD')
        market_check.update({
            'status': 'online' if not quote.get('error') else 'error',
            'provider': quote.get('provider', provider),
            'price': quote.get('price'),
            'timestamp': quote.get('timestamp'),
            'cache': quote.get('cache'),
            'fallback_used': bool(quote.get('fallback_reason')),
            'fallback_reason': quote.get('fallback_reason'),
        })
    except Exception as exc:
        market_check.update({'status': 'offline', 'error': str(exc)})

    free_provider = provider in {'free', 'auto', 'yahoo', 'yahoo_free'}
    real_provider_configured = free_provider or (provider != 'mock' and has_api_key)
    simulated_data = provider == 'mock' or market_check.get('provider') == 'mock'
    return {
        'status': 'online' if market_check['status'] == 'online' else 'degraded',
        'backend': 'online',
        'database': 'online' if database_reachable else 'offline',
        'local_persistence': local_persistence,
        'cache': cache_status,
        'market_data': market_check,
        'market_data_provider': provider,
        'real_provider_configured': real_provider_configured,
        'simulated_data': simulated_data,
        'fallback_enabled': settings.market_provider_fallback_enabled,
        'live_trading_enabled': settings.live_trading_enabled,
        'live_trading_hard_locked': settings.live_trading_hard_locked,
        'paper_mode': settings.bot_mode == 'paper',
        'identifier_provider': identifier_service.provider_status(),
        'internet_analysis_provider': internet_analysis_service.provider_status(),
        'recommended_action': 'Kostenlosen Online-Provider aktiv. Fuer hoehere Datenqualitaet optional Twelve Data/Finnhub/OpenFIGI/Alpha Vantage API-Keys setzen.' if free_provider else ('API-Key fuer echte Marktdaten setzen.' if not real_provider_configured else 'Datenqualitaet pruefen und Paper-Trading fortsetzen.'),
    }


@router.get('/full-diagnostics')
def full_diagnostics(symbol: str = Query('BTC/USD'), timeframe: str = Query('1h'), strategy_name: str = Query('trend_atr_v0.7')):
    checks: list[dict] = []

    db_ok = trading_repository.available if trading_repository.enabled else False
    local_persistence = local_persistence_service.status()
    checks.append({
        'name': 'Speicherung',
        'ok': db_ok or bool(local_persistence.get('enabled')),
        'message': 'PostgreSQL erreichbar' if db_ok else f"Lokale Dateiablage aktiv: {local_persistence.get('path')}",
    })

    try:
        from app.services.market_data_service import get_market_data_service
        quote = get_market_data_service().get_quote(symbol)
        checks.append({'name': 'Marktdaten Quote', 'ok': bool(quote.get('price')), 'message': f"{quote.get('provider')} price={quote.get('price')} fallback={bool(quote.get('fallback_reason'))}"})
    except Exception as exc:
        checks.append({'name': 'Marktdaten Quote', 'ok': False, 'message': str(exc)})

    try:
        from app.services.market_data_service import get_market_data_service
        candles = get_market_data_service().get_candles(symbol, timeframe, 120)
        checks.append({'name': 'Kerzendaten', 'ok': len(candles) >= 50, 'message': f'{len(candles)} Kerzen geladen'})
    except Exception as exc:
        checks.append({'name': 'Kerzendaten', 'ok': False, 'message': str(exc)})

    try:
        rec = __import__('app.services.recommendation_service', fromlist=['recommendation_service']).recommendation_service.recommend(symbol=symbol, timeframe=timeframe, strategy_name=strategy_name, include_internet=True)
        decision = rec.get('decision', {})
        checks.append({'name': 'Recommendation Service', 'ok': decision.get('action') is not None, 'message': f"{decision.get('action')} / {decision.get('trade_decision')} / Risiko {decision.get('risk_level')}"})
    except Exception as exc:
        checks.append({'name': 'Recommendation Service', 'ok': False, 'message': str(exc)})

    try:
        online = internet_analysis_service.analyze(symbol, max_items=3)
        checks.append({'name': 'Internet-Analyse', 'ok': bool(online.get('online')), 'message': online.get('summary') or online.get('warning')})
    except Exception as exc:
        checks.append({'name': 'Internet-Analyse', 'ok': False, 'message': str(exc)})

    try:
        ledger = trading_repository.list_cash_transactions(limit=1) if trading_repository.available else local_persistence_service.list_cash_transactions(limit=1)
        checks.append({'name': 'Paper-Konto', 'ok': True, 'message': f'Cash-Ledger erreichbar, letzte Eintraege: {len(ledger)}'})
    except Exception as exc:
        checks.append({'name': 'Paper-Konto', 'ok': False, 'message': str(exc)})

    ok = all(item['ok'] for item in checks if item['name'] not in {'Internet-Analyse'})
    return {
        'status': 'ok' if ok else 'degraded',
        'checks': checks,
        'symbol': symbol,
        'timeframe': timeframe,
        'strategy_name': strategy_name,
    }
