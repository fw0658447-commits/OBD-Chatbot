# Risk Rules MVP v0.3

Live-Trading ist deaktiviert. Der Bot darf nur Paper-Trades erzeugen.

## Harte Regeln

- Jeder Trade braucht einen Stop-Loss.
- Jeder Trade braucht ein Take-Profit-Ziel.
- Mindest-CRV: 2.0.
- Maximalrisiko pro Trade: 1 Prozent des Musterdepots.
- Maximaler Tagesverlust: 2 Prozent.
- Maximal offene Bot-Trades: 3.
- Mindest-Confidence: 65/100.
- Maximaler Risk Score: 70/100.
- Kill-Switch blockiert neue Trades.

## Entscheidungsprinzip

KI prognostiziert. Strategie erzeugt Signale. Risiko-Engine blockiert. Bot handelt nur Paper.
