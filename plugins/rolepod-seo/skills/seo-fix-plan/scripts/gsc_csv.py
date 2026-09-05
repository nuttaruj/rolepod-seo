#!/usr/bin/env python3
"""rolepod-seo — optional Search Console demand data from a manual CSV export (no API, no key).

Usage:
  gsc_csv.py <export.zip | Pages.csv | Queries.csv> [more files…] [--pages sidecar-or-collect.json]
             [--out DIR] [--min-impressions N]

The owner exports Performance → Export from Google Search Console (a zip with
Pages.csv / Queries.csv, or single CSVs). This script never fetches anything;
it reads the file(s) and writes gsc.json + gsc.md into --out (default
.rolepod-seo/gsc-<date>/) with:

  summary        clicks, impressions, average CTR / position across rows
  quick_wins     impressions ≥ 20 and position 4–20 — almost on page 1
  low_ctr_top3   position ≤ 3, CTR < 3 %, impressions ≥ 50 — title / snippet problem
  seen_not_clicked  impressions ≥ 100, clicks ≤ 5 — demand without pull
  top_pages / top_queries  by clicks
  pages_join     when --pages is given: each audited URL with its clicks /
                 impressions / CTR / position, and Search Console pages that
                 the audit never fetched

Thresholds are heuristics, adjustable with --min-impressions. This is an
optional input: an audit is complete without it; never ask for it twice.
Stdlib only.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import sys
import zipfile
from urllib.parse import urlsplit, urlunsplit

VERSION = 1


def norm(url: str) -> str:
    p = urlsplit(url.strip())
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), path, p.query, ""))


def to_num(v: str) -> float:
    v = (v or "").strip().replace("%", "").replace(",", "")
    try:
        return float(v)
    except ValueError:
        return 0.0


def parse_csv_text(text: str, name: str) -> dict:
    """Return {kind: pages|queries|other, rows: [{item, clicks, impressions, ctr, position}]}."""
    text = text.lstrip("﻿")
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return {"kind": "other", "rows": [], "name": name}
    h = [c.strip().lower() for c in header]
    first = h[0] if h else ""
    if "page" in first or "url" in first:
        kind = "pages"
    elif "quer" in first:
        kind = "queries"
    elif name.lower().startswith("pages"):
        kind = "pages"
    elif name.lower().startswith("quer"):
        kind = "queries"
    else:
        kind = "other"

    def col(*names):
        for i, c in enumerate(h):
            if any(n in c for n in names):
                return i
        return None

    ci, ii, ri, pi = col("click"), col("impression"), col("ctr"), col("position")
    rows = []
    for parts in reader:
        if not parts or not parts[0].strip():
            continue
        rows.append({
            "item": parts[0].strip(),
            "clicks": int(to_num(parts[ci])) if ci is not None and ci < len(parts) else 0,
            "impressions": int(to_num(parts[ii])) if ii is not None and ii < len(parts) else 0,
            "ctr": round(to_num(parts[ri]), 2) if ri is not None and ri < len(parts) else 0.0,
            "position": round(to_num(parts[pi]), 1) if pi is not None and pi < len(parts) else 0.0,
        })
    return {"kind": kind, "rows": rows, "name": name}


def load_inputs(paths: list[str]) -> list[dict]:
    tables = []
    for p in paths:
        if p.lower().endswith(".zip"):
            with zipfile.ZipFile(p) as z:
                for info in z.infolist():
                    if info.filename.lower().endswith(".csv"):
                        tables.append(parse_csv_text(z.read(info).decode("utf-8", "replace"), os.path.basename(info.filename)))
        else:
            with open(p, encoding="utf-8-sig") as f:
                tables.append(parse_csv_text(f.read(), os.path.basename(p)))
    return tables


def buckets(rows: list[dict], min_impr: int) -> dict:
    qw = sorted([r for r in rows if r["impressions"] >= max(20, min_impr) and 4 <= r["position"] <= 20], key=lambda r: -r["impressions"])[:15]
    low = sorted([r for r in rows if r["position"] <= 3 and r["ctr"] < 3 and r["impressions"] >= max(50, min_impr)], key=lambda r: -r["impressions"])[:15]
    seen = sorted([r for r in rows if r["impressions"] >= max(100, min_impr) and r["clicks"] <= 5], key=lambda r: -r["impressions"])[:15]
    top = sorted(rows, key=lambda r: -r["clicks"])[:15]
    return {"quick_wins": qw, "low_ctr_top3": low, "seen_not_clicked": seen, "top": top}


def summary(rows: list[dict]) -> dict:
    clicks = sum(r["clicks"] for r in rows)
    impr = sum(r["impressions"] for r in rows)
    pos = [r["position"] for r in rows if r["position"]]
    return {"rows": len(rows), "clicks": clicks, "impressions": impr,
            "ctr": round(clicks / impr * 100, 2) if impr else 0.0,
            "avg_position": round(sum(pos) / len(pos), 1) if pos else 0.0}


def audited_urls(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return [p.get("url") for p in d.get("pages", []) if p.get("url")]


def md_table(title: str, rows: list[dict], label: str) -> str:
    if not rows:
        return f"### {title}\n\nnone\n"
    out = [f"### {title}", "", f"| {label} | clicks | impressions | CTR | position |", "|---|---:|---:|---:|---:|"]
    for r in rows:
        out.append(f"| {r['item']} | {r['clicks']} | {r['impressions']} | {r['ctr']}% | {r['position']} |")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--pages", help="audit sidecar or collect.json to join Search Console pages with audited URLs")
    ap.add_argument("--out")
    ap.add_argument("--min-impressions", type=int, default=0)
    ap.add_argument("--fixed-time", help="ISO timestamp (tests)")
    a = ap.parse_args(argv)
    tables = load_inputs(a.files)
    pages_rows = [r for t in tables if t["kind"] == "pages" for r in t["rows"]]
    query_rows = [r for t in tables if t["kind"] == "queries" for r in t["rows"]]
    if not pages_rows and not query_rows:
        print("no Pages or Queries table found — export Performance → Export from Search Console (zip or CSV)", file=sys.stderr)
        return 2
    now = a.fixed_time or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = a.out or os.path.join(".rolepod-seo", f"gsc-{now[:10].replace('-', '')}")
    os.makedirs(out, exist_ok=True)
    doc = {
        "tool": "rolepod-seo/gsc",
        "version": VERSION,
        "collected_at": now,
        "sources": [{"name": t["name"], "kind": t["kind"], "rows": len(t["rows"])} for t in tables],
        "pages": {"summary": summary(pages_rows), **buckets(pages_rows, a.min_impressions)} if pages_rows else None,
        "queries": {"summary": summary(query_rows), **buckets(query_rows, a.min_impressions)} if query_rows else None,
    }
    if a.pages and pages_rows:
        by_url = {norm(r["item"]): r for r in pages_rows}
        audited = audited_urls(a.pages)
        joined, missing = [], []
        for u in audited:
            r = by_url.get(norm(u))
            joined.append({"url": u, **({k: r[k] for k in ("clicks", "impressions", "ctr", "position")} if r else {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0, "in_search_console": False})})
        aud_norm = {norm(u) for u in audited}
        missing = sorted([r for r in pages_rows if norm(r["item"]) not in aud_norm], key=lambda r: -r["impressions"])[:25]
        doc["pages_join"] = {"audited": joined, "in_search_console_not_audited": missing}
    with open(os.path.join(out, "gsc.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    md = ["# Search Console demand (manual export)", "", f"sources: {', '.join(s['name'] + ' (' + s['kind'] + ', ' + str(s['rows']) + ' rows)' for s in doc['sources'])}", ""]
    for key, label in (("pages", "page"), ("queries", "query")):
        block = doc.get(key)
        if not block:
            continue
        sm = block["summary"]
        md.append(f"## {key.title()} — {sm['clicks']} clicks · {sm['impressions']} impressions · CTR {sm['ctr']}% · avg position {sm['avg_position']}")
        md.append("")
        md.append(md_table("Quick wins — position 4–20 with impressions", block["quick_wins"], label))
        md.append(md_table("Low CTR in the top 3", block["low_ctr_top3"], label))
        md.append(md_table("Seen but not clicked", block["seen_not_clicked"], label))
        md.append(md_table("Top by clicks", block["top"], label))
    if doc.get("pages_join"):
        md.append("## Audited pages in Search Console")
        md.append("")
        md.append("| page | clicks | impressions | CTR | position |")
        md.append("|---|---:|---:|---:|---:|")
        for j in doc["pages_join"]["audited"]:
            md.append(f"| {urlsplit(j['url']).path or '/'} | {j['clicks']} | {j['impressions']} | {j['ctr']}% | {j['position']} |" + ("" if j.get("in_search_console", True) else "  (not in export)"))
        if doc["pages_join"]["in_search_console_not_audited"]:
            md.append("")
            md.append(md_table("In Search Console but not audited (add to the next run)", doc["pages_join"]["in_search_console_not_audited"], "page"))
    with open(os.path.join(out, "gsc.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
