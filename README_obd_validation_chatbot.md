# OBD Dokumentenvalidierungs-Chatbot

Diese Streamlit-App prueft OBD-Dokumente gegen einen ersten Regelkatalog fuer DTC-Matrix, Testfallmatrix und Diagnose-Spezifikation.

## Start lokal oder in GitHub Codespaces

```bash
pip install -r requirements_obd_chatbot.txt
streamlit run obd_validation_chatbot_app.py
```

Danach die im Repository enthaltenen Beispieldateien hochladen:

- `sample_dtc_matrix.csv`
- `sample_testcase_matrix.csv`
- `sample_diagnosis_spec.txt`

## Zweck

Die App erzeugt:

- Gesamtstatus
- High-/Medium-/Low-Finding-Zaehler
- Finding-Tabelle
- Excel-Export
- Chatantworten zu Findings, DTCs, Regeln, Evidence und naechsten Massnahmen

## Beispiel-Fragen im Chat

- Welche High Findings gibt es?
- Wie ist der Gesamtstatus?
- Erklaere R011.
- Zeige mir alles zu DTC P0ABC.
- Welche Evidence fehlt?
- Was sind die naechsten Massnahmen?

## Fachliche Leitplanke

Die App liefert keine finale regulatorische oder homologationsseitige Compliance-Freigabe. Sie bewertet nur die hochgeladenen Dokumente auf Basis der implementierten Regeln.

Zielaussage:

- Freigabefaehig auf Basis der geprueften Dokumente und Regeln.
- Nicht freigabefaehig auf Basis offener High-Findings.

## Aktueller Regelumfang

- R001: DTC-Code muss eindeutig sein
- R002: DTC-Beschreibung darf nicht leer sein
- R003: Monitor-ID darf nicht leer sein
- R004: Storage Logic darf nicht leer sein
- R005: Jeder DTC braucht mindestens einen Testfall
- R006: Jeder Testfall braucht ein Expected Result
- R007: Jeder Testfall braucht einen Teststatus
- R008: Status closed nur mit Evidence-Link erlaubt
- R009: DTC aus Matrix muss in Diagnose-Spezifikation vorkommen
- R010: Monitor-ID aus Matrix muss in Diagnose-Spezifikation vorkommen
- R011: Enable Conditions muessen am Monitor beschrieben sein
- R012: Inhibit Conditions sollten am Monitor beschrieben sein
- R013: Detection Logic muss am Monitor beschrieben sein
- R014: Healing/Reset/Aging Logic sollte beschrieben sein
- R015: Unklare Formulierungen muessen reviewed werden
- R016: Diagnose-Spezifikation ist leer oder nicht lesbar
- R017: Testfall verweist nicht eindeutig auf den DTC im Testtext
- R018: DTC-Beschreibung und Testfall/Monitor wirken semantisch schwach verbunden

## Naechste Ausbaustufe

- Regelkatalog aus CSV laden
- flexible manuelle Spaltenzuordnung in der UI
- Export mit separaten Sheets fuer Summary, Findings, DTCs, Testfaelle und Regelkatalog
- optionaler LLM-Review mit Quellenbezug
