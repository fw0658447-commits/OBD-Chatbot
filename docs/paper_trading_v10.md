# Trading Cockpit v1.0 Paper-Trading Ops

v1.0 macht aus dem bisherigen Ensemble-Bot eine kontrollierbare Paper-Trading-Version.

## Kernfunktionen

- Zentrale Bot-Konfiguration in `bot_runtime_config`
- Paper-only Scheduler fuer Symbol-/Watchlist-Laeufe
- Decision-Audit-Logging fuer jede Bot-Entscheidung
- Risk-Limits als Laufzeitkonfiguration statt nur statische `.env`-Werte
- Kill-Switch mit persistentem Zustand
- Equity-Kurve aus geschlossenen Paper-Orders

## Sicherheitsprinzipien

- `live_trading_enabled` bleibt immer `false`.
- Der Scheduler ruft nur den Paper-Bot auf.
- Kill-Switch blockiert neue Bot-Cycles.
- Die Risk Engine bleibt nachgelagert aktiv, auch wenn Rule/ML/Ensemble ein Signal erlaubt.
- Decision-Audits speichern auch blockierte Signale, damit spaeter nachvollziehbar bleibt, warum ein Trade nicht ausgefuehrt wurde.

## Wichtige Endpunkte

```text
GET   /api/bot/config
PATCH /api/bot/config
POST  /api/bot/enable
POST  /api/bot/disable
POST  /api/bot/kill-switch
POST  /api/bot/kill-switch/reset
GET   /api/bot/scheduler/status
POST  /api/bot/scheduler/start
POST  /api/bot/scheduler/stop
POST  /api/bot/scheduler/run-once
GET   /api/bot/scheduler/runs
GET   /api/bot/decision-audits
GET   /api/bot/equity-curve
```

## Naechster Schritt nach v1.0

Vor jeder echten Broker-Anbindung sollten Stabilitaet, Persistenz, Datenqualitaet und Paper-Performance ueber mehrere Marktphasen getestet werden. Eine spaetere Broker-Integration sollte weiterhin erst als Simulation/Sandbox starten.
