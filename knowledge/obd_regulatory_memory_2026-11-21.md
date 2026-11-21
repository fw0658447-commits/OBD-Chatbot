# Weltweite OBD-/System-Compliance-Wissensbasis (verifiziert bis 21.11.2026)

> **Zweck:** Persistente fachliche Referenz fuer den OBD-Validierungs-Agenten. Scope: gesamtes Fahrzeug, alle Maerkte, ICE/PHEV/BEV, Lebenszyklus. Quellenstand 2026-11-21. Keine Freigabeentscheidung und kein Ersatz fuer geltende amtliche Texte.
>
> **Quellenstatus je Aussage:** **[G]** geltender, national/regional umgesetzter Text; **[U]** UN-GTR/UN-Regelung als fachliche Vorlage, regionale Anwendbarkeit separat; **[B]** verabschiedeter Beschluss/unterstuetzte Vorlage ohne automatische nationale Wirkung; **[P]** Gesetzes-/Normvorschlag/Arbeitsentwurf; **[N]** technischer Standard, keine eigene generelle Gesetzespflicht; **[E]** technische Engineering-Ableitung; **[O]** offene Verifikation.
>
> **WICHTIG:** Markt, Kategorie, Datum, Type Approval vs. New Registration, Motor-/Fahrzeugmodelljahr, Genehmigungsserie und Antriebskonzept bei jeder Anfrage zuerst klaeren. Kein ungesicherter Schluss von Gesetz A auf Markt B. Quellen nach Stichtag erneut pruefen.

## 1. Quellengestuetzte Kernaussagen

1. **[U] UN GTR 22 / Amendment 2, WP.29/2026/207 (08.09.2026):** Harmonisiertes Verfahren zur Batterie-Dauerhaltbarkeit fuer PEV und OVC-HEV (nicht generelles ICE-/NOVC-HEV-OBD). SOCE und SOCR als Lebenszeitmonitore, OBD-Port fuer beide Werte vorgeschrieben, OTA optional. SOCE-MPR Kategorien 1-1/1-2: 80% bis 5 J/100.000 km und 70% danach bis 8 J/160.000 km; Kategorie 2: 75%/65%. SOCR-MPR derzeit reserviert. Part A prueft SOCE-Monitorgenauigkeit (3-16 Fahrzeuge, statistische Entscheidung; keine pauschale +/-5%-Einzelfahrzeugregel); Part B prueft Batterie-Dauerhaltbarkeit (jaehrliche Behoerdenstichprobe, regelmaessig >=500, mind. 90% ueber anwendbarem MPR/DPR); Part C prueft **optional** virtuelle Strecke fuer V2X oder sonstige Nicht-Traktionsanwendungen der Kategorie 2 (1-4 Fahrzeuge, 50 km virtuelle Strecke oder 2 h, 23 +/- 5 C; >5% Uebermeldung fuehrt fuer Einzeltest zu fail). Familien: A Monitor (MF), B Durability (BD), C Virtual Distance (VD), jeweils separate Kriterien und eindeutige Kennungen. Ein negatives Ergebnis kann Fahrzeugfamilien-Korrekturmassnahmen ausloesen. Annex 2 unterscheidet mandatory OBD-Daten, bei V2X-Option zusaetzliche Daten und marktbezogen zusaetzlich anforderbare Daten. **Nicht behaupten:** GTR 22 schreibt automatisch klassische DTC, MIL, Readiness oder SOVD fuer SOCE vor. Die regionale Umsetzung ist gesondert zu pruefen.
   Quelle: https://unece.org/transport/events/wp29-world-forum-harmonization-vehicle-regulations-200th-session und dort Dokument ECE/TRANS/WP.29/2026/207; begleitender Technical Report /208.
2. **[B] EU-Ratsbeschluss 2026/2542 (09.11.2026, publiziert 18.11.2026):** EU soll in WP.29 fuer die gelisteten Vorschlaege stimmen, darunter GTR 20 Amendment 1 (/204, EV Safety), GTR 21 Amendment 2 (/205, EV Power), GTR 22 Amendment 2 (/207, Battery Durability LD) und GTR 25 Amendment 1 (/209, Battery Durability HD). Der Beschluss **ist selbst kein Inkraftsetzen einer GTR in EU-Typgenehmigungsrecht**. Internationaler Annahmestatus ggf. anhand offizieller AC.3-Sitzungsunterlagen/Registry nachfuehren.
   Quelle: https://eur-lex.europa.eu/eli/dec/2026/2542/oj.
