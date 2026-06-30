# Trading Cockpit MVP v1.5 Full-Fix Update

## Ziele

v1.5 behebt die typischen iPadOS/GitHub-Codespaces-Probleme:

- Frontend ruft nicht mehr `localhost:8000` im iPad-Browser auf.
- Frontend nutzt standardmaessig einen Next.js Same-Origin-Proxy: `/api/backend`.
- Paper-Konto-Endpunkte bleiben ueber den Proxy erreichbar.
- Default-Marktdatenprovider ist jetzt `free` statt `mock`.
- Free-Online-Marktdaten laufen ueber einen Yahoo-Finance-kompatiblen Fallback.
- Internetanalyse nutzt Finnhub/Alpha Vantage, falls konfiguriert, sonst Yahoo Finance RSS als freien News-Fallback.
- ISIN/WKN-Lookup hat einen lokalen Common-Identifier-Fallback fuer haeufige Beispiele wie Apple ISIN/WKN.
- Full-System-Check im Frontend und API: `/api/ops/full-diagnostics`.

## Update-Befehl in Codespaces

Im Projektordner:

```bash
cd /workspaces/Trading-Bot
bash scripts/codespaces_full_fix.sh
```

Danach Ports oeffnen:

- 3000: Frontend
- 8000: API, mit `/docs` fuer Swagger

## Wichtige Defaults

```env
MARKET_DATA_PROVIDER=free
NEXT_PUBLIC_API_BASE_URL=auto
MARKET_PROVIDER_FALLBACK_ENABLED=true
```

Wenn du professionelle Datenquellen nutzen willst:

```env
MARKET_DATA_PROVIDER=twelve_data
MARKET_DATA_API_KEY=dein_key
OPENFIGI_API_KEY=dein_key
FINNHUB_API_KEY=dein_key
ALPHA_VANTAGE_API_KEY=dein_key
```

## Tests

```bash
bash scripts/codespaces_smoke_test.sh
curl http://localhost:8000/api/ops/status
curl 'http://localhost:8000/api/ops/full-diagnostics?symbol=BTC/USD&timeframe=1h&strategy_name=trend_atr_v0.7'
```

## Hinweis

Live-Trading bleibt gesperrt. Diese Version ist fuer Analyse, Research, Paper-Trading, Watchlist und Bot-Simulation gedacht.
