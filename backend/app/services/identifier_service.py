from __future__ import annotations

import re
from typing import Any

import requests

from app.config import settings
from app.services.market_data_service import get_market_data_service


ISIN_RE = re.compile(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$')
WKN_RE = re.compile(r'^[A-Z0-9]{6}$')

COMMON_IDENTIFIER_MAP: dict[str, dict[str, Any]] = {
    'US0378331005': {'symbol': 'AAPL', 'name': 'Apple Inc.', 'asset_type': 'stock', 'currency': 'USD', 'isin': 'US0378331005', 'wkn': '865985'},
    '865985': {'symbol': 'AAPL', 'name': 'Apple Inc.', 'asset_type': 'stock', 'currency': 'USD', 'isin': 'US0378331005', 'wkn': '865985'},
    'US5949181045': {'symbol': 'MSFT', 'name': 'Microsoft Corp.', 'asset_type': 'stock', 'currency': 'USD', 'isin': 'US5949181045'},
    'US88160R1014': {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'asset_type': 'stock', 'currency': 'USD', 'isin': 'US88160R1014'},
    'US67066G1040': {'symbol': 'NVDA', 'name': 'NVIDIA Corp.', 'asset_type': 'stock', 'currency': 'USD', 'isin': 'US67066G1040'},
    'US78462F1030': {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF Trust', 'asset_type': 'etf', 'currency': 'USD', 'isin': 'US78462F1030'},
}


class InstrumentIdentifierService:
    """Lookup and normalize instruments by ticker, ISIN, WKN or search text."""

    OPENFIGI_URL = 'https://api.openfigi.com/v3/mapping'

    def provider_status(self) -> dict[str, Any]:
        return {
            'openfigi_configured': bool(settings.openfigi_api_key),
            'market_data_provider': settings.market_data_provider,
            'market_data_configured': bool(settings.market_data_api_key) or settings.market_data_provider in {'mock', 'free', 'auto', 'yahoo_free'},
            'common_identifier_map_enabled': True,
            'supported_inputs': ['ticker', 'isin', 'wkn', 'figi', 'name/free-text'],
        }

    def lookup(self, query: str, query_type: str = 'auto', exchange: str | None = None) -> dict[str, Any]:
        normalized = query.strip().upper()
        detected_type = self._detect_type(normalized, query_type)

        if normalized in COMMON_IDENTIFIER_MAP:
            return {
                'query': query,
                'query_type': detected_type,
                'provider': 'common_identifier_map',
                'online': False,
                'results': [{**COMMON_IDENTIFIER_MAP[normalized], 'source': 'common_identifier_map'}],
                'warnings': ['Lokaler v1.5-Identifier-Fallback genutzt. Fuer breite ISIN/WKN-Abdeckung OPENFIGI_API_KEY setzen.'],
            }

        if detected_type in {'isin', 'wkn', 'figi'}:
            mapped = self._openfigi_lookup(normalized, detected_type, exchange=exchange)
            if mapped.get('results'):
                return mapped

        market_matches = self._market_search(query)
        return {
            'query': query,
            'query_type': detected_type,
            'provider': 'market_search_fallback',
            'online': settings.market_data_provider != 'mock',
            'results': market_matches,
            'warnings': [] if market_matches else ['Kein Instrument gefunden. Suche mit anderem Namen, Ticker, ISIN oder WKN versuchen.'],
        }

    def _detect_type(self, normalized: str, query_type: str) -> str:
        if query_type and query_type != 'auto':
            return query_type.lower()
        if ISIN_RE.match(normalized):
            return 'isin'
        if normalized.startswith('BBG') and len(normalized) >= 8:
            return 'figi'
        if WKN_RE.match(normalized) and '/' not in normalized:
            return 'wkn'
        if '/' in normalized or '.' in normalized or len(normalized) <= 6:
            return 'ticker'
        return 'name'

    def _openfigi_lookup(self, identifier: str, identifier_type: str, exchange: str | None = None) -> dict[str, Any]:
        id_type_map = {'isin': 'ID_ISIN', 'wkn': 'ID_WERTPAPIER', 'figi': 'ID_BB_GLOBAL'}
        payload = [{'idType': id_type_map.get(identifier_type, 'ID_ISIN'), 'idValue': identifier}]
        if exchange:
            payload[0]['exchCode'] = exchange

        headers = {'Content-Type': 'application/json'}
        if settings.openfigi_api_key:
            headers['X-OPENFIGI-APIKEY'] = settings.openfigi_api_key

        try:
            response = requests.post(self.OPENFIGI_URL, json=payload, headers=headers, timeout=12)
            response.raise_for_status()
            raw = response.json()
            first = raw[0] if raw else {}
            data = first.get('data') or []
            results = [self._normalize_openfigi_item(item, identifier) for item in data[:12]]
            return {
                'query': identifier,
                'query_type': identifier_type,
                'provider': 'openfigi',
                'online': True,
                'results': results,
                'warnings': first.get('warning') or [],
                'raw_count': len(data),
            }
        except Exception as exc:
            return {
                'query': identifier,
                'query_type': identifier_type,
                'provider': 'openfigi_error',
                'online': False,
                'results': [],
                'warnings': [f'OpenFIGI nicht erreichbar oder Rate-Limit/API-Problem: {exc}'],
            }

    def _market_search(self, query: str) -> list[dict[str, Any]]:
        try:
            matches = get_market_data_service().search_assets(query)
        except Exception as exc:
            return [{'symbol': query.upper(), 'name': 'Fallback-Symbol', 'asset_type': 'unknown', 'error': str(exc)}]
        return [
            {
                'symbol': item.get('symbol'),
                'name': item.get('name') or item.get('instrument_name') or item.get('symbol'),
                'asset_type': item.get('asset_type') or item.get('instrument_type'),
                'exchange': item.get('exchange'),
                'currency': item.get('currency'),
                'source': item.get('provider') or settings.market_data_provider,
            }
            for item in matches
        ]

    def _normalize_openfigi_item(self, item: dict[str, Any], identifier: str) -> dict[str, Any]:
        symbol = item.get('ticker') or item.get('symbol') or identifier
        exchange_code = item.get('exchCode')
        return {
            'symbol': symbol,
            'name': item.get('name'),
            'asset_type': item.get('securityType') or item.get('securityType2'),
            'exchange': exchange_code,
            'currency': item.get('currency'),
            'figi': item.get('figi'),
            'composite_figi': item.get('compositeFIGI'),
            'share_class_figi': item.get('shareClassFIGI'),
            'market_sector': item.get('marketSector'),
            'security_description': item.get('securityDescription'),
            'source': 'openfigi',
        }


identifier_service = InstrumentIdentifierService()