3. **[G] Euro 7 Grundverordnung (EU) 2024/1257 (konsolidierte Fassung 2026):** M1/N1 neue Typen 29.11.2026, Neufahrzeuge 29.11.2027; spaetere Termine fuer schwere Klassen und Spezialfaelle. OBD, OBM, OBFCM, Batteriezustand, off-board Daten und Antitampering sind getrennte Pflichten; Art. 4 verlangt Schutz u.a. von Batterie/BMS, ECU, OBD/OBM, Kilometerzaehler, elektrischen Antrieben. **EU-MPR statt allgemeiner GTR 22:** M1 SOCE 80%/72%; N1 75%/67% fuer die jeweiligen 5 J/100 tkm- bzw. 8 J/160 tkm-Fenster (pruefen, ob Sonderregime zutrifft). Kein SOCR-Grenzwert aus leerer Tabelle erfinden.
   Quelle: https://eur-lex.europa.eu/eli/reg/2024/1257/oj.
4. **[G] Euro 7 Durchfuehrungsverordnung (EU) 2025/1706, geaendert durch (EU) 2026/1764 (13.07., Amtsblatt 22.07.2026):** Annex XV Battery Durability, Art. 10a In-Service Conformity; UN R154 04 series Annex C1 / Level 1A fuer technische Basis, EU-spezifische SOCE-MPR ersetzen R154-Werte; UN R83 Annex 5 fuer ISC. Annex XVII low-temp EV range (Art. 10b optional ISC), Annex XIX EV system power (Art. 10c optional ISC). Hersteller-Konformitaetserklaerung und dokumentierte Familien. **OBFCM fuer PEVs hat besonderen Uebergang bis 01.01.2030** nach Art. 2; andere Teile haben andere Anwendungstermine, also nicht pauschal alles verschieben.
   Quellen: https://eur-lex.europa.eu/eli/reg_impl/2025/1706/oj und https://eur-lex.europa.eu/eli/reg_impl/2026/1764/oj.
5. **[G] Euro 7 Bremsemissionen:** (EU) 2026/1762 definiert pruef-/genehmigungsbezogene Verfahren und Dokumentation fuer M1/N1, angelehnt an **UN R179**, inklusive Bremsen-Emissionsfamilie und fahrzeugspezifischem Reibbremsanteil (C-Faktor). Delegierte (EU) 2026/1214 aktualisiert den Referenzrahmen von UN GTR 24 auf UN R179. Delegierte (EU) 2026/1753 aktualisiert die EU-WVTA-Regelwerksliste fuer u.a. Batterie, Bremsen, Systemleistung, low-temp-range. **[E]** Rekuperations-/Friktionsbremsstrategie und Funktions-/Kalibrierungszustand koennen denselben Fahrzeugnachweis beeinflussen; daraus nicht ohne Rechtsgrundlage einen neuen Brems-DTC folgern.
   Quellen: https://eur-lex.europa.eu/eli/reg_impl/2026/1762/oj ; https://eur-lex.europa.eu/eli/reg_del/2026/1214/oj ; https://eur-lex.europa.eu/eli/reg_del/2026/1753/oj.
6. **[G] USA EPA 40 CFR 86.1806-27:** Modelljahr 2027+ grundsaetzlich 13 CCR 1968.2 California OBD-II vom 30.11.2022 durch Reference, **mit EPA-spezifischen Ausnahmen** (u.a. (a)(4) eine bestimmte California-Antitampering-Bestimmung ausgenommen; (a)(9)-(13) konkrete CO2/Off-Cycle-Teile; Deficiencies EPA nach (c), nicht CARB (k)). OBD muss emissionsrelevante Fehler erkennen, DTC speichern und warnen; Useful Life und Familien/Bins separat berechnen. **Nicht auf BEV ohne Prüfung des Anwendungsbereichs ausdehnen.**
   Quelle: https://www.ecfr.gov/current/title-40/section-86.1806-27 .
