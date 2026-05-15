import io
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    import docx
except Exception:
    docx = None

st.set_page_config(page_title="OBD Dokumentenvalidierungs-Chatbot", layout="wide")

SEVERITY_ORDER = {"High": 0, "Medium": 1, "Low": 2, "Info": 3}
UNCLEAR_TERMS = [
    "tbd", "to be defined", "to be clarified", "n/a", "not defined",
    "sufficient", "adequate", "as needed", "if necessary", "where applicable",
    "falls erforderlich", "bei bedarf", "geeignet", "ausreichend", "noch offen",
]

COLUMN_SYNONYMS: Dict[str, List[str]] = {
    "DTC_Code": ["dtc_code", "dtc", "dtc code", "fault code", "fehlercode", "diagnostic trouble code"],
    "DTC_Name": ["dtc_name", "name", "dtc name", "fault name", "fehlername"],
    "Description": ["description", "beschreibung", "fault description", "fehlerbeschreibung"],
    "Monitor_ID": ["monitor_id", "monitor", "monitor id", "monitor-id", "monitorid", "monitor name"],
    "Storage_Logic": ["storage_logic", "storage logic", "speicherlogik", "fault memory", "fehlerspeicher"],
    "Healing_Logic": ["healing_logic", "healing logic", "aging", "reset logic", "clear logic", "heilung"],
    "Severity": ["severity", "criticality", "kritikalitaet", "kritikalität", "prio", "priority"],
    "Status": ["status", "state", "reifegrad"],
    "Evidence_Link": ["evidence_link", "evidence", "nachweis", "nachweislink", "test report", "report link"],
    "Testcase_ID": ["testcase_id", "testcase", "test case", "test id", "tc_id", "tc id"],
    "Preconditions": ["preconditions", "vorbedingungen", "precondition"],
    "Test_Steps": ["test_steps", "test steps", "steps", "testschritte"],
    "Expected_Result": ["expected_result", "expected result", "expected", "erwartetes ergebnis", "sollergebnis"],
    "Actual_Result": ["actual_result", "actual result", "ist-ergebnis", "actual"],
    "Test_Status": ["test_status", "test status", "result", "ergebnis", "test result", "teststatus"],
    "SW_Version": ["sw_version", "software version", "softwarestand", "sw", "version"],
}

RULES = {
    "R001": ("High", "DTC-Code muss eindeutig sein"),
    "R002": ("Medium", "DTC-Beschreibung darf nicht leer sein"),
    "R003": ("High", "Monitor-ID darf nicht leer sein"),
    "R004": ("High", "Storage Logic darf nicht leer sein"),
    "R005": ("High", "Jeder DTC braucht mindestens einen Testfall"),
    "R006": ("High", "Jeder Testfall braucht ein Expected Result"),
    "R007": ("Medium", "Jeder Testfall braucht einen Teststatus"),
    "R008": ("High", "Status closed nur mit Evidence-Link erlaubt"),
    "R009": ("High", "DTC aus Matrix muss in Diagnose-Spezifikation vorkommen"),
    "R010": ("High", "Monitor-ID aus Matrix muss in Diagnose-Spezifikation vorkommen"),
    "R011": ("High", "Enable Conditions muessen am Monitor beschrieben sein"),
    "R012": ("Medium", "Inhibit Conditions sollten am Monitor beschrieben sein"),
    "R013": ("High", "Detection Logic muss am Monitor beschrieben sein"),
    "R014": ("Medium", "Healing/Reset/Aging Logic sollte beschrieben sein"),
    "R015": ("Medium", "Unklare Formulierungen muessen reviewed werden"),
    "R016": ("High", "Diagnose-Spezifikation ist leer oder nicht lesbar"),
    "R017": ("Medium", "Testfall verweist nicht eindeutig auf den DTC im Testtext"),
    "R018": ("Medium", "DTC-Beschreibung und Testfall wirken semantisch schwach verbunden"),
}


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def is_blank(value) -> bool:
    if value is None:
        return True
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def safe_str(value) -> str:
    if is_blank(value):
        return ""
    return str(value).strip()


