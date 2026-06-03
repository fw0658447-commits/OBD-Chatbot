# v1.2 Validation & Monitoring

Diese Version macht das Trading Cockpit belastbarer fuer ernsthaftes Paper-Trading. Ziel ist nicht Echtgeldhandel, sondern eine kontrollierte Paper-Trading-Umgebung mit klaren Freigabe-Gates.

## Neue Kernfunktionen

- Release-Gates fuer Paper-Automation
- Mindesthistorie fuer geschlossene Trades
- Profit-Factor-, Winrate-, Drawdown- und Expectancy-Grenzen
- Datenqualitaets-Gate im Monitoring
- Daily Report fuer die letzten 24 Stunden
- Alerts fuer kritische Betriebszustaende
- Strategie-/Modus-Matrix
- optionales `enforce_validation_gate`, das Bot-Cycles blockiert, solange die Strategie nicht freigegeben ist

## Neue API-Endpunkte

```bash
GET /api/monitoring/validation-gates
GET /api/monitoring/daily-report?lookback_hours=24
GET /api/monitoring/alerts
GET /api/monitoring/strategy-matrix
GET /api/monitoring/system-report
GET /api/bot/validation-gates
```

## Wichtige Konfigurationswerte

```json
{
  "enforce_validation_gate": false,
  "min_closed_trades_for_release": 100,
  "min_profit_factor_for_release": 1.15,
  "min_win_rate_for_release": 45,
  "max_drawdown_percent_for_release": 12,
  "min_expectancy_per_trade_for_release": 0,
  "min_data_quality_score_for_release": 70
}
```

`enforce_validation_gate` ist standardmaessig `false`, damit das System weiter Paper-Trades sammeln kann. Wird es auf `true` gesetzt, blockiert der Bot neue Paper-Orders, solange die Release-Gates nicht bestanden sind.

## Freigabelogik

Eine Strategie gilt als fuer kontrollierte Paper-Automation freigegeben, wenn alle Blocking-Gates bestanden sind:

- ausreichend geschlossene Paper-Trades
- Profit Factor nach Kostenmodell ueber Mindestwert
- Drawdown unter Maximalwert
- letzter Datenqualitaetsreport trade-allowed
- keine kritischen Alerts

Warn-Gates wie Winrate oder Expectancy werden separat angezeigt. Sie blockieren nicht zwingend, sind aber fuer die Interpretation wichtig.

## Realistische Nutzungsregel

Vor jeder ernsthaften Nutzung sollten mindestens 100 geschlossene Paper-Trades ueber mehrere Marktphasen vorliegen. Die Ergebnisse muessen nach Spread, Slippage und Kommission positiv bleiben.

Live-Trading ist weiterhin hart gesperrt.
