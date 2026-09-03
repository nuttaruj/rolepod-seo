#!/usr/bin/env python3
"""rolepod-seo — render the JSON sidecar as a self-contained HTML report.

Usage:
  render_report.py <sidecar.json> [--out FILE] [--collect collect.json] [--artifact]
                   [--previous older-sidecar.json]

--previous adds a "Since last audit" section (score deltas, fixed / new /
still-open findings matched by id) and prints the same one-liner to stderr
for the chat summary. The roadmap (week 1 / weeks 2–3 / month 2 / ongoing),
the quick-wins block, the per-page finding counts and the per-dimension
status counts are all derived from the sidecar — no extra input.

Default output: a complete HTML document (inline CSS, no external assets)
next to the sidecar as seo-audit-<host>-<date>.html. A "Save as PDF"
button calls window.print() — the browser's print dialog makes the PDF;
there is no PDF library, no download link, no automation. The @media print
block hides the button, forces light colours, keeps card / chip colours and
breaks pages before the findings and the matrix.

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
PHASES = [
    ("Week 1 — unblock", "critical", "Crawl / indexation blockers and anything that hides money pages."),
    ("Weeks 2–3 — high impact and quick wins", "high+quick-win", "Fixes with clear upside; the quick wins are one-file changes."),
    ("Month 2 — content and trust", "medium", "Copy, briefs, E-E-A-T, schema breadth."),
    ("Ongoing — decide, measure, re-audit", "ongoing", "Owner decisions, what needs a tool to prove, leading indicators."),
]
# signal name → group, first match wins; the model writes free-text signals, so match by keyword
SIGNAL_GROUPS = [
    ("schema", r"schema|json-?ld|structured|breadcrumb|organization|local-?business|faqpage|speakable|sameas"),
    ("technical", r"title|description|h1|heading|canonical|robots|noindex|sitemap|redirect|https|hsts|mixed|viewport|lang|charset|url|favicon|og\b|open-?graph|twitter|hreflang|inlink|(?<!content-)depth|orphan|link|crawl|index|security|header|status|404|5xx"),
    ("content", r"content|word|thin|duplicate|topic|fresh|date|scann|readab|image|alt|paragraph"),
    ("trust", r"author|about|contact|nap|trust|proof|testimonial|entity|citation|fact|claim|source|bot|llms|render|agent|e-?e-?a-?t|brand"),
    ("answer", r"answer|question|faq|definition|step|how-?to|table|compar|voice|hours|service-?area|paa|toc|jump"),
]


def signal_group(signal: str) -> str:
    s_ = (signal or "").lower()
    for group, rx in SIGNAL_GROUPS:
        if re.search(rx, s_):
            return group
    return "other"


def group_counts(findings: list[dict], dim: str) -> list[tuple[str, dict[str, int]]]:
    """[(group, {fail, warn, pass}), …] for one dimension, in SIGNAL_GROUPS order, empty groups dropped."""
    acc: dict[str, dict[str, int]] = {}
    for f in findings:
        if f.get("dimension") != dim or f.get("status") not in ("fail", "warn", "pass"):
            continue
        g = signal_group(f.get("signal", ""))
        acc.setdefault(g, {"fail": 0, "warn": 0, "pass": 0})[f["status"]] += 1
    order = [g for g, _ in SIGNAL_GROUPS] + ["other"]
    return [(g, acc[g]) for g in order if g in acc]


def group_line(findings: list[dict], dim: str) -> str:
    parts = []
    for g, c in group_counts(findings, dim):
        bits = [f"{c[k]} {k}" for k in ("fail", "warn", "pass") if c[k]]
        parts.append(f"<strong>{esc(g)}</strong> — {', '.join(bits)}")
    return " · ".join(parts)


# Signals with no effect on Google Search when the finding does not say otherwise.
NO_EFFECT_RE = re.compile(r"faq-?page|faq-?schema|how-?to|llms|speakable", re.I)
EFFECT_ORDER = {"direct": 0, "indirect": 1, "none": 2}
EFFECT_LABEL = {"direct": "affects Google Search", "indirect": "indirect / AI engines", "none": "no effect on Google Search"}


def effect_of(f: dict) -> str:
    """Explicit findings[].seo_effect wins; otherwise infer 'none' for retired / ignored signals, else 'direct'."""
    e = f.get("seo_effect")
    if e in EFFECT_ORDER:
        return e
    return "none" if NO_EFFECT_RE.search(f.get("signal", "") or "") else "direct"


def effective(findings: list[dict]) -> list[dict]:
    return [f for f in findings if effect_of(f) != "none"]


SITE_TYPE_LABEL = {"saas": "SaaS / software", "ecommerce": "e-commerce", "local": "local service", "publisher": "publisher / blog", "agency": "agency / services", "unknown": "not detected"}
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
.chip.not-assessed,.chip.info,.chip.none{background:var(--na-bg);color:var(--na)}
.chip.none{border:1px dashed var(--na)}
tr.none td{opacity:.7}
.chip.p-critical{background:var(--p-critical);color:#fff}
.chip.p-high{background:var(--p-high);color:#fff}
.chip.p-medium{background:var(--p-medium);color:#fff}
.chip.p-quick-win{background:var(--p-quick);color:#fff}
.sev{font-size:12px;color:var(--muted)}
ul.plain{padding-left:20px}
dl.gloss dt{font-weight:600;margin-top:8px}
dl.gloss dd{margin:0 0 4px}
.foot{margin-top:40px;font-size:12px;color:var(--muted);border-top:1px solid var(--line);padding-top:12px}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}
.box{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.box h3{margin:0 0 8px;font-size:14px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted)}
.box ul{margin:0;padding-left:18px}
.counts{font-size:12px;opacity:.85;margin-top:8px}
.counts b{font-weight:600}
.counts.groups{opacity:.75;font-size:11px;line-height:1.5}
.delta{font-size:13px;color:var(--muted)}
.delta .up{color:var(--good);font-weight:600}.delta .down{color:var(--bad);font-weight:600}
.phase{margin:14px 0 0}
.phase h3{margin:0 0 4px}
.phase p.muted{margin:0 0 6px;font-size:13px}
.toolbar{display:flex;justify-content:flex-end;align-items:center;gap:12px;padding:12px 0 0;font-size:13px;color:var(--muted)}
.print-btn{appearance:none;border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:8px;padding:7px 14px;font:inherit;font-weight:600;cursor:pointer}
.print-btn:hover{border-color:var(--navy)}
.print-btn:focus-visible{outline:2px solid var(--navy);outline-offset:2px}
@page{margin:16mm}
@media print{
  :root,:root[data-theme="dark"],:root:not([data-theme="light"]){--bg:#ffffff;--fg:#1c1c1e;--muted:#5c6370;--card:#f5f6f8;--line:#e1e3e8;
    --good:#1e8e3e;--good-bg:#e6f4ea;--warn:#b26a00;--warn-bg:#fff4e0;--bad:#c5221f;--bad-bg:#fce8e6;--na:#5c6370;--na-bg:#eceef1}
  body{font-size:12px;background:#fff;color:#1c1c1e}
  .no-print,.toolbar{display:none!important}
  .cover,.card,.chip,.card .status{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .cover{margin:0 0 24px;border-radius:8px}
  #seo,#matrix{break-before:page;page-break-before:always}
  tr,.card{page-break-inside:avoid;break-inside:avoid}
  h2,h3{page-break-after:avoid;break-after:avoid}
  .tablewrap{overflow:visible;border:0}
  a{color:inherit;text-decoration:none}
}
@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}
"""


