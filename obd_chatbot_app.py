import json
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="OBD System Review Assistant", layout="wide")

KNOWLEDGE = {
    "obd eu7": {
        "title": "OBD im EU7-Kontext",
        "core": [
            "OBD ist als Gesamtsystem über Funktionen, Fehlerpfade, Diagnoseentscheidung, Fehlerreaktion und Nachweisführung zu bewerten.",
            "Für BEV rücken systemische Betrachtungen, Diagnoseketten, Dokumentation und Nachweislogik deutlich stärker in den Vordergrund.",
            "Wichtige Bewertungsfragen: Was wird erkannt? Wie sicher wird erkannt? Welche Reaktion folgt? Wie wird die Wirkung bis zum Nachweis geschlossen?"
        ],
        "checks": [
            "Wirkkette Ursache → Erkennung → Diagnoseentscheidung → Reaktion → Nachweis",
            "Variantenabdeckung und Delta-Betrachtung",
            "Freigabereife, Testbarkeit, Dokumentationsqualität",
            "Abgleich mit Markt- und Projektanforderungen"
        ],
        "risks": [
            "Unklare Verantwortlichkeiten",
            "Lücken in Wirkketten und Dokumentation",
            "Nicht nachvollziehbare Varianten-Deltas",
            "Späte Fehlererkennung vor Zertifizierung oder Freigabe"
        ]
    },
    "wirkkettenanalyse": {
        "title": "Wirkkettenanalyse",
        "core": [
            "Eine belastbare Wirkkettenanalyse verbindet technische Ursache, Signalwirkung, Diagnoseentscheidung, Fehlerreaktion, Kundenauswirkung und regulatorischen Nachweis.",
            "Die Analyse sollte nicht auf DTC-Texte reduziert werden, sondern Architektur, Datenpfade, Plausibilitäten und Reaktionslogik einschließen.",
            "Für mehrere Varianten ist eine Master-Wirkkette mit definierten Variantendeltas meist am effizientesten."
        ],
        "checks": [
            "Eindeutige Trigger und Voraussetzungen",
            "Plausibilisierung und Fehlertoleranz",
            "DTC-/Warn-/Degradationslogik",
            "Nachweisbarkeit in Doku, Daten und Test"
        ],
        "risks": [
            "Nur Teilketten dokumentiert",
            "Signalpfade nicht sauber nachvollziehbar",
            "Reaktion passt nicht zum Fehlerbild",
            "Kein konsistenter Bezug zwischen Analyse und Testfall"
        ]
    },
    "obm": {
        "title": "OBM",
        "core": [
            "OBM sollte über Datenquelle, Triggerlogik, Plausibilisierung, Speicherung, Ausleitung und Variantenunterschiede bewertet werden.",
            "Entscheidend ist, ob die Datenkette fachlich und technisch geschlossen sowie später feldtauglich interpretierbar ist.",
            "Neben dem Konzept zählen Konsistenz, Robustheit und Nachweisfähigkeit."
        ],
        "checks": [
            "Datenquelle und Signalqualität",
            "Trigger-/Speicherlogik",
            "Varianten- und Marktbezug",
            "Auswertbarkeit in Feld- und Validierungsdaten"
        ],
        "risks": [
            "Instabile Trigger",
            "Uneinheitliche Variantenumsetzung",
            "Daten ohne belastbare Interpretation",
            "Lücken in Schnittstellen oder Doku"
        ]
    },
    "obfcm": {
        "title": "OBFCM",
        "core": [
            "OBFCM ist vor allem hinsichtlich Datenpfad, Berechnungslogik, Konsistenz und Variantenabbildung zu bewerten.",
            "Wichtig sind Nachvollziehbarkeit der Inputs, stabile Ableitung und konsistente Dokumentation.",
            "Auch bei kleinerem Themenumfang kann der Aufwand durch Varianten und Datenlogik deutlich steigen."
        ],
        "checks": [
            "Inputgrößen und Berechnungslogik",
            "Abgleich über Varianten",
            "Plausibilisierung und Ausreißerbehandlung",
            "Nachweis- und Dokumentationsstand"
        ],
        "risks": [
            "Inkonsistente Datenbasis",
            "Unklare Berechnungslogik",
            "Zu spätes Varianten-Clearing",
            "Fehlende Traceability"
        ]
    },
    "antitampering": {
        "title": "Anti-Tampering",
        "core": [
            "Anti-Tampering ist über Sensorik, Signalpfade, Softwarelogik, Codierung, Plausibilitäten und mögliche Manipulationsangriffe zu betrachten.",
            "Ziel ist nicht nur Schutz, sondern auch nachvollziehbare Bewertung der Wirksamkeit und der Restrisiken.",
            "Relevant sind sowohl technische Maßnahmen als auch Nachweisführung und Governance."
        ],
        "checks": [
            "Angriffsflächen und Manipulationspfade",
            "Erkennung und Reaktion",
            "Schnittstellen zu Diagnose und Dokumentation",
            "Bewertung von Restrisiken"
        ],
        "risks": [
            "Nur punktuelle Schutzbetrachtung",
            "Keine Verbindung zur Wirkkette",
            "Unzureichende Variantenbewertung",
            "Fehlende Nachweis- und Reviewstruktur"
        ]
    },
    "felddaten": {
        "title": "Felddatenanalyse",
        "core": [
            "Eine gute Felddatenanalyse braucht Datenimport, Normalisierung, Filterlogik, KPI-/Event-Auswertung und eine nachvollziehbare fachliche Interpretation.",
            "Für OBD-/OBM-Themen sind Traceability, Variantenbezug und robuste Auffälligkeitserkennung entscheidend.",
            "Das Tool sollte nicht nur Daten anzeigen, sondern konkrete Bewertungslogik unterstützen."
        ],
        "checks": [
            "Datenquellen und Mapping",
            "Filter- und Segmentierungslogik",
            "Variantenzuordnung",
            "Berichts- und Exportfähigkeit"
        ],
        "risks": [
            "Daten ohne Kontext",
            "Fehlinterpretationen durch schwache Filter",
            "Nicht vergleichbare Variantenstände",
            "Keine belastbare Priorisierung"
        ]
    },
    "hil": {
        "title": "HIL / virtuelle Absicherung",
        "core": [
            "Auch ohne reale Hardware braucht eine virtuelle HIL-/SIL-nahe Absicherung klare Modelle, Schnittstellen, Stimuli, Restbussimulation und Testlogik.",
            "Der Nutzen entsteht durch reproduzierbare Testfälle, frühe Fehlererkennung und Vergleichbarkeit über Varianten.",
            "Der Aufwand liegt stark in Modellierung, Integration und Debugging."
        ],
        "checks": [
            "Zielarchitektur und Scope",
            "Abstraktion fehlender Hardware",
            "Stimuli und Fehlersimulation",
            "Testautomatisierung und Ergebnisbewertung"
        ],
        "risks": [
            "Zu breiter Scope",
            "Schwache Modellgüte",
            "Hoher Pflegeaufwand",
            "Unklare Aussagekraft gegenüber Realfahrzeug"
        ]
    }
}

