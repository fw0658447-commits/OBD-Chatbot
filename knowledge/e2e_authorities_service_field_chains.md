# End-to-End Compliance: Behörden, Inspektion, Service, GSP, Feld, Safety und Rueckkopplung
Stand: 2026-11-21. Diese Matrix ist eine Engineering-Referenz, keine Homologationsfreigabe.

## Begriffe und Rollen

- KBA: deutsche Typgenehmigungs- und Marktueberwachungsbehoerde (inkl. Massnahmen und Rueckrufe, soweit zustaendig). Keine allgemeine Werkstatt oder HU-Pruefstelle.
- TUeV und GTUe: Pruef-/Ueberwachungsorganisationen bzw. technische Dienste je Zulassung/Anerkennung und Auftrag; nicht mit dem KBA gleichsetzen.
- MLIT: japanisches Verkehrsministerium; OBD-Kensa ist japanisches ePTI-Regime, nicht EU-Roadworthiness.
- EPA: US-Bundesumweltbehoerde. CARB: kalifornische Luftreinhaltebehoerde mit eigener Rechtsgrundlage. Kein pauschales EPA=CARB.
- Brasilien: CONAMA/IBAMA (insbesondere PROCONVE, IUMPR), je Funktion zusaetzlich SENATRAN, INMETRO und weitere Stellen.
- Indien: MoRTH und CMVR/AIS/BS VI; Pruefung und Genehmigungswege mit anwendbaren Pruefinstituten getrennt betrachten.
- China: MEE (Emissionen) und SAMR/MIIT je Marktstandard, Produkt und Zulassung; China 6 aktuell, China 7 LD bis zu amtlicher Veroeffentlichung als offen behandeln.
- EU: EUR-Lex/Kommission fuer Rechtsakte; nationale Typgenehmigungs-, Marktueberwachungs- und PTI-Stellen (etwa KBA) unterscheiden.
- RoW: **kein einheitlicher Rechtsraum**. UK (GB vs NI), Kanada, Australien, Japan, Korea, ASEAN, Indien, Brasilien, weitere Staaten jeweils separat.
- **EU/b**: Nutzer-Kuerzel noch nicht eindeutig; keine eigenmaechtige Interpretation.
- **GSP, SCE, RTM**: organisations- bzw. kontextspezifische Kuerzel erst nach bestaetigter Definition als verbindliche Rollen/Prozesse kodieren. Bis dahin aufgabenbasierte Platzhalter mit gekennzeichneter Annahme.

## End-to-End-Lebenszyklusmatrix

| Phase | Kernelement | Input aus vorherigen Phasen | Output/Nachweis | Rueckkopplung |
|---|---|---|---|---|
| Regulatorik / Zielmarkt | Zulassungskategorien, Markt, Stichtage, lokale Ausnahmen, Entwuerfe, Normverweise | Offizielle Markttexte, OEM-Produktauslegung | Requirement-ID und Rechtsstatus | Revisionen/WP29/Behörden, neue lokale Umsetzung |
| Systemarchitektur | OBD/OBM, BMS/SOCE, Safety, Cybersecurity, Gateway, remote Datenpfad | Requirements, HARA/TARA, Fahrzeugkonzept | Funktionale Wirkketten, Schnittstellen, Traceability | Feldprobleme, Service und Security Incidents |
| Entwicklung / Software | Monitorlogik, DTC, Enable/Inhibit, CAL ID/CVN, Diagnose-API, OTA/SUMS | E/E Design, Testanforderungen | SW-Konfiguration, Testplan, Cyber-/Safety-Kontrollen | OTA, Werkstattflash, Hotfix |
| Absicherung / PVE | SIL/HIL, Cluster/Gesamtfahrzeug, OBD Demo, Sicherheit, Manipulationsversuch, ePTI Testbarkeit | Anforderungen, DTC/TC, Service-Schnittstellen | Evidence, Reifegrad, bekannte Deficiencies | Fehlende Testabdeckung und Feld-Finding |
| Zertifizierung / Produktion | Type Approval, CoP, Familien, Softwarefreigabe | Belege, Genehmigungsantraege, Versionslisten | Rechtskonforme Freigabe fuer Markt, Fahrzeugkonfiguration | In-Use, Recall, Marktueberwachung |
| Vertrieb / Kunde | Anzeige, Warnung, Datenschutzhinweise, Wartung, OTA-Kommunikation | Softwarestand, Owner Information | Kundeninformation, nachweisbare Software- und Datenhistorie | Kundenbeschwerde, Ueberwachung |
| GSP/Service/After-Sales | DTC/Fehlerspeicher, GFF, SOVD/UDS, Reparaturleitfaeden, Werkstattupdates, Teiletausch | Zulassungsrelevante Betriebsdaten und Diagnose-Spezifikationen | Reparatur, SW-Stand, Fehlerrueckmeldung, Serviceakte | Fehlerbild an Entwicklung, Quality, Regulatorik |
| PTI/HU/ePTI | nationale technische Pruefpflicht, Zugriff, DTC-/Warnungsrelevanz | OBD/RMI, Versionsidentifikation, Sicherheits- und Emissionsfunktionen | Pruefergebnis, Befund, Untersuchungsstatistik | Daten nur soweit rechtlich/technisch zugaenglich an Feldqualitaet |
| Feld / Quality / Marktaufsicht | Warranty, IUMPR/IUPR, OBM/SOCE, Unfaelle/Safety, Cyberalerts, Beschwerden | Flotten-Daten und Reparatur-/Pruefstatistik | Risikobewertung, Abhilfe, Behoerdenmeldung | Anforderungen/Monitoring/OTA/PVE-Re-Test aktualisieren |