def read_table(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    raise ValueError("Unterstuetzt werden CSV, XLSX und XLS.")


def auto_map_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    mapping: Dict[str, str] = {}
    normalized_existing = {normalize_name(col): col for col in df.columns}
    for canonical, synonyms in COLUMN_SYNONYMS.items():
        candidates = [normalize_name(canonical)] + [normalize_name(s) for s in synonyms]
        for candidate in candidates:
            if candidate in normalized_existing:
                mapping[normalized_existing[candidate]] = canonical
                break
    mapped = df.rename(columns=mapping).copy()
    return mapped, mapping


def read_spec_text(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    name = uploaded_file.name.lower()
    raw = uploaded_file.read()
    if name.endswith((".txt", ".md")):
        return raw.decode("utf-8", errors="ignore")
    if name.endswith(".pdf"):
        if PdfReader is None:
            return ""
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if name.endswith(".docx"):
        if docx is None:
            return ""
        document = docx.Document(io.BytesIO(raw))
        return "\n".join(p.text for p in document.paragraphs)
    return ""


def extract_window(text: str, needle: str, radius: int = 900) -> str:
    if not text or not needle:
        return ""
    match = re.search(re.escape(needle), text, flags=re.IGNORECASE)
    if not match:
        return ""
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    return text[start:end]


def contains_any(text: str, terms: List[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def token_overlap(a: str, b: str) -> float:
    stop = {"the", "and", "oder", "und", "mit", "bei", "for", "from", "this", "that", "dtc", "fault", "error", "fehler"}
    tokens_a = {t for t in re.findall(r"[a-zA-Z0-9_]{3,}", a.lower()) if t not in stop}
    tokens_b = {t for t in re.findall(r"[a-zA-Z0-9_]{3,}", b.lower()) if t not in stop}
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / max(1, min(len(tokens_a), len(tokens_b)))


def make_finding(findings: List[dict], rule_id: str, source: str, affected: str, problem: str, recommendation: str, location: str = ""):
    severity, rule_name = RULES[rule_id]
    findings.append({
        "Finding_ID": f"F-{len(findings) + 1:04d}",
        "Rule_ID": rule_id,
        "Rule_Name": rule_name,
        "Severity": severity,
        "Source": source,
        "Source_Location": location,
        "Affected_Object": affected,
        "Problem": problem,
        "Recommendation": recommendation,
        "Status": "Open",
    })


def validate(dtc_df: pd.DataFrame, tc_df: pd.DataFrame, spec_text: str) -> pd.DataFrame:
    findings: List[dict] = []

    if "DTC_Code" not in dtc_df.columns:
        make_finding(findings, "R002", "DTC-Matrix", "DTC-Matrix", "Pflichtspalte DTC_Code fehlt oder wurde nicht erkannt.", "Spalte DTC_Code ergaenzen oder Spaltenmapping anpassen.")
        return pd.DataFrame(findings)

    if "DTC_Code" in dtc_df.columns:
        dupes = dtc_df[dtc_df["DTC_Code"].astype(str).str.strip().duplicated(keep=False)]
        for idx, row in dupes.iterrows():
            make_finding(findings, "R001", "DTC-Matrix", safe_str(row.get("DTC_Code")), "DTC-Code kommt mehrfach vor.", "DTC-Code eindeutig machen oder Duplikat fachlich begruenden.", f"Zeile {idx + 2}")

    for idx, row in dtc_df.iterrows():
        dtc = safe_str(row.get("DTC_Code")) or f"Zeile {idx + 2}"
        if is_blank(row.get("Description")):
            make_finding(findings, "R002", "DTC-Matrix", dtc, "DTC-Beschreibung fehlt.", "Fehlerbild, Diagnoseentscheidung und technische Auswirkung beschreiben.", f"Zeile {idx + 2}")
        if is_blank(row.get("Monitor_ID")):
            make_finding(findings, "R003", "DTC-Matrix", dtc, "Monitor-ID fehlt.", "DTC einem konkreten Monitor zuordnen.", f"Zeile {idx + 2}")
        if is_blank(row.get("Storage_Logic")):
            make_finding(findings, "R004", "DTC-Matrix", dtc, "Storage Logic fehlt.", "Speicherlogik mit pending/confirmed/aging/clear beschreiben.", f"Zeile {idx + 2}")
        if safe_str(row.get("Status")).lower() == "closed" and is_blank(row.get("Evidence_Link")):
            make_finding(findings, "R008", "DTC-Matrix", dtc, "Status ist closed, aber Evidence-Link fehlt.", "Nachweis verlinken oder Status auf Open/In Review setzen.", f"Zeile {idx + 2}")

    tc_dtc_values = set()
    if "DTC_Code" in tc_df.columns:
        tc_dtc_values = {safe_str(x).upper() for x in tc_df["DTC_Code"].tolist() if safe_str(x)}
    for idx, row in dtc_df.iterrows():
        dtc = safe_str(row.get("DTC_Code"))
        if dtc and dtc.upper() not in tc_dtc_values:
            make_finding(findings, "R005", "DTC-/Testfallmatrix", dtc, "Kein Testfall fuer diesen DTC gefunden.", "Testfall ergaenzen oder fachliche Ausnahme dokumentieren.", f"DTC-Zeile {idx + 2}")

    for idx, row in tc_df.iterrows():
        tc = safe_str(row.get("Testcase_ID")) or f"Zeile {idx + 2}"
        dtc = safe_str(row.get("DTC_Code"))
        if is_blank(row.get("Expected_Result")):
            make_finding(findings, "R006", "Testfallmatrix", tc, "Expected Result fehlt.", "Erwartetes Diagnoseverhalten eindeutig beschreiben.", f"Zeile {idx + 2}")
        if is_blank(row.get("Test_Status")):
            make_finding(findings, "R007", "Testfallmatrix", tc, "Teststatus fehlt.", "Status wie Passed, Failed, Blocked oder Open pflegen.", f"Zeile {idx + 2}")
        combined_test_text = " ".join(safe_str(row.get(col)) for col in ["Preconditions", "Test_Steps", "Expected_Result"])
        if dtc and dtc.upper() not in combined_test_text.upper():
            make_finding(findings, "R017", "Testfallmatrix", tc, f"DTC {dtc} wird im Testtext/Expected Result nicht eindeutig genannt.", "DTC-Code im Testschritt oder Expected Result explizit referenzieren.", f"Zeile {idx + 2}")

    spec = spec_text or ""
    if spec_text is not None and len(spec.strip()) == 0:
        make_finding(findings, "R016", "Diagnose-Spezifikation", "Spezifikation", "Spezifikation ist leer, nicht hochgeladen oder nicht lesbar.", "TXT/DOCX/PDF mit Textschicht hochladen; gescannte PDFs benoetigen OCR.")
    elif spec.strip():
        for idx, row in dtc_df.iterrows():
            dtc = safe_str(row.get("DTC_Code"))
            monitor = safe_str(row.get("Monitor_ID"))
            description = safe_str(row.get("Description"))
            if dtc and not re.search(re.escape(dtc), spec, flags=re.IGNORECASE):
                make_finding(findings, "R009", "Diagnose-Spezifikation", dtc, "DTC wird in der Diagnose-Spezifikation nicht gefunden.", "DTC in Spezifikation aufnehmen oder Matrix korrigieren.")
            monitor_window = extract_window(spec, monitor) if monitor else ""
            if monitor and not monitor_window:
                make_finding(findings, "R010", "Diagnose-Spezifikation", monitor, "Monitor-ID wird in der Diagnose-Spezifikation nicht gefunden.", "Monitorabschnitt mit eindeutiger Monitor-ID ergaenzen.")
            if monitor_window:
                if not contains_any(monitor_window, ["enable", "enabling", "vorbeding", "aktivierungsbeding", "start condition"]):
                    make_finding(findings, "R011", "Diagnose-Spezifikation", monitor, "Enable Conditions am Monitor nicht erkannt.", "Enable Conditions mit Signalen, Grenzwerten und Betriebszustand ergaenzen.")
                if not contains_any(monitor_window, ["inhibit", "disable", "sperr", "block", "nicht aktiv", "inhibition"]):
                    make_finding(findings, "R012", "Diagnose-Spezifikation", monitor, "Inhibit Conditions am Monitor nicht erkannt.", "Inhibit Conditions ergaenzen oder Not Applicable begruenden.")
                if not contains_any(monitor_window, ["detect", "detection", "threshold", "limit", "grenzwert", "plausib", "set condition"]):
                    make_finding(findings, "R013", "Diagnose-Spezifikation", monitor, "Detection Logic am Monitor nicht erkannt.", "Fehlererkennung mit Trigger, Threshold und Set-Condition beschreiben.")
                if not contains_any(monitor_window, ["heal", "aging", "reset", "clear", "loesch", "lösch", "heil"]):
                    make_finding(findings, "R014", "Diagnose-Spezifikation", monitor, "Healing/Reset/Aging Logic am Monitor nicht erkannt.", "Clear-/Healing-/Aging-Bedingungen ergaenzen.")
                if description and token_overlap(description, monitor_window) < 0.10:
                    make_finding(findings, "R018", "DTC-Matrix/Diagnose-Spezifikation", dtc or monitor, "DTC-Beschreibung und Monitorabschnitt wirken semantisch schwach verbunden.", "Beschreibung und Monitorlogik fachlich abgleichen; ggf. Zuordnung korrigieren.")

        for term in UNCLEAR_TERMS:
            for match in re.finditer(re.escape(term), spec, flags=re.IGNORECASE):
                context = spec[max(0, match.start() - 80): min(len(spec), match.end() + 80)].replace("\n", " ")
                make_finding(findings, "R015", "Diagnose-Spezifikation", term, f"Unklare Formulierung gefunden: '{term}'.", f"Formulierung konkretisieren. Kontext: {context}")

    if not findings:
        return pd.DataFrame(columns=["Finding_ID", "Rule_ID", "Rule_Name", "Severity", "Source", "Source_Location", "Affected_Object", "Problem", "Recommendation", "Status"])
    result = pd.DataFrame(findings)
    return result.sort_values(by="Severity", key=lambda s: s.map(SEVERITY_ORDER)).reset_index(drop=True)


def overall_status(findings: pd.DataFrame) -> str:
    if findings.empty:
        return "Freigabefaehig auf Basis der geprueften Dokumente und Regeln."
    if (findings["Severity"] == "High").any():
        return "Nicht freigabefaehig auf Basis offener High-Findings."
    if (findings["Severity"] == "Medium").any():
        return "Review erforderlich auf Basis offener Medium-Findings."
    return "Bedingt freigabefaehig auf Basis der geprueften Dokumente und Regeln."


def management_summary(findings: pd.DataFrame) -> str:
    status = overall_status(findings)
    if findings.empty:
        return f"**Gesamtstatus:** {status}\n\nKeine Findings im aktuellen Regelumfang."
    counts = findings["Severity"].value_counts().to_dict()
    top_high = findings[findings["Severity"] == "High"].head(5)
    lines = [
        f"**Gesamtstatus:** {status}",
        "",
        f"**Findings:** High={counts.get('High', 0)}, Medium={counts.get('Medium', 0)}, Low={counts.get('Low', 0)}, Info={counts.get('Info', 0)}",
        "",
        "**Wichtigste Blocker:**",
    ]
    if top_high.empty:
        lines.append("- Keine High-Findings; Medium-Findings reviewen.")
    else:
        for _, row in top_high.iterrows():
            lines.append(f"- {row['Rule_ID']} / {row['Affected_Object']}: {row['Problem']}")
    lines.extend([
        "",
        "**Naechster Schritt:** High-Findings schliessen oder fachlich begruenden; danach Test-/Evidence-Abdeckung erneut pruefen.",
    ])
    return "\n".join(lines)


def build_excel(findings: pd.DataFrame, summary: pd.DataFrame, dtc_df: pd.DataFrame, tc_df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        findings.to_excel(writer, index=False, sheet_name="Findings")
        summary.to_excel(writer, index=False, sheet_name="Summary")
        dtc_df.head(200).to_excel(writer, index=False, sheet_name="DTC_Input_Preview")
        tc_df.head(200).to_excel(writer, index=False, sheet_name="Testcase_Input_Preview")
    return buffer.getvalue()


def answer_question(question: str, findings: pd.DataFrame, dtc_df: pd.DataFrame, tc_df: pd.DataFrame, spec_text: str) -> str:
    q = question.lower()
    if findings is None:
        return "Bitte zuerst Dokumente hochladen und die Validierung starten."
    if "gesamt" in q or "status" in q or "freigabe" in q:
        return management_summary(findings)
    if "high" in q or "blocker" in q:
        subset = findings[findings["Severity"] == "High"]
        if subset.empty:
            return "Es gibt aktuell keine High-Findings im geprueften Umfang."
        return "**High-Findings:**\n\n" + subset[["Finding_ID", "Rule_ID", "Affected_Object", "Problem", "Recommendation"]].to_markdown(index=False)
    rule_match = re.search(r"r\d{3}", q)
    if rule_match:
        rule_id = rule_match.group(0).upper()
        rule = RULES.get(rule_id)
        subset = findings[findings["Rule_ID"] == rule_id]
        if not rule:
            return f"Regel {rule_id} ist im aktuellen Regelkatalog nicht vorhanden."
        text = f"**{rule_id}: {rule[1]}**\n\nSchweregrad: {rule[0]}"
        if subset.empty:
            return text + "\n\nDiese Regel hat aktuell kein Finding erzeugt."
        return text + "\n\n**Aktuelle Findings:**\n\n" + subset[["Finding_ID", "Affected_Object", "Problem", "Recommendation"]].to_markdown(index=False)
    dtc_match = re.search(r"\b[pucb][0-9a-f]{4}\b", q, flags=re.IGNORECASE)
    if dtc_match:
        dtc = dtc_match.group(0).upper()
        dtc_rows = dtc_df[dtc_df.get("DTC_Code", pd.Series(dtype=str)).astype(str).str.upper() == dtc] if "DTC_Code" in dtc_df else pd.DataFrame()
        tc_rows = tc_df[tc_df.get("DTC_Code", pd.Series(dtype=str)).astype(str).str.upper() == dtc] if "DTC_Code" in tc_df else pd.DataFrame()
        f_rows = findings[findings["Affected_Object"].astype(str).str.upper().str.contains(dtc, regex=False)]
        parts = [f"**Analyse fuer DTC {dtc}**"]
        if not dtc_rows.empty:
            parts.append("\n**DTC-Matrix:**\n" + dtc_rows.head(5).to_markdown(index=False))
        if not tc_rows.empty:
            parts.append("\n**Testfaelle:**\n" + tc_rows.head(10).to_markdown(index=False))
        if not f_rows.empty:
            parts.append("\n**Findings:**\n" + f_rows[["Finding_ID", "Rule_ID", "Severity", "Problem", "Recommendation"]].to_markdown(index=False))
        if len(parts) == 1:
            return f"Ich finde DTC {dtc} nicht in den hochgeladenen strukturierten Daten."
        return "\n".join(parts)
    if "evidence" in q or "nachweis" in q:
        ev = findings[findings["Problem"].str.contains("Evidence|Nachweis|Testfall", case=False, na=False)]
        if ev.empty:
            return "Es wurden keine expliziten Evidence-/Nachweis-Findings gefunden."
        return "**Evidence-/Nachweis-Findings:**\n\n" + ev[["Finding_ID", "Rule_ID", "Severity", "Affected_Object", "Problem", "Recommendation"]].to_markdown(index=False)
    if "maßnahme" in q or "massnahme" in q or "nächste" in q or "naechste" in q:
        if findings.empty:
            return "Keine Findings vorhanden. Naechster Schritt: Regelumfang erweitern und mit realen Projektunterlagen pruefen."
        subset = findings.sort_values(by="Severity", key=lambda s: s.map(SEVERITY_ORDER)).head(10)
        return "**Priorisierte Massnahmen:**\n\n" + subset[["Severity", "Affected_Object", "Problem", "Recommendation"]].to_markdown(index=False)
    return "Ich kann Fragen zu Gesamtstatus, High-Findings, DTCs, Regeln, Evidence und naechsten Massnahmen beantworten. Beispiel: 'Welche High Findings gibt es?' oder 'Erklaere R011'."


st.title("OBD Dokumentenvalidierungs-Chatbot")
st.caption("Regelbasierte OBD-Dokumentenpruefung mit Chat-Erklaerung fuer DTC-Matrix, Testfallmatrix und Diagnose-Spezifikation.")

with st.sidebar:
    st.header("Dokumente")
    dtc_file = st.file_uploader("DTC-Matrix hochladen", type=["csv", "xlsx", "xls"])
    tc_file = st.file_uploader("Testfallmatrix hochladen", type=["csv", "xlsx", "xls"])
    spec_file = st.file_uploader("Diagnose-Spezifikation optional", type=["txt", "md", "pdf", "docx"])
    run_validation = st.button("Validierung starten", use_container_width=True)
    st.divider()
    st.markdown("**Typische Fragen**")
    st.markdown("- Welche High Findings gibt es?\n- Wie ist der Gesamtstatus?\n- Erklaere R011.\n- Zeige mir alles zu DTC P0ABC.\n- Welche Evidence fehlt?\n- Was sind die naechsten Massnahmen?")

if "findings" not in st.session_state:
    st.session_state.findings = None
    st.session_state.dtc_df = pd.DataFrame()
    st.session_state.tc_df = pd.DataFrame()
    st.session_state.spec_text = ""
    st.session_state.messages = []

if run_validation:
    if dtc_file is None or tc_file is None:
        st.error("Bitte mindestens DTC-Matrix und Testfallmatrix hochladen.")
    else:
        try:
            raw_dtc = read_table(dtc_file)
            raw_tc = read_table(tc_file)
            dtc_df, dtc_mapping = auto_map_columns(raw_dtc)
            tc_df, tc_mapping = auto_map_columns(raw_tc)
            spec_text = read_spec_text(spec_file) if spec_file else ""
            findings = validate(dtc_df, tc_df, spec_text)
            st.session_state.findings = findings
            st.session_state.dtc_df = dtc_df
            st.session_state.tc_df = tc_df
            st.session_state.spec_text = spec_text
            st.session_state.messages = [{"role": "assistant", "content": management_summary(findings)}]
            st.success("Validierung abgeschlossen.")
        except Exception as exc:
            st.error(f"Validierung fehlgeschlagen: {exc}")

findings = st.session_state.findings
if findings is None:
    st.info("Lade links eine DTC-Matrix und eine Testfallmatrix hoch und starte die Validierung.")
else:
    summary_df = pd.DataFrame([{
        "Timestamp": datetime.now().isoformat(timespec="seconds"),
        "Overall_Status": overall_status(findings),
        "Total_Findings": len(findings),
        "High": int((findings["Severity"] == "High").sum()) if not findings.empty else 0,
        "Medium": int((findings["Severity"] == "Medium").sum()) if not findings.empty else 0,
        "Low": int((findings["Severity"] == "Low").sum()) if not findings.empty else 0,
    }])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Findings", len(findings))
    c2.metric("High", summary_df.loc[0, "High"])
    c3.metric("Medium", summary_df.loc[0, "Medium"])
    c4.metric("Low", summary_df.loc[0, "Low"])
    st.markdown(management_summary(findings))

    with st.expander("Finding-Tabelle", expanded=True):
        if findings.empty:
            st.success("Keine Findings im aktuellen Regelumfang.")
        else:
            severity_filter = st.multiselect("Severity filtern", ["High", "Medium", "Low", "Info"], default=["High", "Medium", "Low", "Info"])
            filtered = findings[findings["Severity"].isin(severity_filter)]
            st.dataframe(filtered, use_container_width=True)

    excel_data = build_excel(findings, summary_df, st.session_state.dtc_df, st.session_state.tc_df)
    st.download_button(
        "Finding-Report als Excel herunterladen",
        data=excel_data,
        file_name="obd_findings_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.divider()
    st.subheader("Chat zum Validierungsergebnis")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    prompt = st.chat_input("Frage zum Ergebnis stellen ...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        answer = answer_question(prompt, findings, st.session_state.dtc_df, st.session_state.tc_df, st.session_state.spec_text)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()