KEYWORDS = {
    "obd eu7": ["eu7", "obd"],
    "wirkkettenanalyse": ["wirkkette", "wirkketten"],
    "obm": ["obm"],
    "obfcm": ["obfcm", "obfcm"],
    "antitampering": ["antitampering", "anti tampering", "tampering"],
    "felddaten": ["felddaten", "field data", "feld"],
    "hil": ["hil", "sil", "restbus", "simulation", "virtuell"]
}

SAVED_PROMPTS = [
    "Bewerte die Wirkkettenanalyse für 5 BEV-Varianten und nenne die größten Risiken.",
    "Gib mir eine Management-Zusammenfassung zu OBM, OBF(C)M und Anti-Tampering.",
    "Welche Arbeitspakete braucht ein Tool zur Felddatenanalyse?",
    "Wie würdest du den HIL-Aufbau ohne reale Hardware strukturieren?"
]


def detect_topics(question: str):
    q = question.lower()
    hits = []
    for topic, words in KEYWORDS.items():
        if any(word in q for word in words):
            hits.append(topic)
    return hits


def build_answer(question: str) -> str:
    topics = detect_topics(question)

    if not topics:
        return (
            "**Einschätzung**\n\n"
            "Ich erkenne kein klares Themencluster. Formuliere die Frage am besten zu OBD EU7, "
            "Wirkkettenanalyse, OBM, OBF(C)M, Anti-Tampering, Felddatenanalyse oder HIL/virtueller Validierung.\n\n"
            "**Sinnvolle nächste Frage**\n"
            "- Welches Thema soll bewertet werden?\n"
            "- Für wie viele Varianten?\n"
            "- Geht es um Konzept, Review, Validierung oder Toolentwicklung?"
        )

    blocks = ["**Fachliche Einschätzung**\n"]
    for topic in topics:
        item = KNOWLEDGE[topic]
        blocks.append(f"### {item['title']}")
        blocks.append("**Kernaussagen**")
        for x in item["core"]:
            blocks.append(f"- {x}")
        blocks.append("**Prüfpunkte**")
        for x in item["checks"]:
            blocks.append(f"- {x}")
        blocks.append("**Typische Risiken**")
        for x in item["risks"]:
            blocks.append(f"- {x}")
        blocks.append("")

    ql = question.lower()
    if any(w in ql for w in ["kosten", "aufwand", "pm", "personal"]):
        blocks.append("**Aufwandslogik**")
        blocks.append(
            "- Aufwand steigt überproportional mit Variantenanzahl, schlechter Doku, schwacher Wiederverwendung und vielen Nachschleifen."
        )
        blocks.append(
            "- Ein effizienter Ansatz ist meist: Master-Betrachtung + definierte Variantendeltas + zentrale Review- und Testlogik."
        )
        blocks.append(
            "- Für Management sollten Personal, Tooling, Datenaufbereitung, Testumgebung und Reviewschleifen getrennt ausgewiesen werden."
        )

    blocks.append("**Empfohlene nächste Schritte**")
    blocks.append("- Scope und Zielbild sauber trennen: Bewertung, Validierung, Toolentwicklung, HIL-Aufbau")
    blocks.append("- Master-Architektur und Variantendeltas definieren")
    blocks.append("- Prüf- und Nachweislogik je Thema festlegen")
    blocks.append("- Aufwand als Szenarien knapp / realistisch / robust schneiden")

    return "\n".join(blocks)


