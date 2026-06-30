# Trading Cockpit v1.1 - Real-Market-Readiness

v1.1 macht die Paper-Trading-Version deutlich realistischer. Ziel ist nicht Echtgeldhandel, sondern ein belastbares, auditiertes Paper-System, das echte Marktdaten, Datenqualitaet und Ausfuehrungskosten beruecksichtigt.

## Neue Gates vor jedem Bot-Trade

1. Marktdaten laden
2. Datenqualitaet pruefen
3. Kerzen optional in PostgreSQL speichern
4. Datenqualitaetsreport speichern
5. Nur wenn `trade_allowed = true`: Indikatoren, Prognose, Strategie und Risk Engine ausfuehren

Der Bot wird blockiert, wenn:

- zu wenige Kerzen vorhanden sind
- OHLC-Daten ungueltig sind
- grosse Datenluecken erkannt werden
- der Quality Score unter dem Grenzwert liegt
- `BLOCK_TRADES_ON_DATA_QUALITY_FAIL=true` gesetzt ist

## Paper-Ausfuehrungsmodell

Paper-Fills sind nicht mehr idealisiert. Das Modell beruecksichtigt:

- Spread in Basispunkten
- Slippage in Basispunkten
- Kommission in Basispunkten
- Mindestkommission

Long Entry wird zum simulierten Ask ausgefuehrt, Long Exit zum simulierten Bid. Short-Logik ist gespiegelt. P/L ist netto nach Kosten.

## Neue Endpunkte

```text
GET  /api/ops/readiness
GET  /api/data/cache/status
GET  /api/data/quality?symbol=BTC/USD&timeframe=1h&persist=true
POST /api/data/persist-candles?symbol=BTC/USD&timeframe=1h&limit=500
GET  /api/data/stored-candles?symbol=BTC/USD&timeframe=1h
GET  /api/data/quality/reports
GET  /api/export/datasets
GET  /api/export/csv/orders
GET  /api/export/csv/signals
GET  /api/export/csv/predictions
GET  /api/export/csv/decision_audits
GET  /api/export/csv/backtests
GET  /api/export/csv/data_quality
```

## Readiness-Check

`GET /api/ops/readiness` gibt zurueck, ob das System fuer realistisches Paper-Trading bereit ist. Der Check ist absichtlich streng. Er verlangt unter anderem:

- erreichbare PostgreSQL-Persistenz
- aktiven Live-Trading-Hard-Lock
- aktiviertes Kostenmodell
- keine blockierenden Datenqualitaetsbefunde

## Echte Marktdaten

Fuer Mock-Daten:

```env
MARKET_DATA_PROVIDER=mock
```

Fuer Twelve Data:

```env
MARKET_DATA_PROVIDER=twelve_data
MARKET_DATA_API_KEY=<dein-api-key>
MARKET_PROVIDER_FALLBACK_ENABLED=true
```

Fallback bedeutet: Wenn Twelve Data nicht erreichbar ist, laeuft das System mit Mock-Daten weiter. Fuer echte Entscheidungsqualitaet sollte man Fallback-Ereignisse beobachten und nicht als echte Daten interpretieren.

## Realistische Anwendung

Diese Version ist sinnvoll fuer:

- Paper-Trading mit Watchlist-Symbolen
- Vergleich von Strategien und Decision Modes
- Datensatzaufbau fuer ML-Verbesserung
- Audit von Bot-Entscheidungen
- Export und externe Analyse in Python/R/BI-Tools

Diese Version ist noch nicht fuer Echtgeldhandel gedacht.
