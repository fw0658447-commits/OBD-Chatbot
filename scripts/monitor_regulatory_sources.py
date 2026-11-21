#!/usr/bin/env python3
"""Conservative monitoring of curated automotive regulatory URLs.

No legal interpretation and no bulk scraping. Uses HEAD where possible. Downloads
only explicitly allowlisted official PDFs (never standards or secondary sources).
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/"knowledge"/"source_catalog.json"
STATUS=ROOT/"knowledge"/"source_status.json"
ARCHIVE=ROOT/"knowledge"/"official_documents"
MAX_BYTES=12*1024*1024
APPROVED_ARCHIVE_HOSTS={"unece.org","www.unece.org","eur-lex.europa.eu","www.govinfo.gov","www.ecfr.gov"}
AGENT="OBD-regulatory-source-monitor/1.0 (public metadata; no bulk scraping)"
TIMEOUT=17

def call(url, method="HEAD"):
    req=Request(url, method=method, headers={"User-Agent":AGENT,"Accept":"application/pdf,text/html,application/json,*/*"})
    with urlopen(req, timeout=TIMEOUT) as resp:
        return resp.status, dict(resp.headers), resp.url, resp

def inspect(source):
    out={"id":source["id"],"url":source["url"],"market":source["market"],
         "source_class":source["source_class"],"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    policy=source.get("fetch_policy","link_only")
    if policy=="link_only":
        out.update({"status":"link_only","notice":"No automated retrieval of full text"})
        return out
    try:
        status,headers,final_url,_=call(source["url"],"HEAD")
        out.update({"status":"reachable","http_status":status,"resolved_url":final_url,
                    "etag":headers.get("ETag"),"last_modified":headers.get("Last-Modified"),
                    "content_length":headers.get("Content-Length"),"content_type":headers.get("Content-Type")})
        if policy!="archive_pdf":
            return out
        host=urlparse(final_url).hostname
        if host not in APPROVED_ARCHIVE_HOSTS or not final_url.lower().split("?")[0].endswith(".pdf"):
            out.update({"status":"manual_review","notice":"Archive URL not official/verified PDF"})
            return out
        size=int(headers.get("Content-Length") or 0)
        if size>MAX_BYTES:
            out.update({"status":"too_large"})
            return out
        req=Request(final_url, headers={"User-Agent":AGENT,"Accept":"application/pdf"})
        with urlopen(req,timeout=TIMEOUT) as response:
            raw=response.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES or not raw.startswith(b"%PDF-"):
            out.update({"status":"manual_review","notice":"Not a valid bounded PDF"})
            return out
        ARCHIVE.mkdir(parents=True,exist_ok=True)
        fp=ARCHIVE/(source["id"]+".pdf")
        digest=hashlib.sha256(raw).hexdigest()
        if not fp.exists() or hashlib.sha256(fp.read_bytes()).hexdigest()!=digest:
            fp.write_bytes(raw)
        out.update({"status":"archived","sha256":digest,"archive_path":str(fp.relative_to(ROOT))})
    except (HTTPError,URLError,TimeoutError,ValueError,OSError) as exc:
        out.update({"status":"review_needed","error":str(exc)[:300]})
    return out

def main():
    catalog=json.loads(CATALOG.read_text(encoding="utf-8"))
    today=datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    old={}
    if STATUS.exists():
        old={row["id"]:row for row in json.loads(STATUS.read_text(encoding="utf-8")).get("sources",[])}
    rows=[inspect(s) for s in catalog["sources"]]
    changes=[]
    for row in rows:
        prev=old.get(row["id"])
        if prev and any(row.get(k)!=prev.get(k) for k in ("etag","last_modified","sha256","content_length","status")):
            changes.append(row["id"])
    STATUS.write_text(json.dumps({"checked_date_utc":today,"source_count":len(rows),
        "changed_metadata_sources":changes,"warning":"Change signals require human reading of official amendment and its legal status; absence of change is not proof of no amendments.","sources":rows},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Sources checked: {len(rows)}; possible changes: {len(changes)}; review-needed: {sum(r['status']=='review_needed' for r in rows)}")

if __name__=="__main__":
    main()
