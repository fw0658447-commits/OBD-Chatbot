"""Shared, local evidence retrieval for the OBD Systemkoordination agent.

Structured retrieval only: no LLM, no network access and no legal sign-off.
Reads the same curated data in both Streamlit applications.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KNOWLEDGE = ROOT / "knowledge"
MARKDOWN_FILES = (
    "obd_regulatory_memory_2026-11-21.md",
    "e2e_authorities_service_field_chains.md",
    "agent_systemkoordination.md",
)
GLOSSARY = {
    "gsp": "GSP: lokale/organisationsspezifische Bedeutung nicht bestaetigt; Aufgaben in Service, Reparatur, Diagnose und Feld pruefen.",
    "sce": "SCE-Relevanz: bislang keine eindeutig belegte allgemeingueltige Legaldefinition; als pruefpflichtige System-Compliance-Relevanz klassifizieren, nicht als gesetzliche Kategorie behaupten.",
    "rtm": "RTM: Abkuerzung im Projektkontext nicht bestaetigt; koennte mehrere Bedeutungen haben. Die konkret gemeinte Prozessdefinition muss hinterlegt werden.",
    "eu/b": "EU/b: markt- bzw. projektspezifische Bezeichnung noch nicht belegt, nicht als eigenstaendige Rechtskategorie interpretieren.",
}
ALIASES = {
    "sovd": ("sovd", "iso 17978"),
    "ota": ("ota", "software-update", "softwareupdate", "sums"),
    "antitampering": ("antitampering", "anti-tampering", "manipulation", "tampering"),
    "safety": ("safety", "sicherheit", "functional safety", "hv", "thermal"),
    "security": ("cybersecurity", "r155", "cyber", "csms", "tara"),
    "epti": ("epti", "hu", "hauptuntersuchung", "obd-kensa", "roadworthiness"),
    "field": ("feld", "field", "iompr", "iumpr", "warranty", "flotte"),
    "service": ("service", "kunde", "werkstatt", "gff", "reparatur", "rmi"),
    "china": ("china", "gb18352", "gb 18352", "chinesisch"),
    "eu": ("euro 7", "euro7", "eu7", "eu-7"),
    "us": ("epa", "carb", "usa", "california", "tier 4"),
    "remote": ("remote obd", "remote ob", "ferndiagnose", "remote", "telematik"),
}
STOPWORDS = {"der","die","das","und","oder","ein","eine","zum","zur","mit","von",
             "für","fuer","was","wie","ist","sind","hat","haben","alle","alles",
             "aus","auf","dem","den","des","im","in","zu","ich","mein","meine",
             "bitte","prüfung","prüfen","prüfe","zeig","zeige","warum","welche",
             "the","and","for","with","from","this","that"}

def _read_json(filename, fallback):
    try:
        return json.loads((KNOWLEDGE / filename).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback

def _tokens(value):
    words = re.findall(r"[\w./-]{3,}", str(value).lower())
    return {w for w in words if w not in STOPWORDS}

def _score(query, candidate, add_exact=True):
    tokens = _tokens(query)
    candidate = str(candidate).lower()
    if not tokens:
        return 0
    score = sum(1 for t in tokens if t in candidate)
    if add_exact and len(query.strip()) >= 5 and query.strip().lower() in candidate:
        score += 5
    return score

def _expanded_query(query):
    q=query.lower()
    additions=[]
    for _,terms in ALIASES.items():
        if any(t in q for t in terms):
            additions.extend(terms[:2])
    return query + " " + " ".join(additions)

def _node_hits(question, graph):
    q=question.lower()
    result=[]
    for node in graph.get("nodes", []):
        identifier=node["id"].lower()
        title=node.get("name","").lower()
        normalized_id=identifier.replace("_"," ").replace("-"," ")
        if (identifier in q or title in q or
            (len(normalized_id)>5 and normalized_id in q) or
            any(t in title and t in q for t in ("sovd","gtr 22","r155","r156","j1979-2","euro 7","euro7","r154","epti","obd-kensa","26262","21434","24089"))):
            result.append(node)
    return result

def search_knowledge(query, limit=6):
    """Return ranked and attributable source records, graph edges, projects and text."""
    q=_expanded_query(query)
    catalog=_read_json("source_catalog.json",{})
    graph=_read_json("regulatory_graph.json",{})
    early=_read_json("early_warning_initiatives.json",{})
    src=[]
    for entry in catalog.get("sources",[]):
        hay=" ".join(str(entry.get(k,"")) for k in ("title","id","market","issuer","domain"))
        score=_score(q,hay)
        if score:
            src.append((score,entry))
    src.sort(key=lambda x:(-x[0],x[1]["id"]))
    projects=[]
    for record in early.get("initiatives",[]):
        hay=" ".join(str(record.get(k,"")) for k in ("title","id","kind","region","topics","assessment"))
        score=_score(q,hay)
        if score:
            projects.append((score,record))
    projects.sort(key=lambda x:(-x[0],x[1]["id"]))
    nodes=_node_hits(question,graph)
    hit_ids={node["id"] for node in nodes}
    edges=[e for e in graph.get("edges",[]) if e.get("from") in hit_ids or e.get("to") in hit_ids]
    docs=[]
    for name in MARKDOWN_FILES:
        path=KNOWLEDGE/name
        if not path.exists():
            continue
        raw=path.read_text(encoding="utf-8")
        chunks=re.split(r"(?=^##\s+)|\n(?=\d+\. \*\*\[)|\n\n+",raw,flags=re.M)
        for chunk in chunks:
            chunk=chunk.strip()
            if not chunk or len(chunk)<70:
                continue
            score=_score(q,chunk)
            if score:
                docs.append((score,{"filename":name,"excerpt":chunk[:1200]}))
    docs.sort(key=lambda x:-x[0])
    return {
        "source_matches":[x[1] for x in src[:limit]],
        "initiatives":[x[1] for x in projects[:min(limit,4)]],
        "nodes":nodes[:limit],
        "edges":edges[:min(limit,6)],
        "knowledge":[x[1] for x in docs[:min(limit,3)]],
        "unknown_terms":[message for key,message in GLOSSARY.items()
                         if re.search(r"(?<!\w)"+re.escape(key)+r"(?!\w)",question,re.I)],
        "source_count":len(catalog.get("sources",[])),
        "relation_count":len(graph.get("edges",[])),
        "initiative_count":len(early.get("initiatives",[])),
    }

def answer_from_knowledge(question):
    """A grounded answer excerpt to append to the existing domain heuristics."""
    hits=search_knowledge(question)
    if not any(hits[k] for k in ("source_matches","initiatives","nodes","edges","knowledge","unknown_terms")):
        return ""
    lines=["### Weltweite Regulatorik- und E2E-Einordnung",
           "Die folgenden Treffer stammen aus der kuratierten Wissensbasis. "
           "Sie sind **keine automatische Compliance-Freigabe**; Markt, Kategorie, "
           "Modelljahr, Inkrafttreten und originale Normklausel sind fallbezogen zu pruefen."]
    if hits["unknown_terms"]:
        lines+=["","**Begriffe mit offenem Geltungsbereich**"]
        lines+=["- "+v for v in hits["unknown_terms"]]
    if hits["nodes"]:
        lines+=["","**Relevante Regelwerke / Normen**"]
        for n in hits["nodes"][:5]:
            lines.append(f"- {n['name']} ({n.get('market','?')}; Status: {n.get('status','offen')})")
    if hits["edges"]:
        lines+=["","**Querverbindungen und Nachweisbedarf**"]
        for e in hits["edges"][:5]:
            state="Textbezug im Katalog (juristisch pruefen)" if e.get("confidence")=="verified_text" else "Hypothese / Expertenreview erforderlich"
            lines.append(f"- {e['from']} ↔ {e['to']}: {e['relation']} — {e.get('basis','')} **[{state}]**")
    if hits["source_matches"]:
        lines+=["","**Quellen zur direkten Nachpruefung**"]
        for s in hits["source_matches"][:6]:
            cls=s.get("source_class","")
            lines.append(f"- [{s['title']}]({s['url']}) — {s['market']}; Quelle: {cls}")
    if hits["initiatives"]:
        lines+=["","**Fruehwarnung: Gruppen, Vorhaben und Piloten**"]
        for p in hits["initiatives"][:4]:
            lines.append(f"- [{p['title']}]({p['source']}) — {p.get('status','ungeprueft')}; {p.get('assessment','')}")
    if hits["knowledge"]:
        lines+=["","**E2E-/Engineering-Kontext (kuratiert, nicht Normtext)**"]
        for hit in hits["knowledge"][:2]:
            snippet=re.sub(r"\s+"," ",hit["excerpt"])[:440]
            lines.append(f"- *{hit['filename']}*: {snippet}")
    lines+=["","**Gesamtsystem-Pruefpfad:** Rechtsgrundlage → betroffene Fahrzeugfunktion "
           "→ Diagnose-/Datenkette → Safety/Security/SUMS → HIL/PVE/Zertifizierung "
           "→ Service/Kunde/ePTI → Feldueberwachung → Korrektur und Revalidierung. "
           "Unabhaengige Messreferenzen pruefen, um Zirkelbezuege zu vermeiden."]
    return "\n".join(lines)

def knowledge_metrics():
    catalog=_read_json("source_catalog.json",{})
    graph=_read_json("regulatory_graph.json",{})
    early=_read_json("early_warning_initiatives.json",{})
    return {"sources":len(catalog.get("sources",[])),
            "regulations_and_standards":len(graph.get("nodes",[])),
            "relationships":len(graph.get("edges",[])),
            "initiatives":len(early.get("initiatives",[]))}
