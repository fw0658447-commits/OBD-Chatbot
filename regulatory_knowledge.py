"""Read-only market-wide regulatory memory for the OBD validation chatbot.

Never interprets a knowledge hit as legal sign-off. The maintained knowledge
file contains sources, legal statuses, applicability and open questions.
"""
from pathlib import Path
import re
import streamlit as st

MEMORY_PATHS = [
    Path(__file__).resolve().parent / "knowledge" / "obd_regulatory_memory_2026-11-21.md",
    Path(__file__).resolve().parent / "knowledge" / "e2e_authorities_service_field_chains.md",
]

@st.cache_data(show_spinner=False)
def read_regulatory_memory():
    try:
        return "\n\n".join(path.read_text(encoding="utf-8") for path in MEMORY_PATHS if path.exists())
    except OSError:
        return ""

def _chunks(text):
    blocks = re.split(r"(?=^##\s+)", text, flags=re.M)
    return [b.strip() for b in blocks if b.strip()]

def search_regulatory_memory(query, limit=8):
    doc = read_regulatory_memory()
    if not doc or not query.strip():
        return []
    tokens = set(re.findall(r"[\w/-]{3,}", query.lower()))
    results = []
    for section in _chunks(doc):
        for block in re.split(r"\n(?=\d+\. \*\*\[)", section):
            if not block.strip():
                continue
            lower = block.lower()
            score = sum(1 for t in tokens if t in lower)
            if query.lower() in lower:
                score += 5
            if score:
                results.append((score, block.strip()))
    results.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in results[:limit]]

def regulatory_memory_panel():
    with st.expander("Weltweite Regulatorik-Wissensbasis (Stand 21.11.2026)", expanded=False):
        st.caption("Weltweite Quellen, Behoerden, Service-/Feld-Wirkketten und Zirkelschluesse. Keine automatische rechtliche Freigabe; Modelljahr und regionalen Rechtsstand pruefen.")
        if not read_regulatory_memory():
            st.warning("Regulatorik-Wissensbasis fehlt im Deployment.")
            return
        q = st.text_input("Regelwerk, Markt, Behoerde oder E2E-Wirkkette suchen", key="regulatory_search", placeholder="z. B. KBA, GTUe, MLIT, OTA, GSP, Feld, SOVD, Zirkelschluss")
        if q.strip():
            hits = search_regulatory_memory(q)
            if not hits:
                st.info("Kein entsprechender Eintrag in der Wissensbasis. Fehlender Treffer ist keine regulatorische Entwarnung.")
            for idx, hit in enumerate(hits, 1):
                with st.expander(f"Treffer {idx}", expanded=(idx == 1)):
                    st.markdown(hit)
        else:
            st.info("Recherche-Stand und Quellen sind persistent in der Datei hinterlegt. Einen Suchbegriff eingeben.")
            st.markdown("[Regulatorik-Wissensbasis](https://github.com/fw0658447-commits/OBD-Chatbot/blob/main/knowledge/obd_regulatory_memory_2026-11-21.md) | [E2E Behörden/Service/Feld](https://github.com/fw0658447-commits/OBD-Chatbot/blob/main/knowledge/e2e_authorities_service_field_chains.md)")
