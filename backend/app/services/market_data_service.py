from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import requests

from app.config import settings
from app.services.market_cache_service import market_cache_service


class MarketDataError(RuntimeError):
    pass


class MockMarketDataService:
    """Deterministic-enough mock data for local MVP development."""

    def search_assets(self, query: str) -> List[Dict]:
        universe = [
            {'symbol': 'BTC/USD', 'name': 'Bitcoin US Dollar', 'asset_type': 'crypto'},
            {'symbol': 'ETH/USD', 'name': 'Ethereum US Dollar', 'asset_type': 'crypto'},
            {'symbol': 'AAPL', 'name': 'Apple Inc.', 'asset_type': 'stock', 'isin': 'US0378331005', 'wkn': '865985'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp.', 'asset_type': 'stock'},
            {'symbol': 'TSLA', 'name': 'Tesla Inc.', 'asset_type': 'stock'},
            {'symbol': 'NVDA', 'name': 'NVIDIA Corp.', 'asset_type': 'stock'},
            {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF', 'asset_type': 'etf'},
            {'symbol': 'QQQ', 'name': 'Invesco QQQ ETF', 'asset_type': 'etf'},
            {'symbol': 'EUR/USD', 'name': 'Euro US Dollar', 'asset_type': 'forex'},
            {'symbol': 'XAU/USD', 'name': 'Gold Spot US Dollar', 'asset_type': 'commodity'},
        ]
        q = query.lower().strip()
        return [
            item for item in universe
            if q in item['symbol'].lower()
            or q in item['name'].lower()
            or q == str(item.get('isin', '')).lower()
            or q == str(item.get('wkn', '')).lower()
        ]

    def get_quote(self, symbol: str) -> Dict:
        candles = self.get_candles(symbol=symbol, timeframe='1h', limit=5)
        last = candles[-1]
        previous = candles[-2]
        change = last['close'] - previous['close']
        change_percent = change / previous['close'] * 100
        return {
            'symbol': symbol,
            'price': round(last['close'], 4),
            'change': round(change, 4),
            'change_percent': round(change_percent, 2),
            'timestamp': last['timestamp'],
            'provider': 'mock',
        }

    def get_candles(self, symbol: str, timeframe: str, limit: int = 200) -> List[Dict]:
        base = self._base_price(symbol)
        interval_minutes = self._interval_minutes(timeframe)
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        start = now - timedelta(minutes=interval_minutes * (limit - 1))

        rng = random.Random(f'{symbol}-{timeframe}-{limit}')
        candles: List[Dict] = []
        close = base

        for i in range(limit):
            timestamp = start + timedelta(minutes=interval_minutes * i)
            trend = i * base * 0.00018
            wave = math.sin(i / 8) * base * 0.01
            noise = rng.uniform(-base * 0.003, base * 0.003)
            new_close = max(base * 0.1, base + trend + wave + noise)
            open_price = close
            high = max(open_price, new_close) * (1 + rng.uniform(0.0005, 0.004))
            low = min(open_price, new_close) * (1 - rng.uniform(0.0005, 0.004))
            volume = abs(rng.gauss(100000, 15000))

            candles.append({
                'timestamp': timestamp.isoformat(),
                'open': round(open_price, 4),
                'high': round(high, 4),
                'low': round(low, 4),
                'close': round(new_close, 4),
                'volume': round(volume, 2),
            })
            close = new_close

        return candles

    def _base_price(self, symbol: str) -> float:
        mapping = {
            'BTC/USD': 68000.0,
            'BTC-USD': 68000.0,
            'ETH/USD': 3600.0,
            'ETH-USD': 3600.0,
            'AAPL': 195.0,
            'MSFT': 430.0,
            'TSLA': 180.0,
            'NVDA': 120.0,
            'SPY': 525.0,
            'QQQ': 450.0,
            'EUR/USD': 1.08,
            'EURUSD=X': 1.08,
            'XAU/USD': 2350.0,
            'GC=F': 2350.0,
        }
        return mapping.get(symbol.upper(), 100.0)

    def _interval_minutes(self, timeframe: str) -> int:
        mapping = {'1m': 1, '5m': 5, '15m': 15, '1h': 60, '4h': 240, '1d': 1440, '1D': 1440}
        return mapping.get(timeframe, 60)


class YahooFreeMarketDataService:
    """Free online market-data fallback using Yahoo Finance chart/search endpoints.

    This is intended for Paper-Trading and analysis only. It does not replace licensed
    exchange feeds for live trading. If it fails, the app falls back to mock data when
    MARKET_PROVIDER_FALLBACK_ENABLED=true.
    """

    SEARCH_URL = 'https://query1.finance.yahoo.com/v1/finance/search'
    CHART_URL = 'https://query1.finance.yahoo.com/v8/finance/chart'

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 TradingCockpit/1.5'})

    def search_assets(self, query: str) -> List[Dict]:
        response = self.session.get(
            self.SEARCH_URL,
            params={'q': query, 'quotes_count': 10, 'news_count': 0},
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
        quotes = payload.get('quotes') or []
        items: List[Dict] = []
        for item in quotes[:12]:
            symbol = item.get('symbol')
            if not symbol:
                continue
            items.append({
                'symbol': self._from_yahoo_symbol(symbol),
                'provider_symbol': symbol,
                'name': item.get('longname') or item.get('shortname') or symbol,
                'asset_type': (item.get('quoteType') or 'unknown').lower(),
                'exchange': item.get('exchange'),
                'currency': item.get('currency'),
                'provider': 'yahoo_free',
            })
        return items

    def get_quote(self, symbol: str) -> Dict:
        candles = self.get_candles(symbol=symbol, timeframe='1h', limit=48)
        if len(candles) < 2:
            raise MarketDataError('Yahoo returned too few candles for quote.')
        last = candles[-1]
        previous = candles[-2]
        change = float(last['close']) - float(previous['close'])
        change_percent = (change / float(previous['close']) * 100) if float(previous['close']) else 0.0
        return {
            'symbol': symbol,
            'provider_symbol': self._to_yahoo_symbol(symbol),
            'price': round(float(last['close']), 6),
            'change': round(change, 6),
            'change_percent': round(change_percent, 4),
            'timestamp': last['timestamp'],
            'provider': 'yahoo_free',
        }

    def get_candles(self, symbol: str, timeframe: str, limit: int = 200) -> List[Dict]:
        yahoo_symbol = self._to_yahoo_symbol(symbol)
        interval = self._interval(timeframe)
        range_value = self._range(timeframe, limit)
        response = self.session.get(
            f'{self.CHART_URL}/{yahoo_symbol}',
            params={'interval': interval, 'range': range_value, 'includePrePost': 'false'},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        chart = payload.get('chart') or {}
        if chart.get('error'):
            raise MarketDataError(str(chart.get('error')))
        result = (chart.get('result') or [None])[0]
        if not result:
            raise MarketDataError('Yahoo returned no chart result.')
        timestamps = result.get('timestamp') or []
        quote = ((result.get('indicators') or {}).get('quote') or [{}])[0]
        opens = quote.get('open') or []
        highs = quote.get('high') or []
        lows = quote.get('low') or []
        closes = quote.get('close') or []
        volumes = quote.get('volume') or []
        candles: List[Dict] = []
        for i, ts in enumerate(timestamps):
            try:
                o, h, l, c = opens[i], highs[i], lows[i], closes[i]
                if o is None or h is None or l is None or c is None:
                    continue
                candles.append({
                    'timestamp': datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat(),
                    'open': round(float(o), 6),
                    'high': round(float(h), 6),
                    'low': round(float(l), 6),
                    'close': round(float(c), 6),
                    'volume': float(volumes[i] or 0) if i < len(volumes) else 0.0,
                })
            except Exception:
                continue
        if not candles:
            raise MarketDataError('Yahoo returned no usable candles.')
        return candles[-limit:]

    def _to_yahoo_symbol(self, symbol: str) -> str:
        s = symbol.strip().upper()
        mapping = {
            'BTC/USD': 'BTC-USD',
            'ETH/USD': 'ETH-USD',
            'EUR/USD': 'EURUSD=X',
            'GBP/USD': 'GBPUSD=X',
            'USD/JPY': 'JPY=X',
            'XAU/USD': 'GC=F',
            'XAG/USD': 'SI=F',
            'SPX': '^GSPC',
            'NDX': '^NDX',
            'DAX': '^GDAXI',
        }
        return mapping.get(s, s.replace('/', '-'))

    def _from_yahoo_symbol(self, symbol: str) -> str:
        mapping = {'BTC-USD': 'BTC/USD', 'ETH-USD': 'ETH/USD', 'EURUSD=X': 'EUR/USD', 'GC=F': 'XAU/USD'}
        return mapping.get(symbol, symbol)

    def _interval(self, timeframe: str) -> str:
        mapping = {'1m': '1m', '5m': '5m', '15m': '15m', '1h': '1h', '4h': '1h', '1D': '1d', '1d': '1d'}
        return mapping.get(timeframe, '1h')

    def _range(self, timeframe: str, limit: int) -> str:
        if timeframe == '1m':
            return '7d'
        if timeframe in {'5m', '15m'}:
            return '60d'
        if timeframe == '4h':
            return '1y'
        if timeframe in {'1D', '1d'}:
            return '5y'
        return '1y' if limit > 500 else '6mo'


class TwelveDataService:
    BASE_URL = 'https://api.twelvedata.com'

    def search_assets(self, query: str) -> List[Dict]:
        response = requests.get(
            f'{self.BASE_URL}/symbol_search',
            params={'symbol': query, 'apikey': settings.market_data_api_key},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get('data', [])
        return [
            {
                'symbol': item.get('symbol'),
                'name': item.get('instrument_name') or item.get('symbol'),
                'asset_type': item.get('instrument_type'),
                'exchange': item.get('exchange'),
                'currency': item.get('currency'),
                'provider': 'twelve_data',
            }
            for item in items
        ]

    def get_quote(self, symbol: str) -> Dict:
        response = requests.get(
            f'{self.BASE_URL}/quote',
            params={'symbol': symbol, 'apikey': settings.market_data_api_key},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if 'code' in data and data.get('status') == 'error':
            raise MarketDataError(data.get('message', 'Twelve Data error'))
        return {
            'symbol': symbol,
            'price': float(data.get('close') or data.get('price') or 0),
            'change': float(data.get('change') or 0),
            'change_percent': float(data.get('percent_change') or 0),
            'timestamp': data.get('datetime'),
            'provider': 'twelve_data',
        }

    def get_candles(self, symbol: str, timeframe: str, limit: int = 200) -> List[Dict]:
        response = requests.get(
            f'{self.BASE_URL}/time_series',
            params={
                'symbol': symbol,
                'interval': timeframe,
                'outputsize': limit,
                'apikey': settings.market_data_api_key,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if 'code' in data and data.get('status') == 'error':
            raise MarketDataError(data.get('message', 'Twelve Data error'))

        candles = []
        for row in data.get('values', []):
            candles.append({
                'timestamp': row['datetime'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row.get('volume') or 0),
            })
        return list(reversed(candles))


class CachedMarketDataService:
    def __init__(self, primary, fallback=None):
        self.primary = primary
        self.fallback = fallback

    def search_assets(self, query: str) -> List[Dict]:
        key = f'market:search:{query.lower().strip()}'
        cached = market_cache_service.get(key)
        if cached is not None:
            return cached
        try:
            result = self.primary.search_assets(query)
        except Exception as exc:
            if self.fallback is None:
                raise
            result = self.fallback.search_assets(query)
            for item in result:
                item['fallback_reason'] = str(exc)
        market_cache_service.set(key, result, ttl_seconds=300)
        return result

    def get_quote(self, symbol: str) -> Dict:
        key = f'market:quote:{symbol.upper()}'
        cached = market_cache_service.get(key)
        if cached is not None:
            cached['cache'] = 'hit'
            return cached
        try:
            result = self.primary.get_quote(symbol)
        except Exception as exc:
            if self.fallback is None:
                raise
            result = self.fallback.get_quote(symbol)
            result['fallback_reason'] = str(exc)
        result['cache'] = 'miss'
        market_cache_service.set(key, result, ttl_seconds=settings.quote_cache_ttl_seconds)
        return result

    def get_candles(self, symbol: str, timeframe: str, limit: int = 200) -> List[Dict]:
        key = f'market:candles:{symbol.upper()}:{timeframe}:{limit}'
        cached = market_cache_service.get(key)
        if cached is not None:
            return cached
        try:
            result = self.primary.get_candles(symbol, timeframe, limit)
        except Exception:
            if self.fallback is None:
                raise
            result = self.fallback.get_candles(symbol, timeframe, limit)
        market_cache_service.set(key, result, ttl_seconds=settings.candle_cache_ttl_seconds)
        return result


def get_market_data_service():
    provider = (settings.market_data_provider or 'free').lower().strip()
    mock = MockMarketDataService()
    free = YahooFreeMarketDataService()

    if provider == 'mock':
        return CachedMarketDataService(primary=mock)

    if provider in {'free', 'yahoo', 'yahoo_free', 'auto'}:
        fallback = mock if settings.market_provider_fallback_enabled else None
        return CachedMarketDataService(primary=free, fallback=fallback)

    if provider == 'twelve_data' and settings.market_data_api_key:
        fallback = free if settings.market_provider_fallback_enabled else None
        return CachedMarketDataService(primary=TwelveDataService(), fallback=fallback)

    # Misconfigured real provider: try free online first, then mock fallback.
    fallback = mock if settings.market_provider_fallback_enabled else None
    return CachedMarketDataService(primary=free, fallback=fallback)
