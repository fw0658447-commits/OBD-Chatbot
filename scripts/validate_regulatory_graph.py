#!/usr/bin/env python3
"""Validate explicit regulatory cross-references and propose nonbinding relationships.

Inputs: curated source_catalog.json, regulatory_graph.json, optional source_status.json.
Outputs: knowledge/regulatory_graph_review.json and .md. Never asserts legal equivalence.
"""
import datetime
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
KD=ROOT/"knowledge"
def load(name,default=None):
    p=KD/name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

def norm(s):
    return re.sub(r"[^a-z0-9]+","",str(s).lower())

def main():
    catalog=load("source_catalog.json",{})
    graph=load("regulatory_graph.json",{})
    status=load("source_status.json",{})
    ids={s["id"] for s in catalog.get("sources",[])}
    nodes={n["id"]:n for n in graph.get("nodes",[])}
    issues=[]
    edges=graph.get("edges",[])
    for n in nodes.values():
        if n.get("source_id") and n["source_id"] not in ids:
            issues.append({"severity":"high","kind":"unknown_source","ref":n["id"],"reason":n["source_id"]})
        if not n.get("status"):
            issues.append({"severity":"high","kind":"missing_status","ref":n["id"]})
    for e in edges:
        if e["from"] not in nodes or e["to"] not in nodes:
            issues.append({"severity":"high","kind":"dangling_edge","ref":e["id"]})
        if e.get("confidence")=="verified_text" and not e.get("basis"):
            issues.append({"severity":"high","kind":"missing_citation_for_verified_edge","ref":e["id"]})
        if e["relation"] in ("similar_obd_topic","shared_technical_subject","shared_system_chain","related_technical_standard","shared_service_chain","shared_vehicle_function","similar_inspection_topic","shared_safety_topic","jurisdictional_intersection") and not e.get("requires_human_review"):
            issues.append({"severity":"high","kind":"unreviewed_inference","ref":e["id"]})
    changed=set(status.get("changed_metadata_sources",[]))
    affected=[]
    for n in nodes.values():
        if n.get("source_id") in changed:
            affected.append(n["id"])
    dependent=defaultdict(list)
    for e in edges:
        dependent[e["to"]].append(e["from"])
        dependent[e["from"]].append(e["to"])
    impacted=set(affected)
    frontier=list(affected)
    for _ in range(2):
        subsequent=[]
        for x in frontier:
            for target in dependent[x]:
                if target not in impacted:
                    impacted.add(target)
                    subsequent.append(target)
        frontier=subsequent
    # Detect technically interesting cyclic dependencies, not assume contradictions.
    adjacency=defaultdict(set)
    for e in edges:
        if e["relation"] in ("shared_system_chain","shared_vehicle_function","related_technical_standard","shared_technical_subject","shared_service_chain","shared_safety_topic"):
            adjacency[e["from"]].add(e["to"])
            adjacency[e["to"]].add(e["from"])
    cycles=[]
    seen=set()
    def dfs(node,parent,path):
        seen.add(node)
        for other in adjacency[node]:
            if other==parent:
                continue
            if other in path:
                cyc=path[path.index(other):]+[other]
                key=tuple(sorted(set(cyc)))
                if len(set(cyc))>=3 and key not in {tuple(sorted(set(c))) for c in cycles}:
                    cycles.append(cyc)
            elif other not in seen:
                dfs(other,node,path+[other])
    for n in nodes:
        if n not in seen:
            dfs(n,None,[n])
    report={
      "checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "nodes":len(nodes),"edges":len(edges),"catalog_sources":len(ids),
      "verified_explicit_links":sum(e.get("confidence")=="verified_text" for e in edges),
      "links_requiring_review":sum(e.get("requires_human_review",True) for e in edges),
      "integrity_issues":issues,"metadata_changed_source_ids":sorted(changed),
      "directly_affected_nodes":sorted(affected),"potentially_impacted_nodes":sorted(impacted),
      "potential_engineering_cycles":cycles,
      "methodology":"Identifier and graph-integrity checks + changed-source impact propagation. Not full text semantic verification; explicit citations need periodic expert review. No inferred legal obligations.",
      "source_status_present":bool(status)
    }
    (KD/"regulatory_graph_review.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    lines=["# Regulatory Graph Review","",f"Checked: {report['checked_utc']}","",f"- {len(nodes)} regulation/standard nodes; {len(edges)} relationships; {len(ids)} catalog sources",f"- {report['verified_explicit_links']} source-text-marked links; {report['links_requiring_review']} inference/review links",f"- {len(issues)} graph-integrity findings",f"- {len(affected)} directly affected nodes, {len(impacted)} impacted within two hops",f"- {len(cycles)} potential engineering relation cycles (NOT legal contradictions)","","## Findings"]
    lines.extend([f"- {x['severity']}: {x['kind']} {x['ref']}" for x in issues] or ["- None"])
    lines.extend(["","## Source-change impact"])
    lines.extend(["- "+x for x in sorted(impacted)] or ["- None observed; requires source monitor snapshots"])
    lines.extend(["","## Human-review queue"])
    lines.extend([f"- {e['id']}: {e['from']} -> {e['to']} ({e['relation']}) — {e['basis']}" for e in edges if e.get("requires_human_review")] or ["- None"])
    lines.extend(["","**Limitation:** This is a structured, traceable plausibility check; it does not prove substantive legal accuracy. Review exact legal text, amendments, effective dates, national adoption and clauses before certification."])
    (KD/"regulatory_graph_review.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("Graph review completed:",len(issues),"integrity findings,",len(impacted),"potentially impacted nodes")

if __name__=="__main__":
    main()