7. **[G/N] CARB OBD-II / SAE J1979-2:** 13 CCR 1968.2(d)(9.2.2) sieht fuer 2027+ Fahrzeuge, die den genannten ISO-15765-4-Pfad verwenden, SAE J1979-2 (OBDonUDS) fuer standardisierte OBD-Funktionen vor. Dies ist nicht eine weltweite, fuer alle Fahrzeuge automatisch geltende UDS-Pflicht. OBD-Demo, In-Use-Monitor-Ratios, Speicherlogik, CAL ID/CVN, Mode/Service-Daten und DTC-Status zielgerichtet testen.
   Quellen: https://ww2.arb.ca.gov/resources/documents/obd-ii-regulations-and-rulemaking und https://ww2.arb.ca.gov/sae-j1979-2-guidance.
8. **[G] USA 2026 GHG-Ruecknahme:** EPA finalisierte die Aufhebung bundesweiter Fahrzeug-Treibhausgasstandards am 12.02.2026; Federal Register publiziert 18.02.2026, wirksam 20.04.2026 (91 FR 7686). **Klassische Schadstoff-OBD ist davon nicht pauschal aufgehoben**. Die besondere Bundes-Batterie/GHG-Pflichtenlage muss gegen die aktualisierte CFR-Version geprueft werden. Kalifornische ACC-II-Waiver-Entscheidung wurde durch US Public Law 119-16 (12.06.2025) missbilligt; rechtliche Streitigkeiten/Staendards nicht mit 40 CFR 86.1806-27 verwechseln. **Keine generalisierte Aussage: 'US-Bev OBD entfaellt'**.
   Quellen: https://www.epa.gov/regulations-emissions-vehicles-and-engines/final-rule-rescission-greenhouse-gas-endangerment ; https://www.govinfo.gov/app/details/FR-2026-02-18/2026-03157 ; https://www.congress.gov/119/plaws/publ16/PLAW-119publ16.pdf.
9. **[G] China 6 bleibt tatsaechlich relevant:** MEE-Amendment GB 18352.6-2016 (Bekanntmachung 2026 Nr. 20, vom 23.04.2026; ab 01.05.2026) fuegt Anforderungen u.a. fuer OBD, Defeat Devices, OBD-Demo-Identifikation (CAL ID/CVN Vorher/Nachher; softwarebasierte Fehlersimulation dokumentieren), Fahrzeug-/ECU-Aufbewahrung ab 01.07.2026 und Hybrid-Typprueffamilien hinzu. Der **01.07.2026**-Termin innerhalb des Amendments ist nicht mit Inkrafttreten des gesamten Amendments am **01.05.2026** zu verwechseln.
   Quellen: https://www.mee.gov.cn/xxgk2018/xxgk/xxgk01/202604/t20260430_1150676.html und verlinkter Anhang.
10. **[O/P] China 7 fuer Light-Duty:** Ein finaler, amtlich verifizierter allgemeiner China-7-LD-Abgas-/OBD-Standard samt Durchfuehrungsdatum (insbesondere eine frueher intern verwendete Juli-2029-Annahme) ist in der Recherche bis 21.11.2026 **nicht nachgewiesen**. Daher **nicht als geltende Pflicht ausgeben**; Draft, HD und LD strikt auseinanderhalten. In China aktuelle GB18352.6- und andere tatsaechlich veroeffentlichte Standards separat fuehren.
    Quelle fuer offizielle Bestandskontrolle: https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/dqhjbh/dqydywrwpfbz/ .
11. **[N] China Batterie GB/T 46991.1-2025:** In-vehicle traction battery durability for light-duty vehicles; veroeffentlicht 31.12.2025, wirksam seit 01.07.2026 als **empfohlener nationaler Standard (GB/T)**. Verbindlichkeit kann durch weitere Rechtsakte/Marktmechanismen entstehen, darf aber aus GB/T allein nicht angenommen werden.
    Quelle: https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=D0A1838047E3F5227AC4F7B5721B24FC.
12. **[G] Japan OBD-Kensa/ePTI:** Elektronische OBD-Pruefung seit 01.10.2024, fuer betroffene Import-Neutypen Pruefbeginn 01.10.2025; Pruefpopulation nach relevanten japanischen Fahrzeug-Ersttyp-Terminen, diagnostische Pruefung emissions- und sicherheitsrelevanter Systeme. Kein 1:1-Abbild von EU-PTI. Neue japanische Behoerdenmitteilung 20.11.2026 zur Monitoring-Sitzung 30.11.2026.
    Quellen: https://www.mlit.go.jp/jidosha/jidosha_OBD.html ; https://www.mlit.go.jp/report/press/jidosha09_hh_000368.html.
