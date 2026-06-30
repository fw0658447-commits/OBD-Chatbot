# v1.4 Intelligence & Recommendations

Diese Version erweitert das Trading Cockpit um eine Research- und Entscheidungsschicht.

## Neue Funktionen

- Instrumenten-Lookup nach Ticker, ISIN, WKN, FIGI oder Name
- OpenFIGI-Integration fuer Identifier-Mapping, wenn `OPENFIGI_API_KEY` gesetzt ist
- Fallback ueber vorhandene Marktdaten-Suche/Mock-Universum
- Online-News-/Sentiment-Kontext ueber Finnhub und/oder Alpha Vantage
- strukturierte Empfehlung je Asset:
  - LONG
  - SHORT
  - WATCH
  - NO_TRADE
- klare Entscheidung: Ja / Nein / Beobachten / Nur klein
- Risiko-Level: gering / mittel / hoch
- Checkliste: Datenqualitaet, Confidence, Risk Score, Strategie-Signal, CRV, Online-Kontext

## Neue Umgebungsvariablen

```env
OPENFIGI_API_KEY=
FINNHUB_API_KEY=
ALPHA_VANTAGE_API_KEY=
INTERNET_ANALYSIS_PROVIDER=auto
```

## Neue API-Endpunkte

```text
GET /api/intelligence/providers/status
GET /api/intelligence/instrument/lookup?query=US0378331005&query_type=auto
GET /api/intelligence/internet-analysis?symbol=AAPL&max_items=8
GET /api/intelligence/recommendation?symbol=AAPL&timeframe=1h&strategy_name=trend_atr_v0.7&include_internet=true
```

## Wichtige Hinweise

- Die Empfehlung ist keine Anlageberatung, sondern eine regelbasierte Entscheidungsunterstuetzung.
- Ohne API-Keys arbeitet die Schicht im Fallback-Modus und zeigt bewusst `nicht verbunden` an.
- Online-Kontext beeinflusst die Empfehlung nur als Zusatzfilter. Harte Blocker bleiben Datenqualitaet, Risk Score, Confidence und CRV.
- Live-Trading bleibt gesperrt.
