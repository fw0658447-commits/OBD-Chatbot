# Persistenzschicht v0.2

Diese Iteration verbindet die Paper-Bot-Pipeline mit PostgreSQL, wenn `DATABASE_URL` gesetzt und erreichbar ist.

## Persistierte Objekte

- `assets`: Asset-Stammdaten
- `ai_predictions`: KI-/Scoring-Prognosen je Bot-Lauf oder manueller Prognose
- `bot_signals`: erzeugte Signale, inklusive Status `blocked` oder `executed`
- `paper_orders`: ausgeführte virtuelle Bot-Trades
- `risk_events`: blockierte Signale, Kill-Switch und weitere Risikoereignisse
- `watchlist_items`: persistente Watchlist-Einträge
- `paper_portfolio`: aktueller Paper-Portfolio-Status

## Fallback ohne Datenbank

Wenn `DATABASE_URL` nicht gesetzt ist oder PostgreSQL nicht erreichbar ist, läuft das Backend weiter mit Mock-Marktdaten und In-Memory-Journal. Damit bleiben lokale Tests möglich.

## Wichtige Endpunkte

```text
GET  /health
GET  /api/bot/persistence
POST /api/bot/run-cycle
GET  /api/bot/predictions
GET  /api/bot/signals
GET  /api/bot/orders
GET  /api/bot/risk-events
POST /api/bot/evaluate-open-orders
GET  /api/portfolio/paper
GET  /api/watchlist
POST /api/watchlist
```

## Status

Live-Trading ist weiterhin gesperrt. Die Persistenz gilt ausschließlich für Paper-Trading und Prognosen.
