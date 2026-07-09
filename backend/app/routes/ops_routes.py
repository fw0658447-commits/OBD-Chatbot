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


def _setup_item(
    key: str,
    title: str,
    status: str,
    description: str,
    next_step: str,
    env_vars: list[str],
    active_value: str,
    configured: bool,
    optional: bool,
) -> dict:
    return {
        'key': key,
        'title': title,
        'status': status,
        'description': description,
        'next_step': next_step,
        'env_vars': env_vars,
        'active_value': active_value,
        'configured': configured,
        'optional': optional,
    }


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


@router.get('/setup-guide')
def setup_guide():
    provider = (settings.market_data_provider or 'free').lower().strip()
    free_provider = provider in {'free', 'auto', 'yahoo', 'yahoo_free'}
    has_market_key = bool(settings.market_data_api_key)
    local_persistence = local_persistence_service.status()
    database_reachable = trading_repository.available if trading_repository.enabled else False
    identifier_status = identifier_service.provider_status()
    internet_status = internet_analysis_service.provider_status()
    secure_paper_mode = settings.bot_mode == 'paper' and settings.live_trading_hard_locked and not settings.live_trading_enabled

    market_ready = free_provider or (provider == 'twelve_data' and has_market_key)
    storage_ready = database_reachable or bool(local_persistence.get('enabled'))
    openfigi_ready = bool(identifier_status.get('openfigi_configured'))
    news_ready = bool(internet_status.get('finnhub_configured') or internet_status.get('alpha_vantage_configured'))

    items = [
        _setup_item(
            key='safe_mode',
            title='Sicherer Paper-Modus',
            status='ready' if secure_paper_mode else 'attention',
            description='Echtes Trading ist gesperrt und die App arbeitet im Paper-Modus.' if secure_paper_mode else 'Bitte Paper-Modus und Live-Trading-Sperre pruefen.',
            next_step='So lassen, solange nur getestet wird.' if secure_paper_mode else 'BOT_MODE=paper und LIVE_TRADING_HARD_LOCKED=true setzen.',
            env_vars=['BOT_MODE', 'LIVE_TRADING_HARD_LOCKED'],
            active_value='Paper-Trading gesperrt' if secure_paper_mode else 'Bitte pruefen',
            configured=secure_paper_mode,
            optional=False,
        ),
        _setup_item(
            key='storage',
            title='Speicherung',
            status='ready' if storage_ready else 'attention',
            description='Daten werden lokal gespeichert.' if not database_reachable and storage_ready else ('PostgreSQL ist erreichbar.' if database_reachable else 'Keine dauerhafte Speicherung erreichbar.'),
            next_step='Lokale Datei reicht fuer diesen Rechner. Fuer Team/Server spaeter DATABASE_URL setzen.' if storage_ready and not database_reachable else ('Keine Aktion noetig.' if storage_ready else 'LOCAL_STATE_PATH oder DATABASE_URL setzen.'),
            env_vars=['LOCAL_STATE_PATH', 'DATABASE_URL'],
            active_value='Lokale Datei' if storage_ready and not database_reachable else ('PostgreSQL' if database_reachable else 'Nicht bereit'),
            configured=storage_ready,
            optional=False,
        ),
        _setup_item(
            key='market_data',
            title='Marktdaten',
            status='ready' if market_ready else 'attention',
            description='Kostenlose Online-Marktdaten sind aktiv.' if free_provider else ('Twelve Data ist konfiguriert.' if market_ready else 'Der gewaehlte Marktdatenanbieter braucht noch einen API-Key.'),
            next_step='Optional fuer bessere Datenqualitaet Twelve Data mit API-Key setzen.' if free_provider else ('Datenqualitaet im Paper-Test beobachten.' if market_ready else 'MARKET_DATA_API_KEY setzen oder MARKET_DATA_PROVIDER=free nutzen.'),
            env_vars=['MARKET_DATA_PROVIDER', 'MARKET_DATA_API_KEY'],
            active_value=provider,
            configured=market_ready,
            optional=False,
        ),
        _setup_item(
            key='identifier',
            title='ISIN/WKN-Suche',
            status='ready' if openfigi_ready else 'optional',
            description='OpenFIGI ist aktiv fuer breite Instrumenten-Zuordnung.' if openfigi_ready else 'Lokale Standard-Zuordnung und Marktdaten-Suche sind aktiv.',
            next_step='Keine Aktion noetig.' if openfigi_ready else 'Optional OPENFIGI_API_KEY setzen, wenn ISIN/WKN/FIGI breiter abgedeckt werden sollen.',
            env_vars=['OPENFIGI_API_KEY'],
            active_value='OpenFIGI' if openfigi_ready else 'Fallback aktiv',
            configured=openfigi_ready,
            optional=True,
        ),
        _setup_item(
            key='news',
            title='News und Sentiment',
            status='ready' if news_ready else 'optional',
            description='API-basierte News/Sentiment-Daten sind aktiv.' if news_ready else 'Kostenloser Yahoo-RSS-News-Fallback ist aktiv.',
            next_step='Keine Aktion noetig.' if news_ready else 'Optional FINNHUB_API_KEY oder ALPHA_VANTAGE_API_KEY setzen.',
            env_vars=['FINNHUB_API_KEY', 'ALPHA_VANTAGE_API_KEY', 'INTERNET_ANALYSIS_PROVIDER'],
            active_value=str(internet_status.get('effective_provider') or 'auto'),
            configured=news_ready,
            optional=True,
        ),
        _setup_item(
            key='cache',
            title='Performance-Cache',
            status='ready' if settings.redis_url else 'optional',
            description='Redis ist konfiguriert.' if settings.redis_url else 'In-Memory-Cache ist aktiv und reicht fuer lokale Tests.',
            next_step='Optional REDIS_URL setzen, wenn die App dauerhaft auf einem Server laeuft.' if not settings.redis_url else 'Keine Aktion noetig.',
            env_vars=['REDIS_URL'],
            active_value='Redis' if settings.redis_url else 'In-Memory',
            configured=bool(settings.redis_url),
            optional=True,
        ),
    ]
    profiles = [
        {
            'key': 'local_safe',
            'title': 'Lokaler sicherer Test',
            'best_for': 'Schnell starten auf diesem Rechner',
            'description': 'Paper-Trading, kostenlose Marktdaten und lokale Dateiablage.',
            'env_lines': [
                'BOT_MODE=paper',
                'LIVE_TRADING_HARD_LOCKED=true',
                'MARKET_DATA_PROVIDER=free',
                'LOCAL_STATE_PATH=.local/trading-state.json',
                'NEXT_PUBLIC_API_BASE_URL=auto',
            ],
        },
        {
            'key': 'better_market_data',
            'title': 'Bessere Marktdaten',
            'best_for': 'Mehr Datenqualitaet im Paper-Test',
            'description': 'Twelve Data als bezahlter/limitierter API-Anbieter mit Free-Fallback.',
            'env_lines': [
                'MARKET_DATA_PROVIDER=twelve_data',
                'MARKET_DATA_API_KEY=DEIN_TWELVE_DATA_KEY',
                'MARKET_PROVIDER_FALLBACK_ENABLED=true',
            ],
        },
        {
            'key': 'research_plus',
            'title': 'Recherche erweitern',
            'best_for': 'Mehr Treffer bei ISIN/WKN und News',
            'description': 'Optionale Anbieter fuer Instrumenten-Mapping, Nachrichten und Sentiment.',
            'env_lines': [
                'OPENFIGI_API_KEY=DEIN_OPENFIGI_KEY',
                'FINNHUB_API_KEY=DEIN_FINNHUB_KEY',
                'ALPHA_VANTAGE_API_KEY=DEIN_ALPHA_VANTAGE_KEY',
                'INTERNET_ANALYSIS_PROVIDER=auto',
            ],
        },
    ]
    required_ready = all(item['status'] == 'ready' for item in items if not item['optional'])
    return {
        'status': 'ready' if required_ready else 'attention',
        'summary': 'Grundsetup bereit: sicherer Paper-Modus, Speicherung und Marktdaten sind aktiv.' if required_ready else 'Grundsetup braucht noch Aufmerksamkeit.',
        'items': items,
        'profiles': profiles,
        'restart_steps': [
            'Vorlage kopieren und in .env einfuegen.',
            'Platzhalter wie DEIN_TWELVE_DATA_KEY durch eigene Keys ersetzen.',
            'Backend und Frontend neu starten, damit die neuen Werte geladen werden.',
            'Setup-Seite erneut oeffnen und Status pruefen.',
        ],
        'env_file': '.env',
        'env_example': '.env.example',
        'secret_note': 'API-Keys werden aus Sicherheitsgruenden nicht angezeigt, nur ob sie konfiguriert sind.',
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