def status_counts(findings: list[dict], dim: str) -> dict[str, int]:
    c = {"fail": 0, "warn": 0, "pass": 0}
    for f in findings:
        if f.get("dimension") == dim and f.get("status") in c:
            c[f["status"]] += 1
    return c


def open_ids(doc: dict) -> dict[str, dict]:
    return {f["id"]: f for f in doc.get("findings", []) if f.get("status") in ("fail", "warn") and f.get("id")}


def compare(doc: dict, prev: dict) -> dict:
    cur, old = open_ids(doc), open_ids(prev)
    return {
        "previous_date": (prev.get("generated_at") or "")[:10],
        "scores": {d: (prev.get("scores", {}).get(d, {}).get("score"), doc.get("scores", {}).get(d, {}).get("score")) for d in ("seo", "geo", "aeo")},
        "fixed": [old[i] for i in old if i not in cur],
        "new": [cur[i] for i in cur if i not in old],
        "still": [cur[i] for i in cur if i in old],
    }


def compare_line(cmp: dict) -> str:
    parts = []
    for d, (a, b) in cmp["scores"].items():
        if isinstance(a, int) and isinstance(b, int):
            parts.append(f"{DIM_NAME[d]} {a}→{b}")
    return f"since {cmp['previous_date']}: " + ", ".join(parts) + f" · fixed {len(cmp['fixed'])} · new {len(cmp['new'])} · still open {len(cmp['still'])}"