13. **[P] EU ePTI Roadworthiness Package COM(2025)180 (24.04.2025):** Vorschlag zur Erweiterung von 2014/45/EU und 2014/47/EU, einschl. elektronischer Sicherheitsdiagnose, HV-Systemen, DTC-/SW-Datenzugriff und PN/NOx-Pruefung. Stand 21.11.2026 als **laufendes Gesetzgebungsverfahren**, nicht als bereits verbindliche gesamte neue EU-PTI-Regel.
    Quellen: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52025PC0180 und https://eur-lex.europa.eu/procedure/EN/2025_97.
14. **[G] Indien BS VI OBD Stage II-B:** MoRTH GSR 809(E) vom 09.11.2022 sieht OBD Stage II-B fuer Fahrzeuge ab 01.04.2025 vor; AIS 137, Emissions-DTCs, MIL, IUPR/Monitoring dem genauen Typ zuordnen. EU-/CARB-Schwellen nicht kopieren.
    Quelle: https://www.morth.gov.in/sites/default/files/notifications_document/10-GSR%20809%28E%29%20dated%209th%20November%2C%202022%20OBD%202_0.pdf.
15. **[G] Brasilien Proconve L8/OBD IUMPR:** IBAMA weist 24.08.2026 auf Berichte ueber In-Use Monitor Performance Ratio fuer Hersteller/Importeure leichter Fahrzeuge auf Basis CONAMA 492/2018 und IBAMA IN 16/2025 hin. Direkte Nachweiskette OBD-In-Use-Daten, Reporting und Familien.
    Quelle: https://www.gov.br/ibama/pt-br/assuntos/emissoes-e-residuos/emissoes/elaboracao-de-relatorio-iumpr.
16. **[N/P] SOVD und Remote Diagnose:** ISO 17978-1:2026 (Mai 2026) ist als Grundsatzstandard publiziert. ISO/AWI 17978-4 'Remote Access' ist erst in Entwicklung. **SOVD, Remote OBD, klassischer EOBD-Port und gesetzlich definierte Funkuebertragung sind nicht identisch.** Die Pflicht ergibt sich nur aus einem konkret einschlaegigen Rechtsakt.
    Quellen: https://www.iso.org/standard/85133.html ; https://www.iso.org/standard/94689.html.
17. **[U/G je Genehmigungsmarkt] UN R155 / R156:** Cybersecurity Management und Software Update Management sind eigene rechtliche Regelungsfamilien. Bei der Compliance-Wirkkette pruefen, ob manipulierte Monitorparameter, Softwareupdates, Steuergeraetewechsel, Zertifizierungswerte und Offboard-Daten die Konformitaet nach Euro7, OBD und Safety beeinflussen. Keine generische 'R155 schreibt fuer jeden SOCE DTC' Behauptung.
    Quelle: https://unece.org/transport/road-transport/reference-documents.
18. **[U] Global weitere GTR:** UN GTR 20 Electric Vehicle Safety (Amendment 1 Proposal WP.29/2026/204), GTR 21 EV Power (Amendment 2 /205), GTR 25 Battery Durability HD (Amendment 1 /209). Safety, Power und Durability sind **unterschiedliche Messgegenstaende**; gemeinsame Datenelemente/ECUs sind moeglich, aber keine pauschale gegenseitige Erfuellung.
    Quelle: https://unece.org/transport/events/wp29-world-forum-harmonization-vehicle-regulations-200th-session.

## 2. Marktuebergreifende Verknuepfungen: System-Compliance-Wirkketten

