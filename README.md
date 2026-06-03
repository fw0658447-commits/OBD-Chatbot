# Trading Cockpit MVP v1.2.1 — iPadOS / Codespaces Ready

KI-gestütztes Trading-Cockpit mit Analyse, Watchlist, Paper-Trading-Bot, Risiko-Engine, Backtesting, Monitoring und Validierungs-Gates.

Diese Version ist für **iPadOS über GitHub Codespaces** vorbereitet. Das iPad dient als Browser-Oberfläche; Backend, Datenbank, Redis, Worker und Frontend laufen in Codespaces.

## Status

- Paper-Trading: aktiv nutzbar
- Live-Trading: bewusst hart gesperrt
- Marktdaten: Mock-Daten standardmäßig aktiv, Twelve Data optional
- Ziel: realistische Paper-Trading-Validierung, nicht Echtgeldhandel

## Enthalten

- FastAPI Backend
- Next.js Frontend
- PostgreSQL
- Redis
- Paper-Trading-Bot
- Risk Engine
- Datenqualitätsprüfung
- Spread-/Slippage-/Kommissionsmodell für Paper-Trades
- Backtesting
- Strategie-Katalog
- Parameter-Optimierung
- ML-Baseline-Modell
- Rule/ML/Ensemble-Bot-Modi
- Validation Gates
- Monitoring-Tab
- CSV-Exports
- iPadOS/Codespaces Devcontainer
- Codespaces Start-/Stop-/Status-Skripte

## Schnellstart auf iPadOS mit GitHub Codespaces

1. GitHub-Repository erstellen, idealerweise privat.
2. Projektdateien in das Repository hochladen.
3. `Code -> Codespaces -> Create codespace on main` öffnen.
4. Im Codespaces-Terminal starten:

```bash
bash scripts/codespaces_start.sh
```

5. In der Codespaces-Ansicht **Ports** öffnen:

```text
3000 -> Frontend
8000 -> API; /docs fuer Swagger
```

## Status prüfen

```bash
bash scripts/codespaces_status.sh
```

Smoke-Test:

```bash
bash scripts/codespaces_smoke_test.sh
```

## Lokal mit Docker starten

```bash
docker compose up --build
```

Frontend:

```text
http://localhost:3000
```

API:

```text
http://localhost:8000/docs
```

## Echte Marktdaten aktivieren

Standardmäßig läuft das Projekt mit Mock-Daten. Für Twelve Data in `.env` oder `docker-compose.yml` setzen:

```text
MARKET_DATA_PROVIDER=twelve_data
MARKET_DATA_API_KEY=DEIN_API_KEY
```

Danach neu starten:

```bash
bash scripts/codespaces_stop.sh
bash scripts/codespaces_start.sh
```

## Wichtige Endpunkte

```text
GET  /health
GET  /api/ops/readiness
GET  /api/monitoring/system-report
GET  /api/monitoring/validation-gates
GET  /api/bot/config
POST /api/bot/scheduler/run-once
POST /api/bot/run-cycle
GET  /api/bot/orders
GET  /api/bot/performance
GET  /api/bot/equity-curve
```

## iPadOS-Anleitung

Siehe:

```text
docs/ipados_codespaces_quickstart.md
```

## Sicherheit

Diese Version sendet keine echten Broker-Orders. Sie ist für Analyse, Backtesting, Paper-Trading, Monitoring und Strategievalidierung gedacht.
