# Trading Cockpit MVP v0.7 - Parameter-Optimierung und ML-Dataset

v0.7 erweitert das Backtesting um zwei Bausteine:

1. **Parameter-Optimierung** fuer regelbasierte Strategien
2. **ML-Trainingsdatensatz** aus Kerzen, Indikatoren, KI-Prognosen, Signalen und spaeterer Kursbewegung

Live-Trading bleibt deaktiviert. Die Optimierung dient nur dazu, robuste Kandidaten fuer Paper-Trading und weitere Tests zu finden.

## Neue Strategienamen

Die v0.6-Strategien bleiben als Alias nutzbar, intern werden sie auf v0.7 gemappt:

| Strategie | Zweck |
|---|---|
| `trend_atr_v0.7` | Trendfolge mit optimierbarem ATR-Stop und ATR-Ziel |
| `pullback_ema_v0.7` | Ruecksetzer nahe EMA21 mit optimierbarer EMA-Distanz und RSI-Zone |
| `breakout_range_v0.7` | Ausbruch aus der 20-Kerzen-Range mit optionalem Volumenfilter |
| `mean_reversion_rsi_v0.7` | RSI-Reversion mit optimierbaren Ueberkauft-/Ueberverkauft-Schwellen |

## Neue API-Endpunkte

```text
GET  /api/backtest/parameter-grid/{strategy_name}
POST /api/backtest/optimize
POST /api/backtest/ml-dataset
GET  /api/backtest/optimization-runs
GET  /api/backtest/ml-dataset-exports
```

## Beispiel: Parameter-Optimierung

```bash
curl -X POST http://localhost:8000/api/backtest/optimize \
  -H 'Content-Type: application/json' \
  -d '{
    "symbol":"BTC/USD",
    "timeframe":"1h",
    "strategy_name":"trend_atr_v0.7",
    "limit":420,
    "initial_capital":10000,
    "risk_per_trade":0.01,
    "objective":"robust_score",
    "max_combinations":48,
    "persist":true
  }'
```

Der `robust_score` belohnt Return und Profit Factor, bestraft aber Drawdown und zu wenige Trades. Damit wird nicht automatisch die hoechste Rendite gewaehlt, sondern eine konservativere Kandidatenbewertung.

## Beispiel: ML-Dataset

```bash
curl -X POST http://localhost:8000/api/backtest/ml-dataset \
  -H 'Content-Type: application/json' \
  -d '{
    "symbols":["BTC/USD","ETH/USD","AAPL","SPY"],
    "timeframes":["1h"],
    "strategies":["trend_atr_v0.7","pullback_ema_v0.7"],
    "limit":500,
    "lookahead_bars":12,
    "max_rows":1500,
    "include_csv":true,
    "persist":true
  }'
```

## Dataset-Logik

Features enthalten u.a.:

- RSI
- ATR Prozent
- Trendstaerke
- SMA/Trendboolesche Werte
- Volumenbestaetigung
- KI-Wahrscheinlichkeiten
- Confidence Score
- Risk Score
- CRV und Signal Score

Targets:

- `future_return_percent`
- `target_label`: `1` = steigend, `0` = neutral, `-1` = fallend

## Wichtig

Parameter-Optimierung kann Overfitting erzeugen. Ein guter Kandidat muss danach immer noch durch Walk-forward-Test, Out-of-sample-Test und Paper-Bot-Phase laufen.