| System-Cluster | Direktes Gesetz/Norm | Gemeinsamer technischer Beruehrungspunkt | Geforderter koordinierter Nachweis | Grenze der Aussage |
|---|---|---|---|---|
| SOCE/SOCR, BMS, OBD | UN GTR22, EU2026/1764, R154/R83, China GB/T46991.1 | Sensoren, Energie-, Temperatur- und Referenzalgorithmen, Daten-Port | Part A/B/ggf. C, Familien, BMS-Version, Referenzmessung, Port-Auslesung | China GB/T ist nicht automatisch Pflicht, USA nicht 1:1 |
| PHEV Emissions-OBD / Antrieb | EPA 86.1806-27+CARB1968.2; EU7; China6 | Motorstart-, Rekuperations-, Lade-/SOC-Strategie | Emissionsfehlermonitoring, MIL/DTC/Readiness, Betriebsarten, OBD-Demo/PVE | PHEV GTR22-Batteriemonitor ist nicht gleich CARB-DTC-Pflicht |
| Antitampering / SW-Aenderung | EU7 Art. 4, R155/R156, China6, EPA CARB-Exemptions | CAL ID/CVN, Checksums, Sensorik, parameterised monitors, OTA | Manipulationsszenarien, SW-Impact-Review, Datenintegritaet, Re-Certification-Abklaerung | EPA (a)(4) ist gezielte Ausnahme, nicht Antitampering-Abschaffung |
| Brake particulate / Regen | EU2026/1762, R179 | Brake blending, Friktionsanteil, Kalibrierung, Masse | Brake families, C-Faktor, Testprotokoll, Varianten-/SW-Stand | Kein pauschaler Brems-OBD-DTC aus R179 |
| Safety / EV Safety | UN GTR20 / ggf. nationale Umsetzung, R155/156 | BMS, thermal propagation, HV isolation, Sicherheitswarnung | Safety Cases, EVS-Tests, Fehlerwirkung, Versionierung | Safety Diagnostic != Emission OBD |
| ePTI/Inspection | Japan OBD-Kensa geltend; EU COM2025/180 vorgeschlagen; EU7 Daten-Port | Scan-Tool, DTC-Relevanz, ECU-Identitaet, Backend-Auswahl | PTI-Pruedaten, Datenzugang, Kompetenz/Authorization, Fault Classification | Japan verbindlich; EU-Vorschlag noch nicht |
| Remote/OTA/Backend | EU7 Offboard-Daten, GTR22 OTA optional; SOVD ISO | Gateway, Zugriffsschutz, BMS- und Datenversion, Flotte | E2E-Datenkonsistenz, Audit Trail, SW-Versionen, Zugriffsrechte | SOVD-Remote-Teil in Entwicklung, keine universelle Pflicht |
| In-Use/Field | GTR22 Part B, EU Battery ISC, CARB IUPR, Brasilien IUMPR, Japan ePTI | Flotte, Alter/KM, Repair/Warranty, Stichprobe | Datenqualitaet, Familienzuordnung, Ausreisserkontrolle, Root Cause, Corrections | Verschiedene Begriffe und Kennzahlen nicht synonym verwenden |

## 3. Fachliche Unterscheidungen, die Agent immer erzwingen muss

- **OBD (Fehlerdiagnose)** vs **OBM (laufende Emissionsmess-/Monitoringfunktionen)** vs **OBFCM (Verbrauchs-/Energiedaten)** vs **SOCE/SOCR (Battery Durability Monitor)** vs **PTI/ePTI (periodische Untersuchung)** vs **SOVD (Diagnose-API)**.
- **Monitorpflicht** vs **DTC-Pflicht** vs **MIL/Warning** vs **Readiness** vs **IUPR/IUMPR** vs **Datenzugang**: immer Paragraph fuer jeden Schritt nachweisen.
- **[G] rechtlich anwendbar** vs **[U] international harmonisiert** vs **[B] beschlossen aber ohne automatische Umsetzung** vs **[P] noch Vorschlag** vs **[N] Standard** vs **[E] Engineering-Empfehlung**.
- **In-Use Verification (GTR22 Part A/B/C)** vs **In-Service Conformity (Euro7)** vs **OBD IUPR** vs **PVE/OD Demo** vs **Conformity of Production (CoP)**.
- **BEV** nicht automatisch mit ICE-Emission-OBD gleichsetzen; dennoch batterie-, brems-, service-, safety- und datenbezogene Compliance nachhalten.
- **Eine BMS-Softwareaktualisierung** kann Monitorfamilie, SOCE-Algorithmen, Zulassungsreferenzwerte, Diagnose-Datenausgabe, Felddaten und Sicherheit zugleich beeinflussen. Beweise statt vermuteter Kausalitaet.

