#!/usr/bin/env python3
"""Check early-warning initiative references against the curated source registry.

No semantic claims of adoption or implementation. Identifies known initiatives,
source gaps, duplicate records and rules exposed to potential future changes.
"""
from pathlib import Path
import datetime
import json
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1]
K=ROOT/"knowledge"
def load(name): return json.loads((K/name).read_text(encoding="utf-8"))
def main():
    initiatives=load("early_warning_initiatives.json").get("initiatives",[])
    sources=load("source_catalog.json").get("sources",[])
    graph=load("regulatory_graph.json")
    rules={x["id"] for x in graph["nodes"]}
    byurl={x["url"] for x in sources}
    unique=set()
    findings=[]
    priority=defaultdict(list)
    for item in initiatives:
        if item["id"] in unique:
            findings.append({"id":item["id"],"kind":"duplicate_initiative_id","severity":"high"})
        unique.add(item["id"])
        if item["source"] not in byurl:
            findings.append({"id":item["id"],"kind":"source_not_yet_curated","severity":"medium","url":item["source"]})
        for rule in item.get("linked_rules",[]):
            if rule not in rules:
                findings.append({"id":item["id"],"kind":"unknown_linked_rule","severity":"high","rule":rule})
            else:
                priority[rule].append(item["id"])
        if item["kind"] in ("working_group","public_consultation","legislative_proposal","completed_research_pilot","reported_pilot","standards_work_in_progress","draft_guidance"):
            if not item.get("status") or not item.get("date"):
                findings.append({"id":item["id"],"kind":"missing_status_or_date","severity":"high"})
    report={
        "review_date_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "initiatives_count":len(initiatives),
        "by_kind":{k:sum(x["kind"]==k for x in initiatives) for k in sorted({x["kind"] for x in initiatives})},
        "linked_regulations":{k:sorted(v) for k,v in sorted(priority.items())},
        "findings":findings,
        "caution":"Early-warning discovery. An initiative, pilot, draft or consultation does not create binding obligations; a source change is a review trigger only."
    }
    (K/"early_warning_review.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# Early-warning review","",f"Reviewed: {report['review_date_utc']}","","## Initiatives"]
    lines += [f"- **{x['id']}** ({x['kind']}; {x['region']}; {x['status']}): {x['title']} — {x['source']}" for x in initiatives]
    lines += ["","## Data integrity"]
    lines += [f"- {x['severity']} {x['kind']}: {x['id']}" for x in findings] or ["- No structural findings"]
    lines += ["","## Rulewatch relevance"]
    lines += [f"- **{rule}**: {', '.join(items)}" for rule,items in sorted(priority.items())]
    lines += ["","**Interpretation:** Linkage is a research/engineering relevance, not an assertion of legal incorporation."]
    (K/"early_warning_review.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Early warning: {len(initiatives)} initiatives, {len(findings)} integrity findings")

if __name__=="__main__": main()
