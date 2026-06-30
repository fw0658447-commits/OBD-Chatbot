# MVP v0.9 - ML-/Ensemble-Bot-Entscheidung

v0.9 verbindet das bisherige Regelmodell mit dem ML-Baseline-Modell aus v0.8. Der Bot bleibt weiterhin strikt im Paper-Trading-Modus. Live-Trading ist nicht aktiviert.

## Entscheidungsmodi

| Modus | Verhalten |
|---|---|
| `rule` | Das bisherige Regel-/Strategiemodell erzeugt ein Signal. Die Risk Engine entscheidet danach wie bisher. |
| `ml` | Ein trainiertes ML-Modell muss die Richtung des Strategiesignals bestätigen. Ohne ML-Bestätigung wird das Signal blockiert. |
| `ensemble` | Regelmodell und ML-Modell müssen übereinstimmen. Falls das ML-Modell nicht verfügbar oder degradiert ist, kann optional auf Rule-only zurückgefallen werden. |

## Degradationserkennung

Der Bot prüft die Modellmetadaten aus dem letzten Training. Ein Modell gilt als degradiert, wenn zum Beispiel:

- zu wenige Validierungstrades vorhanden sind,
- der Profit Factor unter dem Grenzwert liegt,
- die ML-Winrate unter dem Grenzwert liegt.

Standardwerte:

```text
min_model_profit_factor = 1.0
min_model_win_rate = 45.0
min_ml_probability = 0.52
```

## API-Beispiele

Rule-only:

```bash
curl -X POST http://localhost:8000/api/bot/run-cycle \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"BTC/USD","timeframe":"1h","strategy_name":"trend_atr_v0.7","decision_mode":"rule"}'
```

Ensemble:

```bash
curl -X POST http://localhost:8000/api/bot/run-cycle \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"BTC/USD","timeframe":"1h","strategy_name":"trend_atr_v0.7","decision_mode":"ensemble","min_ml_probability":0.52,"allow_degraded_fallback":true}'
```

ML-Modellzustand:

```bash
curl http://localhost:8000/api/bot/model-health
```

Performance nach Entscheidungsmodus:

```bash
curl http://localhost:8000/api/bot/performance-by-mode
```

## Wichtig

Auch im Ensemble-Modus darf das ML-Modell keine Order direkt auslösen. Der Ablauf bleibt:

1. Strategie erzeugt Signal.
2. Bot-Decision-Layer prüft Rule/ML/Ensemble.
3. Risk Engine prüft Risiko, CRV, offene Trades und Tagesverlust.
4. Paper Trading Engine erzeugt nur virtuelle Orders.