## 4. Pruef-/Validierungspaket (Vorschlag, kein wörtlicher Normtext)

| ID | Paket | Testebenen | Nachweis / Acceptance Gate |
|---|---|---|---|
| W01 | Market/Variant/Date Requirements | Regulatorik, System | Requirements Matrix mit Quelle, Datum, Scope, Rechtsstand, Ausnahme, Owner |
| W02 | E2E Monitor/Data Chain | BMS, SIL/HIL, Fahrzeug, Diagnose | Verified SOCE/SOCR, Fehler-/Plausibilitaetsfaelle, Port-Auslesung, SW- und Familienbezug |
| W03 | OBD Standards/Protokoll | ECU/Gateway, Test-Tool, Fahrzeug | EPA/CARB J1979-2 sofern anwendbar, DTC/Freeze Frame/Readiness/CAL ID/CVN; Marktfall-Matrix |
| W04 | PHEV Cross-Domain | MPT/Cluster/Full Vehicle HIL, PVE | Motorstart/E-Mode/Ladefehler, Emissionswirkung, Monitor Enable/Inhibit, Fehlerreaktionen |
| W05 | In-Use/Fleet | Feld/Quality/Compliance | Part A/B/C oder regionales ISC/IUPR: Population, Stichprobe, Datenqualitaet, Fallentscheidung |
| W06 | OTA/Cyber/Antitampering | SW-Change, Cyber, Vehicle | SW-Impact-Gate, CAL ID/CVN-Traceability, Tampering-Vektoren, Datenintegritaet, Repair |
| W07 | Safety/ePTI/Remote | HV/ADAS, Scan, Service | Landesspezifische DTC-Sets, diagnostischer Zugang, Authentisierung, Update- und Reparaturfaehigkeit |
| W08 | Homologation & Governance | Gesamtfahrzeug + Legal | Dokumentation, 4-Augen-Review, Deltas, Freigabeentscheidung durch berechtigte Funktion |

## 5. Agent-Verhaltensregeln

1. Jede fachliche Antwort beginnt mit: **Rechtsregime & Geltungsbereich, Fahrzeugart/Modelljahr, Status & Primärquelle**. Ist etwas unklar, markiere Annahmen.
2. Zitiere Paragraph, Tabelle, Annex, Stichtag und URL. Keine pauschalen weltweiten Normbehauptungen.
3. Zeige **belegt / nicht belegt / verwechselt mit / offen** bei kritischen Thesen.
4. Stelle Zusammenhaenge als Wirkkette: **Norm -> geforderte Eigenschaft -> ECU/Funktion -> Diagnose-/Datenpfad -> HIL/SIL/Fahrzeug/Flotte -> Homologations-/Feldnachweis -> Owner**.
5. Fuehre einen Delta-Blick USA (EPA vs. CARB), EU (Basis vs. Durchfuehrung vs. UN), China (derzeitige Norm vs. China7-Plan) und Japan/Indien/Brasilien.
6. Trenne regulatorisch benoetigte DTC/MIL/Readiness-Logik strikt von empfohlenen Plausibilitaets-/Cyber-Tests.
7. Kein Compliance-Sign-off. Markiere offenen Volltextbedarf/Behördenabstimmung.
8. Bei Recherche: zuerst amtliche Primärquellen, Veröffentlichungsdatum und konkrete Geltung prüfen; bei unsicheren Angaben ausdrücklich keine Frist nennen.

## 6. Offene Punkte / Watchlist