def render(doc: dict, collect: dict | None = None, prev: dict | None = None) -> tuple[str, str]:
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
    out.append('<div class="toolbar no-print"><span>Save this report as a PDF with the browser\'s print dialog</span>'
               '<button type="button" class="print-btn" onclick="window.print()">Save as PDF</button>'
               '<span>or press ⌘P / Ctrl+P → Save as PDF</span></div>')
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
        c = status_counts(effective(findings), d)
        n_opt = sum(1 for f in findings if f.get("dimension") == d and effect_of(f) == "none" and f.get("status") in ("fail", "warn"))
        out.append(f'<div class="card {cls}"><div class="dim">{DIM_NAME[d]}</div><div class="sub">{DIM_SUB[d]}</div>'
                   f'<div class="score">{score_txt}</div><span class="status">{esc(label)}</span>'
                   f'<div class="sub">band: {esc(s.get("band", "—"))}</div>'
                   f'<div class="counts"><b>{c["fail"]}</b> fail · <b>{c["warn"]}</b> warn · <b>{c["pass"]}</b> pass' + (f' · {n_opt} optional (no Google effect)' if n_opt else "") + '</div>'
                   + (f'<div class="counts groups">{group_line(effective(findings), d)}</div>' if group_counts(effective(findings), d) else "")
                   + (f'<ul class="drivers">{drivers}</ul>' if drivers else "") + "</div>")
    out.append("</div></header>")

    # executive summary
    out.append('<section id="summary"><h2>Executive summary</h2>')
    st = site.get("site_type") or {}
    if isinstance(st, dict) and st.get("type"):
        sig = "; ".join(v if isinstance(v, str) else ", ".join(v) for v in (st.get("signals", {}).get(st["type"], []) or [])[:3])
        out.append(f'<p class="muted">Site type: <strong>{esc(SITE_TYPE_LABEL.get(st["type"], st["type"]))}</strong> ({esc(st.get("confidence", ""))} confidence' + (f" — {esc(sig)}" if sig else "") + ")</p>")
    elif isinstance(st, str) and st:
        out.append(f'<p class="muted">Site type: <strong>{esc(SITE_TYPE_LABEL.get(st, st))}</strong></p>')
    summary = doc.get("summary")
    if summary:
        out.append(f'<p class="lead">{esc(summary)}</p>')
    else:
        parts = []
        for d in ("seo", "geo", "aeo"):
            s = scores.get(d, {})
            lab, _ = score_status(s.get("score"))
            parts.append(f"{DIM_NAME[d]} {s.get('score', '—')}/10 ({lab})")
        top = [f for f in effective(findings) if f.get("status") in ("fail", "warn")]
        top.sort(key=lambda f: (PRIORITY_ORDER.get(f.get("priority"), 9)))
        first = f" First fix: {top[0].get('fix')} ({path_of(top[0].get('page', ''))})." if top else ""
        out.append(f'<p class="lead">{esc(", ".join(parts))}.{esc(first)}</p>')
    crit = [f for f in effective(findings) if f.get("priority") == "critical" and f.get("status") in ("fail", "warn")][:5]
    quick = [f for f in effective(findings) if f.get("priority") == "quick-win" and f.get("status") in ("fail", "warn")][:5]
    out.append('<div class="two">')
    out.append('<div class="box"><h3>Fix first</h3>' + ('<ul>' + "".join(f'<li>{esc(f.get("signal"))} · <span class="mono">{esc(path_of(f.get("page", "")))}</span> — {esc(f.get("fix"))}</li>' for f in crit) + '</ul>' if crit else '<p class="muted">No critical items.</p>') + '</div>')
    out.append('<div class="box"><h3>Quick wins</h3>' + ('<ul>' + "".join(f'<li>{esc(f.get("signal"))} · <span class="mono">{esc(path_of(f.get("page", "")))}</span> — {esc(f.get("fix"))}</li>' for f in quick) + '</ul>' if quick else '<p class="muted">No quick wins tagged.</p>') + '</div>')
    out.append('</div>')
    out.append("</section>")

    if prev:
        cmp = compare(doc, prev)
        out.append(f'<section id="since"><h2>Since last audit <span class="muted">— {esc(cmp["previous_date"])}</span></h2><p class="delta">')
        bits = []
        for d, (a, b) in cmp["scores"].items():
            if isinstance(a, int) and isinstance(b, int):
                cls_ = "up" if b > a else "down" if b < a else ""
                bits.append(f'{DIM_NAME[d]} {a} → <span class="{cls_}">{b}</span>')
        out.append(" · ".join(bits) + f' · fixed <strong>{len(cmp["fixed"])}</strong> · new <strong>{len(cmp["new"])}</strong> · still open <strong>{len(cmp["still"])}</strong></p>')
        out.append('<div class="two">')
        for label, items in (("Fixed", cmp["fixed"]), ("New", cmp["new"])):
            out.append(f'<div class="box"><h3>{label}</h3>' + ('<ul>' + "".join(f'<li>{esc(f.get("signal"))} · <span class="mono">{esc(path_of(f.get("page", "")))}</span></li>' for f in items[:12]) + '</ul>' if items else '<p class="muted">none</p>') + '</div>')
        out.append('</div></section>')

    # pages
    pages = doc.get("pages", [])
    per_page: dict[str, dict[str, int]] = {}
    for f in effective(findings):
        if f.get("status") in ("fail", "warn"):
            per_page.setdefault(f.get("page", ""), {"fail": 0, "warn": 0})[f["status"]] += 1
    if pages:
        out.append('<section id="pages"><h2>Pages audited</h2><div class="tablewrap"><table><thead><tr><th>Page</th><th>Role</th><th>Status</th><th>In sitemap</th><th>Findings</th>'
                   + ("<th>Title</th><th>Words</th><th>Links in / depth</th><th>Schema</th>" if facts else "") + "</tr></thead><tbody>")
        for p in pages:
            f = facts.get(p.get("url"), {})
            st = p.get("status")
            st_cls = "pass" if st == 200 else "fail"
            pc = per_page.get(p.get("url", ""), {})
            cnt = (f'<span class="chip fail">{pc["fail"]} fail</span> ' if pc.get("fail") else "") + (f'<span class="chip warn">{pc["warn"]} warn</span>' if pc.get("warn") else "") or '<span class="muted">—</span>'
            row = (f'<tr><td class="mono">{esc(path_of(p.get("url", "")))}</td><td>{esc(p.get("role", ""))}</td>'
                   f'<td><span class="chip {st_cls}">{esc(st)}</span></td><td>{"yes" if p.get("in_sitemap") else "no"}</td><td>{cnt}</td>')
            if facts:
                dep = f.get("depth")
                row += (f'<td>{esc(f.get("title", ""))}</td><td>{esc(f.get("word_count", ""))}</td>'
                        f'<td>{esc(f.get("inlinks", "—"))} / {"—" if dep is None else esc(dep)}</td>'
                        f'<td class="mono">{esc(", ".join(f.get("schema_types", [])) or "—")}</td>')
            out.append(row + "</tr>")
        out.append("</tbody></table></div></section>")

    # findings per dimension
    for d in ("seo", "geo", "aeo"):
        rows = [f for f in findings if f.get("dimension") == d and f.get("status") != "not-assessed"]
        c = status_counts(effective(findings), d)
        out.append(f'<section id="{d}"><h2>{DIM_NAME[d]} findings <span class="muted">— {DIM_SUB[d]} · {c["fail"]} fail · {c["warn"]} warn · {c["pass"]} pass</span></h2>')
        if group_counts(effective(findings), d):
            out.append(f'<p class="muted">By group: {group_line(effective(findings), d)}</p>')
        if not rows:
            out.append('<p class="muted">No findings recorded for this dimension.</p></section>')
            continue
        out.append('<div class="tablewrap"><table><thead><tr><th>Signal</th><th>Evidence</th><th>Fix</th><th>Page</th><th>Status</th></tr></thead><tbody>')
        order = {"fail": 0, "warn": 1, "pass": 2}
        for f in sorted(rows, key=lambda f: (EFFECT_ORDER[effect_of(f)], order.get(f.get("status"), 3), PRIORITY_ORDER.get(f.get("priority"), 9))):
            st = f.get("status", "")
            eff = effect_of(f)
            tag = f'<br><span class="chip none">{EFFECT_LABEL["none"]}</span>' if eff == "none" else (f'<br><span class="sev">{EFFECT_LABEL["indirect"]}</span>' if eff == "indirect" else "")
            out.append(f'<tr class="{eff}"><td><strong>{esc(f.get("signal"))}</strong><br><span class="sev">{esc(f.get("severity"))}</span>{tag}</td>'
                       f'<td>{esc(f.get("evidence"))}</td><td>{esc(f.get("fix"))}</td>'
                       f'<td class="mono">{esc(path_of(f.get("page", "")))}</td>'
                       f'<td><span class="chip {esc(st)}">{esc(STATUS_LABEL.get(st, st))}</span></td></tr>')
        out.append("</tbody></table></div></section>")

    # priority matrix
    matrix = [f for f in effective(findings) if f.get("status") in ("fail", "warn")]
    optional = [f for f in findings if effect_of(f) == "none" and f.get("status") in ("fail", "warn")]
    matrix.sort(key=lambda f: (PRIORITY_ORDER.get(f.get("priority"), 9), {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(f.get("severity"), 4)))
    out.append('<section id="matrix"><h2>Priority matrix</h2>')
    has_verify = any(f.get("verify") for f in matrix)
    if matrix:
        out.append('<div class="tablewrap"><table><thead><tr><th>Priority</th><th>Issue</th><th>Dim</th><th>Effort</th><th>Impact</th><th>Owner</th><th>Exact change</th>' + ("<th>Verify</th>" if has_verify else "") + '</tr></thead><tbody>')
        for f in matrix:
            pr = f.get("priority", "medium")
            out.append(f'<tr><td><span class="chip p-{esc(pr)}">{esc(PRIORITY_LABEL.get(pr, pr))}</span></td>'
                       f'<td>{esc(f.get("signal"))} · <span class="mono">{esc(path_of(f.get("page", "")))}</span></td>'
                       f'<td>{esc(DIM_NAME.get(f.get("dimension"), f.get("dimension")))}</td><td>{esc(f.get("effort"))}</td><td>{esc(f.get("impact"))}</td>'
                       f'<td>{esc(f.get("owner"))}</td><td>{esc(f.get("fix"))}</td>' + (f'<td>{esc(f.get("verify", ""))}</td>' if has_verify else "") + '</tr>')
        out.append("</tbody></table></div>")

    else:
        out.append('<p class="muted">Nothing to fix — every check passed or was not assessed.</p>')
    out.append("</section>")

    # roadmap derived from priorities
    out.append('<section id="roadmap"><h2>Roadmap</h2>')
    na_items = doc.get("not_assessed", [])
    decisions_ = [f for f in findings if f.get("severity") == "info" and f.get("owner") == "human"]
    leading = [f for f in effective(findings) if f.get("leading_indicator")]
    for title, key, blurb in PHASES:
        out.append(f'<div class="phase"><h3>{esc(title)}</h3><p class="muted">{esc(blurb)}</p>')
        if key == "ongoing":
            items = [f'<li>Decide: {esc(f.get("signal"))} — {esc(f.get("fix"))}</li>' for f in decisions_]
            items += [f'<li>Prove with a tool: {esc(n.get("signal"))} — needs {esc(n.get("needs"))}</li>' for n in na_items]
            items += [f'<li>Watch: {esc(f.get("leading_indicator"))} <span class="muted">({esc(f.get("signal"))})</span></li>' for f in leading]
            items.append("<li>Re-run the audit; the next report diffs against this one by finding id.</li>")
        else:
            wanted = set(key.split("+"))
            items = [f'<li><span class="chip p-{esc(f.get("priority"))}">{esc(PRIORITY_LABEL.get(f.get("priority"), ""))}</span> {esc(f.get("signal"))} · <span class="mono">{esc(path_of(f.get("page", "")))}</span> — {esc(f.get("owner"))}</li>' for f in matrix if f.get("priority") in wanted]
        out.append(('<ul class="plain">' + "".join(items) + "</ul>") if items else '<p class="muted">nothing in this phase</p>')
        out.append("</div>")
    out.append("</section>")

    # optional — no effect on Google Search, listed last on purpose
    if optional:
        out.append('<section id="optional"><h2>No effect on Google Search <span class="muted">— optional, listed last on purpose</span></h2>'
                   '<p class="muted">These signals do not change crawling, indexing or ranking in Google Search (rich results retired, or the file is ignored). They may still help other answer engines. Do nothing here before the sections above are clean.</p>'
                   '<div class="tablewrap"><table><thead><tr><th>Signal</th><th>Why no effect</th><th>Optional change</th><th>Page</th></tr></thead><tbody>')
        for f in optional:
            out.append(f'<tr class="none"><td><strong>{esc(f.get("signal"))}</strong> <span class="chip none">{EFFECT_LABEL["none"]}</span></td>'
                       f'<td>{esc(f.get("evidence"))}</td><td>{esc(f.get("fix"))}</td><td class="mono">{esc(path_of(f.get("page", "")))}</td></tr>')
        out.append("</tbody></table></div></section>")

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

    # methodology
    tiers_used = ["plain fetch (collect.py)"] + (["rolepod-uiproof rendered DOM / CWV / a11y"] if tiers.get("b") else []) + (["connectors"] if tiers.get("c") else [])
    out.append('<section id="method"><h2>How to read the scores</h2>'
               '<p>Each dimension is scored 1–10 from the checklist hit-rate, weighted by page role (home and money pages count more than posts, posts more than utility pages). '
               'Bands: 1–3 critical · 4–5 below baseline · 6–7 solid · 8–9 strong · 10 model. Cover cards colour by score: 8–10 On Track, 5–7 Needs Work, 1–4 Critical. '
               'Every finding quotes the page and the tag; "missing" is claimed only after every fetched page was checked; anything the collection tier could not see is listed under Not assessed with the tool that would prove it. '
               f'Data tiers used: {esc(", ".join(tiers_used))}. Findings keep a stable id so the next audit can diff against this one. '
               'Findings are ordered by effect: what changes Google Search first, then indirect / AI-engine signals, then items marked "no effect on Google Search", which never enter the priority matrix or the roadmap.</p></section>')

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
    ap.add_argument("--previous", help="older sidecar for the same host — adds the Since-last-audit section")
    a = ap.parse_args(argv)
    with open(a.sidecar, encoding="utf-8") as f:
        doc = json.load(f)
    collect = None
    if a.collect:
        with open(a.collect, encoding="utf-8") as f:
            collect = json.load(f)
    prev = None
    if a.previous:
        with open(a.previous, encoding="utf-8") as f:
            prev = json.load(f)
        print(compare_line(compare(doc, prev)), file=sys.stderr)
    title, body = render(doc, collect, prev)
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