## Wirkketten und Zirkelschlusspruefung

1. **SOC/SOCE falsch → Kundenreichweite/Warnung falsch → OBD/SOVD zeigt falschen Wert → Service kann Fehldiagnose stellen → OTA korrigiert Algorithmus → GTR22 Part A/Familienstand und EU7-Feldnachweis neu bewerten.** GTR22 verlangt SOCE/SOCR-Daten, aber keinen pauschalen MIL- oder DTC-Pfad. Jede Folge nur bei nachgewiesener Anwendbarkeit.
2. **Security-Anomalie → TARA/Incident-Verifikation → moegliche Parameter-/Kalibrierungsmanipulation → Emissions-/Battery-/Safety-Folgen → CSMS R155 und ggf. SUMS R156 → Service-/Kundenmassnahme → erneute Absicherung.** Cybersecurity-Erkennung ist nicht gleich Emissions-DTC.
3. **PHEV-Lade-/HV-Fehler → Aenderung der E-Fahranteile/Motorstarts → Emissionsmonitor und Safety-Auswirkungen → EPA/CARB, EU7, China6 Anforderungen differenziert pruefen → HIL/PVE/Feld und Service gemeinsam bewerten.**
4. **Bremsrekup.-Strategie/SW-Update → Reibbremseinsatz → Euro7-Bremsen-Familie/Testkonfiguration → Reparatur/Kundenservice → moegliche veraltete Freigabeevidenz.** Keine automatisch neue Brems-DTC-Pflicht.
5. **Safety-Warnung oder ePTI-DTC → HU/OBD-Kensa-Befund → Werkstatt/SOVD-Fehlerauslesung → OEM-Feldanalyse → Safety/R155/R156/R100/ISO 26262 pruefen → Korrektur und Revalidierung.** Laenderdatenhoheit, Datenschutz und Zugaenglichkeit beachten.
6. **GFF/Diagnoseanleitung falsch → Teiletausch oder fehlerhafte Reparatur → fahrzeugseitige Parametrierung aendert sich → OBD-/SUMS-/Safety-Nachweise koennen betroffen sein → Prozesskorrektur und End-to-End-Retests.**
7. **Remote Monitoring-Anomalie → Datenqualitaet/Version/Consent pruefen → Triage Security vs. Safety vs. Emissionen vs. Batterie → Root Cause → Service/OTA/Behoerdenentscheidung → Feldwirksamkeitsnachweis.** Anomalie ist Beobachtung, nicht automatisch Defect oder Non-compliance.

## Zirkelschluss-/Widerspruchstests fuer Agent

- Zirkelschluss: OBD Monitor ist „korrekt“, weil er denselben Datenwert wie die ECU meldet; ECU-Wert ist „korrekt“, weil OBD denselben Wert meldet. **Unabhaengige Messreferenz** verlangen.
- Zirkelschluss: Feld ist konform, weil keine DTCs vorhanden; DTC-Logik ist konform, weil keine Feldausfaelle gemeldet. **Nachweis der Detektionsfaehigkeit** mit Fehlerbeaufschlagung und Realdaten verlangen.
- Zirkelschluss: OTA-Update ist sicher, weil SUMS Prozess vorhanden; SUMS ist wirksam, weil Update freigegeben. **Nachweis pro Update/Version und Risiko** verlangen.
- Zirkelschluss: ePTI-Testbarkeit gilt als erwiesen, weil GFF erfolgreich; GFF gilt als korrekt, weil ePTI nichts meldet. **Unabhaengige Schnittstellen-/Pruefmitteltests** verlangen.
- Marktuebergreifend: Gleiche technische Funktion bedeutet nicht gleicher Rechtsstatus, Pruefgrenzwert oder Behoerdenverfahren.
- Kein Feld-Rueckschluss auf alle Fahrzeuge ohne Stichproben-/Familien-/Datenqualitaetsbewertung.
- Bei **GSP/RTM/SCE** erst Begriffsklaerung, aber die erforderlichen Funktionen als Rollen-Platzhalter bereits modellieren.

## Mindest-Datensatz je Erkenntnis

requirement_id; title; jurisdiction; source_url; norm_clause; version; issue_date; effective_date; status; applicability; vehicle_class; propulsion; model_year; type_approval_or_registration; function_chain; safety_impact; cybersecurity_impact; antitampering_impact; software_update_impact; diagnostics_protocol; diagnostic_data; service_impact; customer_impact; inspection_impact; field_monitoring; trigger; evidence; owner; reviewer; open_questions; last_verified.

## Amtliche Einstiegsquellen

- Deutschland StVZO Anlagen VIII/VIIIa: https://www.gesetze-im-internet.de/stvzo_2012/anlage_viii.html und https://www.gesetze-im-internet.de/stvzo_2012/anlage_viiia.html
- KBA https://www.kba.de/
- MLIT https://www.mlit.go.jp/jidosha/jidosha_OBD.html
- EPA https://www.ecfr.gov/current/title-40/section-86.1806-27
- CARB https://ww2.arb.ca.gov/resources/documents/obd-ii-regulations-and-rulemaking
- EU https://eur-lex.europa.eu/eli/reg/2024/1257/oj
- IBAMA https://www.gov.br/ibama/pt-br/assuntos/emissoes-e-residuos/emissoes/elaboracao-de-relatorio-iumpr
- Indien https://www.morth.gov.in/
- UNECE https://unece.org/transport/vehicle-regulations-wp29

**Wichtige Grenze:** TUeV und GTUe sind keine staatlichen legislativen Normgeber. Eine vom Hersteller nicht geteilte lokale PTI- oder Werkstattdatenquelle wird durch eine oeffentliche Website nicht automatisch fuer den Agenten verfuegbar.