- [O] Offizielles Protokoll/Global Registry zur AC.3-Annahme von GTR22 Amendment 2 vom 17.-20.11.2026 sowie nationale Implementierungsdaten.
- [O] Euro7: finale technische OBD/OBM/Antitampering-/Datentransfer-Implementierungen, regionale Erweiterungen, UN R83/R154-Anwendungsstand je Genehmigung.
- [O] China7 LD: erster amtlich publizierter finaler Entwurf/Standard, Light-/Heavy-Duty-Trennung, BEV/PHEV Scope, OBD-Demo, ePTI, Remote Reporting, Starttermine.
- [O] USA CARB ACC-II-/Waiver-/Gerichtsstand und konkrete Fortgeltung batteriebezogener Pflichten je Bundesstaat; EPA 86.1806-27 aktualisierte Ausnahmen/deficiencies je MY.
- [O] ISO 17978-4 Remote Access Standardfortschritt, neue R155/R156-Amendments, Datenschutz/Zugangskonzepte.
- [O] EU Roadworthiness COM(2025)180: Rats-/Parlamentsverfahren bis Verabschiedung; Japan OBD-Kensa-Update vom 30.11.2026.
- [O] South Korea, Kanada, UK, Australien, weitere ASEAN-Staaten und regionale ePTI-/SOVD-Regime im naechsten Research-Cycle einzeln anhand offiziellen nationalen Primärrechts ausbauen.

## 7. Quellenliste (amtlich priorisiert, Recherche 21.11.2026)

- UNECE GTR22 Amendment 2 /207 und Technical Report /208: https://unece.org/transport/events/wp29-world-forum-harmonization-vehicle-regulations-200th-session
- EU-Ratsbeschluss 2026/2542: https://eur-lex.europa.eu/eli/dec/2026/2542/oj
- Euro7 Basis: https://eur-lex.europa.eu/eli/reg/2024/1257/oj
- Euro7 LD: https://eur-lex.europa.eu/eli/reg_impl/2025/1706/oj
- Euro7 Battery ISC / EV Range / Power: https://eur-lex.europa.eu/eli/reg_impl/2026/1764/oj
- Euro7 Brake: https://eur-lex.europa.eu/eli/reg_impl/2026/1762/oj
- Euro7 Brake delegated: https://eur-lex.europa.eu/eli/reg_del/2026/1214/oj
- Euro7 WVTA annex: https://eur-lex.europa.eu/eli/reg_del/2026/1753/oj
- EU PTI proposed: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52025PC0180
- USA 40 CFR OBD: https://www.ecfr.gov/current/title-40/section-86.1806-27
- CARB OBD II: https://ww2.arb.ca.gov/resources/documents/obd-ii-regulations-and-rulemaking
- CARB SAE J1979-2: https://ww2.arb.ca.gov/sae-j1979-2-guidance
- EPA repeal: https://www.govinfo.gov/app/details/FR-2026-02-18/2026-03157
- US Public Law 119-16: https://www.congress.gov/119/plaws/publ16/PLAW-119publ16.pdf
- China6 Amendment: https://www.mee.gov.cn/xxgk2018/xxgk/xxgk01/202604/t20260430_1150676.html
- China Standards: https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/dqhjbh/dqydywrwpfbz/
- China GB/T46991.1-2025: https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=D0A1838047E3F5227AC4F7B5721B24FC
- Japan ePTI: https://www.mlit.go.jp/jidosha/jidosha_OBD.html
- Japan monitoring 20.11.2026: https://www.mlit.go.jp/report/press/jidosha09_hh_000368.html
- India GSR809(E): https://www.morth.gov.in/sites/default/files/notifications_document/10-GSR%20809%28E%29%20dated%209th%20November%2C%202022%20OBD%202_0.pdf
- Brazil IBAMA IUMPR: https://www.gov.br/ibama/pt-br/assuntos/emissoes-e-residuos/emissoes/elaboracao-de-relatorio-iumpr
- ISO SOVD Part1: https://www.iso.org/standard/85133.html
- ISO SOVD Part4 draft: https://www.iso.org/standard/94689.html
- UNECE R155/R156 references: https://unece.org/transport/road-transport/reference-documents

**Pflegehinweis:** Dies ist ein zeitpunktbezogener, transparenter Referenzstand. Vor jeder Freigabe: Primärrecht und konsolidierten Rechtsstatus neu öffnen; keine automatische Synchronisation aus diesen Links voraussetzen.


## 8. Ergaenzung 21.11.2026: Grossbritannien, Australien und Kanada (amtliche Quellen)