def export_chat(messages):
    export_payload = [{"role": m["role"], "content": m["content"]} for m in messages]
    return json.dumps(export_payload, ensure_ascii=False, indent=2)


st.title("OBD System Review Assistant")
st.caption("Fachchatbot für OBD EU7, Wirkkettenanalyse, OBM, OBF(C)M, Anti-Tampering, Felddatenanalyse und HIL-/virtuelle Validierung")

with st.sidebar:
    st.header("Schnellstart")
    for prompt in SAVED_PROMPTS:
        if st.button(prompt, use_container_width=True):
            st.session_state["pending_prompt"] = prompt
    st.divider()
    st.markdown("**Modus**")
    mode = st.selectbox(
        "Antwortstil",
        ["Engineering", "Management", "Kompakt"],
        index=0,
    )
    st.session_state["mode"] = mode
    st.divider()
    st.download_button(
        label="Chatverlauf exportieren",
        data=export_chat(st.session_state.get("messages", [])),
        file_name="obd_chat_export.json",
        mime="application/json",
        use_container_width=True,
    )

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": (
                "Hallo Frank — ich bin deine erste OBD-/EU7-Chatbot-Basis. "
                "Ich kann strukturierte Einschätzungen zu OBD EU7, Wirkkettenanalyse, OBM, OBF(C)M, "
                "Anti-Tampering, Felddatenanalyse und HIL/virtueller Validierung liefern."
            ),
        }
    ]

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_prompt = st.session_state.pop("pending_prompt", None) or st.chat_input("Frage eingeben ...")

if user_prompt:
    st.session_state["messages"].append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    answer = build_answer(user_prompt)
    mode = st.session_state.get("mode", "Engineering")
    if mode == "Management":
        answer = answer.replace("**Fachliche Einschätzung**", "**Management-Einschätzung**")
        answer += "\n\n**Management-Fokus**\n- Reifegrad, Risiken, Verantwortlichkeiten und Umsetzungsfähigkeit transparent machen."
    elif mode == "Kompakt":
        answer = "\n".join(answer.splitlines()[:18])

    st.session_state["messages"].append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer)
