#!/usr/bin/env python3
"""rolepod-seo — render the JSON sidecar as a self-contained HTML report.

Usage:
  render_report.py <sidecar.json> [--out FILE] [--collect collect.json] [--artifact]

Default output: a complete HTML document (inline CSS, no external assets)
next to the sidecar as seo-audit-<host>-<date>.html. A small @media print
block keeps the cover colours and avoids page breaks inside tables.

--artifact writes the fragment form the Claude Code Artifact tool expects
(<title> + <style> + content, no <html>/<head>/<body>), with light/dark
tokens and the host as the title. Same content, same file otherwise.

Stdlib only.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from urllib.parse import urlsplit

PRIORITY_ORDER = {"critical": 0, "high": 1, "quick-win": 2, "medium": 3}
PRIORITY_LABEL = {"critical": "Critical", "high": "High", "quick-win": "Quick win", "medium": "Medium"}
PRIORITY_DOT = {"critical": "🔴", "high": "🟠", "medium": "🟡", "quick-win": "🟢"}
STATUS_LABEL = {"fail": "Fail", "warn": "Warn", "pass": "Pass", "not-assessed": "Not assessed"}
DIM_NAME = {"seo": "SEO", "geo": "GEO", "aeo": "AEO"}
DIM_SUB = {"seo": "classic search", "geo": "generative engines", "aeo": "answer engines"}
GLOSSARY = [
    ("SEO", "Search engine optimisation — how a page is found and ranked in classic web search."),
    ("GEO", "Generative engine optimisation — being cited by AI answer engines such as AI Overviews, ChatGPT search and Perplexity."),
    ("AEO", "Answer engine optimisation — winning the direct-answer slot: featured snippets, People Also Ask, voice assistants."),
    ("E-E-A-T", "Experience, Expertise, Authoritativeness, Trust — the signals engines use to decide whether to trust a source."),
    ("Canonical", "The URL a page declares as its preferred address, so duplicates consolidate to one."),
    ("JSON-LD", "Structured data embedded in the page that names its entities (organisation, article, product, FAQ) for machines."),
    ("PAA", "People Also Ask — the expandable question boxes in search results."),
    ("CWV", "Core Web Vitals — Google's page-experience metrics: LCP, INP, CLS."),
    ("noindex", "A robots directive asking engines not to list the page."),
    ("Sitemap", "An XML list of the URLs a site wants crawled, usually at /sitemap.xml."),
]


def score_status(score) -> tuple[str, str]:
    """Score → (status label, css class). 8–10 On Track, 5–7 Needs Work, 1–4 Critical."""
    if not isinstance(score, int):
        return "Not assessed", "na"
    if score >= 8:
        return "On Track", "good"
    if score >= 5:
        return "Needs Work", "warn"
    return "Critical", "bad"


def esc(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def path_of(url: str) -> str:
    if url == "site":
        return "site"
    p = urlsplit(url)
    return (p.path or "/") + (("?" + p.query) if p.query else "")


CSS = """
:root{--bg:#ffffff;--fg:#1c1c1e;--muted:#5c6370;--card:#f5f6f8;--line:#e1e3e8;--navy:#1f3a5f;--navy-fg:#ffffff;
--good:#1e8e3e;--good-bg:#e6f4ea;--warn:#b26a00;--warn-bg:#fff4e0;--bad:#c5221f;--bad-bg:#fce8e6;--na:#5c6370;--na-bg:#eceef1;
--p-critical:#c5221f;--p-high:#e8710a;--p-medium:#b8860b;--p-quick:#1e8e3e}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#121417;--fg:#e8eaed;--muted:#9aa0a6;--card:#1c1f24;--line:#2b2f36;
--good:#5bd37a;--good-bg:#12301c;--warn:#f0b04a;--warn-bg:#3a2a0e;--bad:#ff7b72;--bad-bg:#3d1613;--na:#9aa0a6;--na-bg:#23262c}}
:root[data-theme="dark"]{--bg:#121417;--fg:#e8eaed;--muted:#9aa0a6;--card:#1c1f24;--line:#2b2f36;
--good:#5bd37a;--good-bg:#12301c;--warn:#f0b04a;--warn-bg:#3a2a0e;--bad:#ff7b72;--bad-bg:#3d1613;--na:#9aa0a6;--na-bg:#23262c}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px 48px}
.cover{background:var(--navy);color:var(--navy-fg);padding:40px 24px 32px;margin:0 -24px 32px}
.cover h1{margin:0 0 4px;font-size:30px;font-weight:700;letter-spacing:.2px;text-wrap:balance}
.cover .meta{opacity:.85;margin:0 0 24px;font-size:14px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px}
.card{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.18);border-radius:12px;padding:16px 18px}
.card .dim{font-size:13px;text-transform:uppercase;letter-spacing:.8px;opacity:.85}
.card .sub{font-size:12px;opacity:.7}
.card .score{font-size:40px;font-weight:700;line-height:1.1;margin:6px 0 2px;font-variant-numeric:tabular-nums}
.card .score small{font-size:16px;font-weight:400;opacity:.7}
.card .status{display:inline-block;margin-top:6px;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600}
.card.good .status{background:var(--good-bg);color:var(--good)}
.card.warn .status{background:var(--warn-bg);color:var(--warn)}
.card.bad .status{background:var(--bad-bg);color:var(--bad)}
.card.na .status{background:var(--na-bg);color:var(--na)}
.card .drivers{margin:10px 0 0;padding-left:18px;font-size:13px;opacity:.9}
h2{font-size:20px;margin:36px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--line);text-wrap:balance}
h3{font-size:16px;margin:24px 0 8px}
p.lead{font-size:16px}
.muted{color:var(--muted)}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:var(--card);font-weight:600;white-space:nowrap}
tr:last-child td{border-bottom:0}
td.mono,code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px}
.chip{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.chip.fail{background:var(--bad-bg);color:var(--bad)}
.chip.warn{background:var(--warn-bg);color:var(--warn)}
.chip.pass{background:var(--good-bg);color:var(--good)}
.chip.not-assessed,.chip.info{background:var(--na-bg);color:var(--na)}
.chip.p-critical{background:var(--p-critical);color:#fff}
.chip.p-high{background:var(--p-high);color:#fff}
.chip.p-medium{background:var(--p-medium);color:#fff}
.chip.p-quick-win{background:var(--p-quick);color:#fff}
.sev{font-size:12px;color:var(--muted)}
ul.plain{padding-left:20px}
dl.gloss dt{font-weight:600;margin-top:8px}
dl.gloss dd{margin:0 0 4px}
.foot{margin-top:40px;font-size:12px;color:var(--muted);border-top:1px solid var(--line);padding-top:12px}
@page{margin:16mm}
@media print{
  body{font-size:12px}
  .cover{-webkit-print-color-adjust:exact;print-color-adjust:exact;margin:0 0 24px;border-radius:8px}
  .card,.chip{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  section,table,tr{page-break-inside:avoid;break-inside:avoid}
  h2{page-break-after:avoid;break-after:avoid}
  .tablewrap{overflow:visible;border:0}
  a{color:inherit;text-decoration:none}
}
@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}
"""


def render(doc: dict, collect: dict | None = None) -> tuple[str, str]:
    """Return (title, body_html). body_html is the content inside .wrap."""
    site = doc.get("site", {})
    host = site.get("host", "site")
    mode = site.get("mode", "quick")
    date = (doc.get("generated_at") or "")[:10]
    col = doc.get("collection", {})
    tiers = col.get("tiers", {})
    scores = doc.get("scores", {})
    findings = doc.get("findings", [])
    facts = {}
    if collect:
        for p in collect.get("pages", []):
            facts[p.get("url")] = p

    out: list[str] = []
    # cover
    tier_txt = "Tier A fetch" + (" · Tier B rolepod-uiproof" if tiers.get("b") else "") + (" · connectors" if tiers.get("c") else "")
    out.append('<header class="cover">')
    out.append(f"<h1>{esc(host)}</h1>")
    out.append(f'<p class="meta">SEO · GEO · AEO audit — {esc(mode)} mode · {esc(date)} · {esc(col.get("pages_fetched", "?"))}/{esc(col.get("pages_selected", "?"))} pages fetched · {esc(tier_txt)}</p>')
    out.append('<div class="cards">')
    for d in ("seo", "geo", "aeo"):
        s = scores.get(d, {})
        score = s.get("score")
        label, cls = score_status(score)
        if s.get("band") == "not-assessed":
            label, cls = "Not assessed", "na"
        score_txt = f"{score}<small>/10</small>" if isinstance(score, int) else "—"
        drivers = "".join(f"<li>{esc(x)}</li>" for x in s.get("drivers", [])[:3])
        out.append(f'<div class="card {cls}"><div class="dim">{DIM_NAME[d]}</div><div class="sub">{DIM_SUB[d]}</div>'
                   f'<div class="score">{score_txt}</div><span class="status">{esc(label)}</span>'
                   f'<div class="sub">band: {esc(s.get("band", "—"))}</div>'
                   + (f'<ul class="drivers">{drivers}</ul>' if drivers else "") + "</div>")
    out.append("</div></header>")

    # executive summary
    out.append('<section id="summary"><h2>Executive summary</h2>')
    summary = doc.get("summary")
    if summary:
        out.append(f'<p class="lead">{esc(summary)}</p>')
    else:
        parts = []
        for d in ("seo", "geo", "aeo"):
            s = scores.get(d, {})
            lab, _ = score_status(s.get("score"))
            parts.append(f"{DIM_NAME[d]} {s.get('score', '—')}/10 ({lab})")
        top = [f for f in findings if f.get("status") in ("fail", "warn")]
        top.sort(key=lambda f: (PRIORITY_ORDER.get(f.get("priority"), 9)))
        first = f" First fix: {top[0].get('fix')} ({path_of(top[0].get('page', ''))})." if top else ""
        out.append(f'<p class="lead">{esc(", ".join(parts))}.{esc(first)}</p>')
    out.append("</section>")

    # pages
    pages = doc.get("pages", [])
    if pages:
        out.append('<section id="pages"><h2>Pages audited</h2><div class="tablewrap"><table><thead><tr><th>Page</th><th>Role</th><th>Status</th><th>In sitemap</th>'
                   + ("<th>Title</th><th>Words</th><th>Schema</th>" if facts else "") + "</tr></thead><tbody>")
        for p in pages:
            f = facts.get(p.get("url"), {})
            st = p.get("status")
            st_cls = "pass" if st == 200 else "fail"
            row = (f'<tr><td class="mono">{esc(path_of(p.get("url", "")))}</td><td>{esc(p.get("role", ""))}</td>'
                   f'<td><span class="chip {st_cls}">{esc(st)}</span></td><td>{"yes" if p.get("in_sitemap") else "no"}</td>')
            if facts:
                row += (f'<td>{esc(f.get("title", ""))}</td><td>{esc(f.get("word_count", ""))}</td>'
                        f'<td class="mono">{esc(", ".join(f.get("schema_types", [])) or "—")}</td>')
            out.append(row + "</tr>")
        out.append("</tbody></table></div></section>")

    # findings per dimension
    for d in ("seo", "geo", "aeo"):
        rows = [f for f in findings if f.get("dimension") == d and f.get("status") != "not-assessed"]
        out.append(f'<section id="{d}"><h2>{DIM_NAME[d]} findings <span class="muted">— {DIM_SUB[d]}</span></h2>')
        if not rows:
            out.append('<p class="muted">No findings recorded for this dimension.</p></section>')
            continue
        out.append('<div class="tablewrap"><table><thead><tr><th>Signal</th><th>Evidence</th><th>Fix</th><th>Page</th><th>Status</th></tr></thead><tbody>')
        order = {"fail": 0, "warn": 1, "pass": 2}
        for f in sorted(rows, key=lambda f: (order.get(f.get("status"), 3), PRIORITY_ORDER.get(f.get("priority"), 9))):
            st = f.get("status", "")
            out.append(f'<tr><td><strong>{esc(f.get("signal"))}</strong><br><span class="sev">{esc(f.get("severity"))}</span></td>'
                       f'<td>{esc(f.get("evidence"))}</td><td>{esc(f.get("fix"))}</td>'
                       f'<td class="mono">{esc(path_of(f.get("page", "")))}</td>'
                       f'<td><span class="chip {esc(st)}">{esc(STATUS_LABEL.get(st, st))}</span></td></tr>')
        out.append("</tbody></table></div></section>")

    # priority matrix
    matrix = [f for f in findings if f.get("status") in ("fail", "warn")]
    matrix.sort(key=lambda f: (PRIORITY_ORDER.get(f.get("priority"), 9), {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(f.get("severity"), 4)))
    out.append('<section id="matrix"><h2>Priority matrix</h2>')
    if matrix:
        out.append('<div class="tablewrap"><table><thead><tr><th>Priority</th><th>Issue</th><th>Dim</th><th>Effort</th><th>Impact</th><th>Owner</th><th>Exact change</th></tr></thead><tbody>')
        for f in matrix:
            pr = f.get("priority", "medium")
            out.append(f'<tr><td><span class="chip p-{esc(pr)}">{esc(PRIORITY_LABEL.get(pr, pr))}</span></td>'
                       f'<td>{esc(f.get("signal"))} · <span class="mono">{esc(path_of(f.get("page", "")))}</span></td>'
                       f'<td>{esc(DIM_NAME.get(f.get("dimension"), f.get("dimension")))}</td><td>{esc(f.get("effort"))}</td><td>{esc(f.get("impact"))}</td>'
                       f'<td>{esc(f.get("owner"))}</td><td>{esc(f.get("fix"))}</td></tr>')
        out.append("</tbody></table></div>")
    else:
        out.append('<p class="muted">Nothing to fix — every check passed or was not assessed.</p>')
    out.append("</section>")

    # decisions
    decisions = [f for f in findings if f.get("severity") == "info" and f.get("owner") == "human"]
    if decisions:
        out.append('<section id="decisions"><h2>Decisions for the owner</h2><ul class="plain">')
        for f in decisions:
            out.append(f"<li><strong>{esc(f.get('signal'))}</strong> — {esc(f.get('evidence'))}<br>{esc(f.get('fix'))}</li>")
        out.append("</ul></section>")

    # strengths
    strengths = doc.get("strengths", [])
    out.append('<section id="strengths"><h2>What\'s working</h2>')
    if strengths:
        out.append('<ul class="plain">' + "".join(
            f"<li><strong>{esc(s.get('signal'))}</strong> · <span class=\"mono\">{esc(path_of(s.get('page', '')))}</span> — {esc(s.get('evidence'))}</li>" for s in strengths) + "</ul>")
    else:
        out.append('<p class="muted">No strengths recorded.</p>')
    out.append("</section>")

    # not assessed
    na = doc.get("not_assessed", [])
    if na:
        out.append('<section id="not-assessed"><h2>Not assessed</h2><div class="tablewrap"><table><thead><tr><th>Signal</th><th>Needs</th><th>Installed</th></tr></thead><tbody>')
        for n in na:
            out.append(f"<tr><td>{esc(n.get('signal'))}</td><td>{esc(n.get('needs'))}</td><td>{'yes' if n.get('installed') else 'no'}</td></tr>")
        out.append("</tbody></table></div></section>")

    # glossary
    if mode == "full":
        out.append('<section id="glossary"><h2>Glossary</h2><dl class="gloss">' + "".join(f"<dt>{esc(t)}</dt><dd>{esc(d)}</dd>" for t, d in GLOSSARY) + "</dl></section>")

    out.append(f'<p class="foot">Generated {esc(doc.get("generated_at", ""))} · schema {esc(doc.get("schema", ""))} v{esc(doc.get("schema_version", ""))} · '
               f'collector: {esc(", ".join(col.get("tools", [])))}</p>')
    return host, "\n".join(out)


def to_document(title: str, body: str) -> str:
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<title>{esc(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n<div class=\"wrap\">\n{body}\n</div>\n</body>\n</html>\n")


def to_artifact(title: str, body: str) -> str:
    return f"<title>{esc(title)}</title>\n<style>{CSS}</style>\n<div class=\"wrap\">\n{body}\n</div>\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sidecar")
    ap.add_argument("--out")
    ap.add_argument("--collect", help="collector collect.json to add title / words / schema to the pages table")
    ap.add_argument("--artifact", action="store_true", help="fragment form for the Claude Code Artifact tool")
    a = ap.parse_args(argv)
    with open(a.sidecar, encoding="utf-8") as f:
        doc = json.load(f)
    collect = None
    if a.collect:
        with open(a.collect, encoding="utf-8") as f:
            collect = json.load(f)
    title, body = render(doc, collect)
    text = to_artifact(title, body) if a.artifact else to_document(title, body)
    out = a.out
    if not out:
        base = re.sub(r"\.json$", "", a.sidecar)
        out = base + (".artifact.html" if a.artifact else ".html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