19. **[B/P] Grossbritannien (GB, nicht automatisch Nordirland):** Das britische Department for Transport hat in seiner **Government Response vom 27.10.2026** beschlossen, Euro 7 fuer neue Fahrzeuge in Grossbritannien einzufuehren. Fuer **alle neu zugelassenen Light-Duty-Fahrzeuge im unbegrenzten Serienverfahren** ist der 29.11.2027 geplant, fuer Small Volume Manufacturers 01.07.2030. Anders als die EU will GB **keine verbindliche Euro-7-Frist fuer neue LD-Typen ab 29.11.2026** einrichten. EU-/vergleichbare UNECE-Genehmigungen sollen anerkannt werden. **Noch fehlt laut Government Response das nachfolgende statutory instrument; bis zu dessen Inkrafttreten ist dies kein bereits vollzogener UK-Rechtsakt.** Nordirland separat vom GB-WVTA beurteilen. Relevanz: dieselbe technische Fahrzeugbasis kann bei GB und EU unterschiedlichen Genehmigungsfristen und Formalien unterliegen; homologationsseitige Modell-/Fahrzeuguebertragung pruefen.
    Quelle: https://www.gov.uk/government/consultations/updating-the-minimum-emission-standard-for-new-road-vehicles/outcome/updating-the-minimum-emission-standard-for-new-road-vehicles-government-response .
20. **[G] Australien ADR 79/05:** Die konsolidierte **Australian Design Rule 79/05 – Emission Control for Light Vehicles** ist geltendes australisches Bundesrecht, zuletzt als Compilation 24.09.2026. Gilt fuer bestimmte Kategorien MA/MB/MC/MD/NA bis 3.500 kg. Datum **01.12.2025 fuer neue Modelle**, **01.07.2028 fuer alle Fahrzeuge**, jeweils den detaillierten Anwendungs- und Uebergangsbedingungen unterliegend. Technische Grundlage orientiert sich an UN-/europaeischen Emissions-/OBD-Verfahren und ist gegen die exakt referenzierte Serie zu pruefen. NICHT mit EU Euro7 gleichsetzen. Der **ADR 112/00 Real Driving Emissions** besitzt ebenfalls eine aktuelle Compilation 24.09.2026. Cross-Market-Folge: OBD-Port, Monitor und RDE als technisch wiederverwendbare Nachweisketten, aber eigene Rechts-, Termin- und Fahrzeugkategorie-Matrix.
    Quellen: https://www.legislation.gov.au/F2024L00443/latest/details ; https://www.legislation.gov.au/F2024L00443/2026-09-24/2026-09-24/text/original/pdf ; https://www.legislation.gov.au/F2024L00447/2026-09-24/2026-09-24/text/original/epub/OEBPS/document_1/document_1.html .
21. **[G/O] Kanada:** Das kanadische On-Road Vehicle and Engine Emission Regulations-Regime ist grundsaetzlich mit US-Bundesemissionsstandards harmonisiert. Ein direkter Automatismus, dass jede aktuelle **EPA-OBD-Untervorschrift, inklusive 2026-Sonderaenderungen**, ohne kanadische Referenz-/Aequivalenzpruefung Anwendung findet, ist nicht nachgewiesen. Pro Programm SOR/2003-2 (konsolidiert), relevante CFR-Bezugsstaende, Import-/Zertifizierungswege und kanadische Besonderheiten pruefen.
    Quelle: https://www.canada.ca/en/environment-climate-change/services/air-pollution/sources/transportation/regulations-vehicles-engines.html .
22. **[G/B] UK Vehicle Certification Agency (VCA), FAQs vom 17.09.2026:** Publizierte FAQ zu Euro7-Fahrzeuganforderungen, z.B. Euro7A vs. Euro7B bei OBFCM/PEV. **Informative Auslegung, nicht als eigene gesetzliche Norm verwenden.** Quelle: https://www.vehicle-certification-agency.gov.uk/vehicle-type-approval/euro-7-faq/ .

### Zusaetzliche Cross-Market-Regeln fuer die Agentenantwort

- **EU vs GB:** Rechtsstand/Frist nicht aus dem Wort „Euro 7“ allein schliessen; GB Government Response != enacted statutory instrument; Nordirland getrennt.
- **Australien vs EU:** ADR 79/05 kann technische UN-/EU-Verfahren nutzen; die verbindliche Durchfuehrung, ADR-Anwendungsdaten und erlaubte Alternativen sind australisches Recht.
- **Kanada vs USA:** Harmonisierung heisst nicht die sofortige Uebernahme jeder EPA-Textaenderung; kanadische Rechtsreferenz verifizieren.
