# Backtesting v0.5

Das Backtesting-Modul prueft die gleiche KI-/Regel-Logik, die auch der Paper-Bot verwendet.

## Ablauf

1. Kerzendaten laden
2. Indikatoren auf einem rollierenden Lookback berechnen
3. KI-Prognose erzeugen
4. Strategie-Signal erzeugen
5. Risiko-/Qualitaetsfilter pruefen
6. Trade mit Stop-Loss und Take-Profit simulieren
7. Equity-Kurve und Kennzahlen berechnen

## Konservative Annahmen

- Entry erfolgt zum Close der Signalkerze.
- Stop-Loss und Take-Profit werden candle-basiert geprueft.
- Wenn Stop und Ziel in derselben Kerze beruehrt werden, wird konservativ Stop-Loss zuerst angenommen.
- Slippage, Spread und Gebuehren sind in v0.5 noch nicht modelliert.
- Es wird nur eine Position gleichzeitig simuliert; nach Exit wird das naechste Signal gesucht.

## Kennzahlen

- total_trades
- win_rate_percent
- gross_profit
- gross_loss
- profit_factor
- average_win
- average_loss
- expectancy_per_trade
- total_pnl
- return_percent
- max_drawdown_amount
- max_drawdown_percent

## API

```text
POST /api/backtest/run
POST /api/backtest/compare
GET  /api/backtest/runs
```

## Interpretation

Backtesting ist ein Qualitaetsfilter, keine Prognosegarantie. Ein Setup sollte erst in den Paper-Bot und spaeter in Semi-Auto gehen, wenn es ueber genug Daten eine akzeptable Trefferquote, einen positiven Profit Factor und einen kontrollierten Drawdown zeigt.
