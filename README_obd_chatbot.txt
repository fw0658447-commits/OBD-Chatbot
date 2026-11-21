OBD System Review Assistant – Startanleitung

1. Python installieren (falls noch nicht vorhanden)
2. Im Terminal in den Ordner mit der Datei wechseln
3. Abhängigkeit installieren:
   pip install -r requirements_obd_chatbot.txt
4. App starten:
   streamlit run obd_chatbot_app.py
5. Im Browser die angezeigte lokale Adresse öffnen

Enthaltene Themen:
- OBD EU7
- Wirkkettenanalyse
- OBM
- OBF(C)M
- Anti-Tampering
- Felddatenanalyse
- HIL / virtuelle Validierung

Hinweis:
Diese erste Version ist bewusst einfach gehalten und nutzt feste Fachlogik.
Im nächsten Ausbau kann man ergänzen:
- Upload von PDF/Excel/DOCX
- Antwortlogik je Rolle (Management / Engineering / Zertifizierung)
- Maßnahmenlisten und Ampelstatus
- Aufwandsschätzung / PM-Kalkulation
- Suche in eigenen Dokumenten


OBD SYSTEMKOORDINATION - ERWEITERUNG 21.11.2026
================================================
Die Haupt-App obd_chatbot_app.py und die Dokumentenpruefung
obd_validation_chatbot_app.py verwenden jetzt beide die gemeinsame lokale
Wissens-/Retrieval-Logik obd_systemkoordination_core.py.

Abgedeckte Themen:
- Gesamtfahrzeug OBD/OBM/OBFCM fuer ICE, PHEV, BEV und lokale Marktvarianten
- UNECE WP29 GTR/UN R, EU7, USA EPA/CARB, China6/China7-Status
- Japan MLIT, Deutschland KBA/TUeV/GTUe, Brasilien IBAMA,
  Indien MoRTH, UK, Kanada, Australien und weitere RoW-Quellen
- Safety (GTR20/R100, ISO 26262), Cybersecurity R155/ISO 21434,
  SUMS/OTA R156/ISO 24089, Antitampering
- SOVD/Remote OBD, ePTI/HU, Datenzugang, Service, GSP und Kunde
- SOCE/SOCR, Batterie-Dauerhaltbarkeit, Funktions-/Datenwirkketten
- Feld/RTM, Anomalieerkennung, Zuverlaessigkeit und Reklamationsloop
- Arbeitsgruppen, Pilotprojekte, Konsultationen und Gesetzesentwuerfe
- Quellenstatus und Gesetzes-/Norm-/Engineering-Beziehungsgraph

Dateien:
- knowledge/agent_systemkoordination.md (als Profilvorlage)
- knowledge/obd_regulatory_memory_2026-11-21.md (Quellenstand)
- knowledge/e2e_authorities_service_field_chains.md (E2E und Zirkelschluesse)
- knowledge/source_catalog.json (offizielle und weitere Quellen)
- knowledge/regulatory_graph.json (Regelwerksbeziehungen mit Vertrauensstatus)
- knowledge/early_warning_initiatives.json (Fruehwarnung)
- scripts/monitor_regulatory_sources.py (Quellen-Metadatenmonitor)
- scripts/discover_cross_references.py (Kandidaten, nicht verifiziert)
- scripts/validate_regulatory_graph.py (Referenzintegritaet)
- scripts/check_early_warning.py (Vorhaben und Quellenverweise)

Manueller Test (im Repository):
  python -m compileall -q obd_systemkoordination_core.py obd_chatbot_app.py obd_validation_chatbot_app.py regulatory_knowledge.py scripts tests
  python -m unittest discover -s tests -p 'test_*.py' -v
  python scripts/validate_regulatory_graph.py
  python scripts/check_early_warning.py

GitHub Actions:
- .github/workflows/agent-quality.yml (bei Push und manuell, Syntax/Test)
- .github/workflows/regulatory-monitor.yml (Freitag 05:15 UTC oder manuell)

WICHTIG:
- Datenabruf/Statuspruefung ist KEINE automatische rechtliche Bewertung.
- Neu erfasste technische Zusammenhaenge muessen fachlich verifiziert werden.
- Nicht alle ISO/SAE-/Industrie-Volltexte duerfen automatisiert heruntergeladen werden.
- Kein Rechts-/Homologations-Sign-off und kein Zugriff auf OEM-Geheimdaten.
- Ein externer ChatGPT-Custom-GPT namens 'OBD Systemkoordination' ist durch
  GitHub-Aenderungen NICHT automatisch geaendert. Fuer dessen Aktualisierung
  die Vorlage knowledge/agent_systemkoordination.md und Quellen bereitstellen.
