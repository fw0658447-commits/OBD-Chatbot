# Trading Cockpit MVP v0.6 - Strategie-Katalog

v0.6 ersetzt die fest verdrahtete Backtest-Strategie durch einen kleinen Strategie-Katalog. Die KI-Prognose bleibt ein Filter; konkrete Entry-/Stop-/Target-Werte entstehen in der Strategy Engine.

## Strategien

| Name | Familie | Zweck |
|---|---|---|
| `trend_atr_v0.6` | Trendfolge | Handelt bestehende Trends mit ATR-basiertem Stop und Ziel. |
| `pullback_ema_v0.6` | Pullback | Sucht Ruecksetzer nahe EMA21 innerhalb eines groesseren Trends. |
| `breakout_range_v0.6` | Breakout | Sucht Ausbrueche ueber/unter die 20-Kerzen-Range mit Volumenbestaetigung. |
| `mean_reversion_rsi_v0.6` | Mean Reversion | Antizyklischer Rebound-Ansatz bei ueberverkauftem oder ueberkauftem RSI. |

## Neue API-Endpunkte

```text
GET  /api/backtest/strategies
POST /api/backtest/run
POST /api/backtest/compare
POST /api/backtest/walk-forward
```

`POST /api/backtest/run` akzeptiert jetzt `strategy_name`.

```json
{
  "symbol": "BTC/USD",
  "timeframe": "1h",
  "strategy_name": "pullback_ema_v0.6",
  "limit": 420,
  "initial_capital": 10000,
  "risk_per_trade": 0.01,
  "persist": true
}
```

`POST /api/backtest/compare` kann mehrere Strategien, Assets und Timeframes parallel vergleichen.

```json
{
  "symbols": ["BTC/USD", "ETH/USD", "AAPL", "SPY"],
  "timeframes": ["1h", "4h"],
  "strategies": ["trend_atr_v0.6", "pullback_ema_v0.6", "breakout_range_v0.6", "mean_reversion_rsi_v0.6"],
  "limit": 420,
  "initial_capital": 10000
}
```

## Walk-forward-Test

Der Walk-forward-Test teilt den Testbereich in mehrere aufeinanderfolgende Fenster. Die Strategie wird nicht optimiert; v0.6 nutzt den Test als Stabilitaetspruefung gegen Overfitting-Anzeichen.

```json
{
  "symbol": "BTC/USD",
  "timeframe": "1h",
  "strategy_name": "trend_atr_v0.6",
  "limit": 720,
  "initial_capital": 10000,
  "splits": 3
}
```

## Sicherheit

Live-Trading bleibt deaktiviert. Alle Strategien laufen nur fuer Analyse, Backtest und Paper-Trading.
