# Trading Cockpit MVP v0.8 - Baseline-ML-Modelle

Version 0.8 fuehrt die erste echte ML-Trainingspipeline ein. Sie ersetzt den regelbasierten Bot nicht, sondern bewertet ihn gegen ein reproduzierbares Baseline-Modell.

## Ziele

- ML-Datensatz aus v0.7 automatisch erzeugen
- Baseline-Modell trainieren: Random Forest oder Logistic Regression
- chronologischer Train/Test-Split statt zufaellig gemischter Stichprobe
- Vergleich Regelmodell vs. ML-Prognose
- Modellversionen speichern
- aktuelle Asset-Prognose mit trainiertem Modell erzeugen

## Neue Endpunkte

- `POST /api/ml/train`
- `POST /api/ml/predict`
- `POST /api/ml/predict-asset`
- `POST /api/ml/compare-rule-vs-ml`
- `GET /api/ml/models`
- `GET /api/ml/prediction-runs`

## Modelllogik

Das Modell nutzt die aus v0.7 bekannten Features:

- RSI
- ATR in Prozent
- Trendstaerke
- SMA20/SMA50-Signale
- Volumenbestaetigung
- Regelmodell-Wahrscheinlichkeiten
- Confidence Score
- Risk Score
- CRV
- Signal Score

Zielvariable:

- `1` = zukuenftige Bewegung nach `lookahead_bars` positiv
- `0` = neutral
- `-1` = negativ

## Sicherheitsgrenze

Das ML-Modell darf in v0.8 keine echten Orders ausloesen. Es dient nur als Prognose- und Vergleichsschicht. Paper-Bot und Risk Engine bleiben die Kontrollinstanzen.
