# Trading Cockpit v1.3 - Usability, Paper-Konto und Marktstatus

Diese Version schliesst mehrere praktische Luecken fuer den realistischen Paper-Trading-Betrieb.

## Neue Funktionen

### Paper-Konto

Neue Endpunkte:

```bash
POST /api/portfolio/paper/deposit
POST /api/portfolio/paper/withdraw
POST /api/portfolio/paper/reset
GET  /api/portfolio/paper/cash-ledger
POST /api/portfolio/paper/manual-order
```

Beispiel Einzahlung:

```bash
curl -X POST http://localhost:8000/api/portfolio/paper/deposit \
  -H 'Content-Type: application/json' \
  -d '{"amount": 10000, "note": "Startkapital"}'
```

Beispiel manueller Paper-Trade:

```bash
curl -X POST http://localhost:8000/api/portfolio/paper/manual-order \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"BTC/USD","side":"long","notional_amount":1000}'
```

Wenn Stop-Loss und Take-Profit leer bleiben, setzt das System Standardwerte:

- Long: Stop ca. -2 %, Take-Profit ca. +4 %
- Short: Stop ca. +2 %, Take-Profit ca. -4 %

### Watchlist

Die Watchlist kann jetzt nicht nur Symbole speichern, sondern auch:

- Notiz
- Alarmkurs
- Zielkurs
- Live-/Mock-Quote

Der gleiche Eintrag wird per Upsert aktualisiert, statt mehrfach dupliziert zu werden.

### Online-/Offline-Status

Neuer Endpunkt:

```bash
GET /api/ops/status
```

Der Endpunkt zeigt:

- Backend-Status
- PostgreSQL-Status
- Cache-Status
- Marktdatenanbieter
- Mock-/Live-Datenstatus
- Fallback-Nutzung
- Live-Trading-Lock

### Dashboard

Das Dashboard zeigt jetzt zentral:

- Equity
- Cash
- realisierte/unrealisierte P/L
- Online-/Datenstatus
- Watchlist-Anzahl
- offene Trades
- gebundenes Kapital
- Risk Events

## Echte Marktdaten aktivieren

In `.env`:

```env
MARKET_DATA_PROVIDER=twelve_data
MARKET_DATA_API_KEY=dein_api_key
MARKET_PROVIDER_FALLBACK_ENABLED=true
```

Danach neu starten:

```bash
bash scripts/codespaces_stop.sh
bash scripts/codespaces_start.sh
```

Pruefen:

```bash
curl http://localhost:8000/api/ops/status
curl 'http://localhost:8000/api/data/quality?symbol=BTC/USD&timeframe=1h&limit=220&persist=true'
```

## Hinweis

Auch v1.3 bleibt Paper-Trading-only. Echtgeldhandel ist weiterhin hart gesperrt.
