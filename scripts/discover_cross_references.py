#!/usr/bin/env python3
"""Discover CANDIDATE cross-references in a curated, local evidence corpus.

All suggestions are unverified. No live crawling, no normative legal effect.
Does not modify the approved regulatory_graph.json.
"""
import datetime
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/"knowledge"

# Exact identifier aliases only; not generic terms like "safety" or "OBD".
ALIASES={
"UN_GTR22":[r"\b(?:UN\s*)?GTR\s*(?:No\.?\s*)?22\b",r"\bWP\.29/2026/207\b"],
"GTR20":[r"\b(?:UN\s*)?GTR\s*(?:No\.?\s*)?20\b"],
"UN_R155":[r"\b(?:UN\s*)?R\s*155\b"],
"UN_R156":[r"\b(?:UN\s*)?R\s*156\b"],
"UN_R154":[r"\b(?:UN\s*)?R\s*154\b"],
"UN_R83":[r"\b(?:UN\s*)?R\s*83\b"],
"EU_2024_1257":[r"\b(?:EU\s*)?2024/1257\b"],
"EU_2025_1706":[r"\b(?:EU\s*)?2025/1706\b"],
"EU_2026_1764":[r"\b(?:EU\s*)?2026/1764\b"],
"US_86_1806_27":[r"\b86\.1806-27\b"],
"CARB_1968_2":[r"\b(?:13\s*CCR\s*)?1968\.2\b"],
"SAE_J1979_2":[r"\b(?:SAE\s*)?J1979-2\b"],
"ISO_17978_1":[r"\b(?:ISO\s*)?17978-1\b"],
"ISO_24089":[r"\b(?:ISO\s*)?24089\b"],
"ISO_21434":[r"\b(?:ISO/SAE\s*|ISO\s*)?21434\b"],
"ISO_26262":[r"\b(?:ISO\s*)?26262\b"],
"EU_2018_858":[r"\b(?:EU\s*)?2018/858\b"]
}
FILE_NAMES=["obd_regulatory_memory_2026-11-21.md","e2e_authorities_service_field_chains.md"]
MAX_CONTEXT=600

def main():
    graph=json.loads((D/"regulatory_graph.json").read_text(encoding="utf-8"))
    known={frozenset((e["from"],e["to"])) for e in graph["edges"]}
    candidates=defaultdict(list)
    for name in FILE_NAMES:
        p=D/name
        if not p.exists(): continue
        raw=p.read_text(encoding="utf-8")
        blocks=re.split(r"\n\s*\n|(?=^\d+\.\s+\*\*)",raw,flags=re.M)
        for b in blocks:
            if len(b)<20: continue
            hits={node for node,patterns in ALIASES.items() if any(re.search(regex,b,re.I) for regex in patterns)}
            if len(hits)>1:
                hits=sorted(hits)
                for i,left in enumerate(hits):
                    for right in hits[i+1:]:
                        pair=frozenset((left,right))
                        if pair in known: continue
                        key=(left,right)
                        if len(candidates[key])<2:
                            snippet=re.sub(r"\s+"," ",b).strip()[:MAX_CONTEXT]
                            candidates[key].append({"file":name,"excerpt":snippet})
    out={
      "generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "status":"ALL_UNVERIFIED_CANDIDATE_LINKS",
      "warning":"Co-occurrence in curated prose is only a discovery signal, NEVER legal incorporation or technical equivalence.",
      "proposed":[{"from":a,"to":b,"suggested_relation":"co_mentioned","confidence":"unverified","human_review_required":True,"evidence":hits} for (a,b),hits in sorted(candidates.items())]
    }
    (D/"regulatory_link_candidates.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Candidate cross-links:",len(out["proposed"]))

if __name__=="__main__": main()
