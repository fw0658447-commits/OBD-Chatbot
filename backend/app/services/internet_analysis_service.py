from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import requests

from app.config import settings


class InternetAnalysisService:
    """Fetch lightweight online context for a symbol.

    v1.5 adds a free Yahoo Finance RSS fallback so the app can show real online
    headline context even without paid API keys. API-key providers remain preferred
    when configured.
    """

    FINNHUB_URL = 'https://finnhub.io/api/v1'
    ALPHA_URL = 'https://www.alphavantage.co/query'
    YAHOO_RSS_URL = 'https://feeds.finance.yahoo.com/rss/2.0/headline'

    def provider_status(self) -> dict[str, Any]:
        return {
            'finnhub_configured': bool(settings.finnhub_api_key),
            'alpha_vantage_configured': bool(settings.alpha_vantage_api_key),
            'free_yahoo_news_enabled': True,
            'internet_analysis_enabled': True,
            'preferred_provider': settings.internet_analysis_provider,
            'effective_provider': self._effective_provider(),
        }

    def analyze(self, symbol: str, query: str | None = None, max_items: int = 8) -> dict[str, Any]:
        symbol = symbol.strip().upper()
        articles: list[dict[str, Any]] = []
        provider_results: list[dict[str, Any]] = []
        preferred = (settings.internet_analysis_provider or 'auto').lower()

        if preferred in {'auto', 'finnhub'} and settings.finnhub_api_key:
            result = self._finnhub_news(symbol, max_items=max_items)
            provider_results.append(result)
            articles.extend(result.get('articles', []))

        if preferred in {'auto', 'alpha_vantage'} and settings.alpha_vantage_api_key and len(articles) < max_items:
            result = self._alpha_news_sentiment(symbol, query=query, max_items=max_items - len(articles))
            provider_results.append(result)
            articles.extend(result.get('articles', []))

        if preferred in {'auto', 'free', 'yahoo', 'yahoo_rss'} and len(articles) < max_items:
            result = self._yahoo_rss_news(symbol, max_items=max_items - len(articles))
            provider_results.append(result)
            articles.extend(result.get('articles', []))

        # add a primitive sentiment score for RSS/news items without provider scores
        for article in articles:
            if article.get('sentiment_score') is None:
                article['sentiment_score'] = self._headline_sentiment(article)

        sentiment_score = self._aggregate_sentiment(articles)
        sentiment_label = self._sentiment_label(sentiment_score)
        risk_flags = self._risk_flags(articles)

        return {
            'symbol': symbol,
            'online': bool(articles),
            'provider_status': self.provider_status(),
            'providers': provider_results,
            'headline_count': len(articles),
            'sentiment_score': sentiment_score,
            'sentiment_label': sentiment_label,
            'risk_flags': risk_flags,
            'articles': articles[:max_items],
            'summary': self._build_summary(symbol, sentiment_label, articles, risk_flags),
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'warning': None if articles else 'Keine Online-News/Sentiment-Daten geladen. API-Key pruefen oder spaeter erneut versuchen.',
        }

    def _effective_provider(self) -> str:
        preferred = (settings.internet_analysis_provider or 'auto').lower()
        if preferred != 'auto':
            return preferred
        if settings.finnhub_api_key:
            return 'finnhub'
        if settings.alpha_vantage_api_key:
            return 'alpha_vantage'
        return 'yahoo_rss_free'

    def _finnhub_news(self, symbol: str, max_items: int) -> dict[str, Any]:
        try:
            response = requests.get(
                f'{self.FINNHUB_URL}/company-news',
                params={
                    'symbol': self._stock_symbol(symbol),
                    'from': datetime.now(timezone.utc).date().replace(day=1).isoformat(),
                    'to': datetime.now(timezone.utc).date().isoformat(),
                    'token': settings.finnhub_api_key,
                },
                timeout=12,
            )
            response.raise_for_status()
            data = response.json()
            articles = []
            for item in data[:max_items]:
                articles.append({
                    'source': item.get('source'),
                    'headline': item.get('headline'),
                    'summary': item.get('summary'),
                    'url': item.get('url'),
                    'datetime': item.get('datetime'),
                    'provider': 'finnhub',
                    'sentiment_score': None,
                })
            return {'provider': 'finnhub', 'status': 'online', 'articles': articles}
        except Exception as exc:
            return {'provider': 'finnhub', 'status': 'error', 'error': str(exc), 'articles': []}

    def _alpha_news_sentiment(self, symbol: str, query: str | None, max_items: int) -> dict[str, Any]:
        try:
            response = requests.get(
                self.ALPHA_URL,
                params={
                    'function': 'NEWS_SENTIMENT',
                    'tickers': self._stock_symbol(symbol),
                    'topics': query or '',
                    'apikey': settings.alpha_vantage_api_key,
                    'limit': max_items,
                },
                timeout=12,
            )
            response.raise_for_status()
            data = response.json()
            feed = data.get('feed') or []
            articles = []
            for item in feed[:max_items]:
                score = self._safe_float(item.get('overall_sentiment_score'))
                articles.append({
                    'source': item.get('source'),
                    'headline': item.get('title'),
                    'summary': item.get('summary'),
                    'url': item.get('url'),
                    'datetime': item.get('time_published'),
                    'provider': 'alpha_vantage',
                    'sentiment_score': score,
                    'sentiment_label': item.get('overall_sentiment_label'),
                })
            return {'provider': 'alpha_vantage', 'status': 'online', 'articles': articles}
        except Exception as exc:
            return {'provider': 'alpha_vantage', 'status': 'error', 'error': str(exc), 'articles': []}

    def _yahoo_rss_news(self, symbol: str, max_items: int) -> dict[str, Any]:
        yahoo_symbol = self._yahoo_symbol(symbol)
        try:
            url = f'{self.YAHOO_RSS_URL}?s={quote_plus(yahoo_symbol)}&region=US&lang=en-US'
            response = requests.get(url, timeout=12, headers={'User-Agent': 'Mozilla/5.0 TradingCockpit/1.5'})
            response.raise_for_status()
            root = ET.fromstring(response.text)
            items = root.findall('./channel/item')
            articles: list[dict[str, Any]] = []
            for item in items[:max_items]:
                title = (item.findtext('title') or '').strip()
                link = (item.findtext('link') or '').strip()
                description = (item.findtext('description') or '').strip()
                pub_date = (item.findtext('pubDate') or '').strip()
                if not title:
                    continue
                articles.append({
                    'source': 'Yahoo Finance RSS',
                    'headline': title,
                    'summary': description,
                    'url': link,
                    'datetime': pub_date,
                    'provider': 'yahoo_rss_free',
                    'sentiment_score': None,
                })
            return {'provider': 'yahoo_rss_free', 'status': 'online' if articles else 'empty', 'articles': articles}
        except Exception as exc:
            return {'provider': 'yahoo_rss_free', 'status': 'error', 'error': str(exc), 'articles': []}

    def _aggregate_sentiment(self, articles: list[dict[str, Any]]) -> float:
        scores = [float(a['sentiment_score']) for a in articles if a.get('sentiment_score') is not None]
        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 4)

    def _sentiment_label(self, score: float) -> str:
        if score >= 0.25:
            return 'positiv'
        if score <= -0.25:
            return 'negativ'
        return 'neutral/unbekannt'

    def _risk_flags(self, articles: list[dict[str, Any]]) -> list[str]:
        keywords = {
            'earnings': 'Earnings/Quartalszahlen im Nachrichtenkontext',
            'lawsuit': 'Rechts-/Klage-Risiko im Nachrichtenkontext',
            'investigation': 'Untersuchungs-/Regulierungsrisiko im Nachrichtenkontext',
            'sec': 'SEC-/Regulierungsbezug im Nachrichtenkontext',
            'downgrade': 'Analysten-Downgrade im Nachrichtenkontext',
            'bankruptcy': 'Insolvenz-/Finanzierungsrisiko im Nachrichtenkontext',
            'hack': 'Cyber-/Hack-Risiko im Nachrichtenkontext',
            'ban': 'Regulierungs-/Verbotsrisiko im Nachrichtenkontext',
        }
        text = ' '.join([str(a.get('headline') or '') + ' ' + str(a.get('summary') or '') for a in articles]).lower()
        return [label for keyword, label in keywords.items() if keyword in text]

    def _headline_sentiment(self, article: dict[str, Any]) -> float:
        text = f"{article.get('headline') or ''} {article.get('summary') or ''}".lower()
        positive = ['beats', 'beat', 'surge', 'rally', 'gain', 'upgrade', 'record', 'growth', 'profit', 'bull', 'strong']
        negative = ['miss', 'falls', 'drop', 'lawsuit', 'downgrade', 'loss', 'weak', 'bear', 'risk', 'probe', 'ban']
        score = 0.0
        score += sum(0.12 for word in positive if word in text)
        score -= sum(0.12 for word in negative if word in text)
        return max(-0.8, min(0.8, round(score, 4)))

    def _build_summary(self, symbol: str, sentiment_label: str, articles: list[dict[str, Any]], risk_flags: list[str]) -> str:
        if not articles:
            return f'Keine Online-Analyse fuer {symbol} verfuegbar. Entscheidung basiert nur auf Kursdaten, Indikatoren und Risiko-Regeln.'
        flag_text = ' Risiko-Hinweise: ' + '; '.join(risk_flags) if risk_flags else ''
        return f'Online-Kontext fuer {symbol}: {len(articles)} News/Sentiment-Treffer, aggregiertes Sentiment: {sentiment_label}.{flag_text}'

    def _safe_float(self, value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except Exception:
            return None

    def _stock_symbol(self, symbol: str) -> str:
        return symbol.replace('/USD', '').replace('-USD', '') if symbol.upper() in {'BTC/USD', 'ETH/USD', 'BTC-USD', 'ETH-USD'} else symbol.split('/')[0]

    def _yahoo_symbol(self, symbol: str) -> str:
        s = symbol.strip().upper()
        mapping = {'BTC/USD': 'BTC-USD', 'ETH/USD': 'ETH-USD', 'EUR/USD': 'EURUSD=X', 'XAU/USD': 'GC=F'}
        return mapping.get(s, s.replace('/', '-'))


internet_analysis_service = InternetAnalysisService()
