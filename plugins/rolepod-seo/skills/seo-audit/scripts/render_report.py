#!/usr/bin/env python3
"""rolepod-seo — render the JSON sidecar as a self-contained HTML report.

Usage:
  render_report.py <sidecar.json> [--out FILE] [--collect collect.json] [--artifact]
                   [--previous older-sidecar.json]

Default output: a complete HTML document next to the sidecar as
seo-audit-<host>-<date>.html. Inline CSS, no scripts beyond the one
window.print() button; the only external request is the Google Fonts
stylesheet (Instrument Sans + JetBrains Mono) — offline the system fonts
take over. A "Save as PDF" button opens the browser's print dialog; there
is no PDF library, no download link, no automation.

--artifact writes the fragment form the Claude Code Artifact tool expects
(<title> + <style> + content, no <html>/<head>/<body>), host as the title.
The report is a single light theme on purpose — white page, dark hero —
so it reads the same inside a dark viewer.

--previous adds a "Since last audit" block (score deltas, fixed / new /
still-open findings matched by id) and prints the same one-liner to
stderr for the chat summary.

Everything else — headline, fix-first / quick-win cards, per-dimension
cards, priority matrix, roadmap phases, owner calls, strengths, not
assessed, the optional "no effect on Google Search" list — is derived
from the sidecar. Findings are ordered by effect on Google Search: direct
first, indirect next, "none" last and outside the matrix and roadmap.

Stdlib only.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from urllib.parse import urlsplit

PRIORITY_ORDER = {"critical": 0, "high": 1, "quick-win": 2, "medium": 3}
PRIORITY_LABEL = {"critical": "Critical", "high": "High", "quick-win": "Quick win", "medium": "Medium"}
PRIORITY_DOT = {"critical": "🔴", "high": "🟠", "medium": "🟡", "quick-win": "🟢"}
STATUS_LABEL = {"fail": "Fail", "warn": "Warn", "pass": "Pass", "not-assessed": "Not assessed"}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
DIM_NAME = {"seo": "SEO", "geo": "GEO", "aeo": "AEO"}
DIM_SUB = {"seo": "classic search", "geo": "generative engines", "aeo": "answer engines"}
PHASES = [
    ("Week 1", "Unblock", "critical", "Crawl and indexation blockers, and anything that hides money pages.", "coral"),
    ("Weeks 2–3", "High impact and quick wins", "high+quick-win", "Fixes with clear upside; the quick wins are one-file changes.", "lime"),
    ("Month 2", "Content and trust", "medium", "Copy, briefs, E-E-A-T, and schema breadth.", "amber"),
]
SITE_TYPE_LABEL = {"saas": "SaaS / software", "ecommerce": "e-commerce", "local": "local service", "publisher": "publisher / blog", "agency": "agency / services", "unknown": "not detected"}
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

# signal name → group, first match wins; the model writes free-text signals, so match by keyword
SIGNAL_GROUPS = [
    ("schema", r"schema|json-?ld|structured|breadcrumb|organization|local-?business|faqpage|speakable|sameas"),
    ("technical", r"title|description|h1|heading|canonical|robots|noindex|sitemap|redirect|https|hsts|mixed|viewport|lang|charset|url|favicon|og\b|open-?graph|twitter|hreflang|inlink|(?<!content-)depth|orphan|link|crawl|index|security|header|status|404|5xx"),
    ("content", r"content|word|thin|duplicate|topic|fresh|date|scann|readab|image|alt|paragraph"),
    ("trust", r"author|about|contact|nap|trust|proof|testimonial|entity|citation|fact|claim|source|bot|llms|render|agent|e-?e-?a-?t|brand"),
    ("answer", r"answer|question|faq|definition|step|how-?to|table|compar|voice|hours|service-?area|paa|toc|jump"),
]
# Signals with no effect on Google Search when the finding does not say otherwise.
NO_EFFECT_RE = re.compile(r"faq-?page|faq-?schema|how-?to|llms|speakable", re.I)
EFFECT_ORDER = {"direct": 0, "indirect": 1, "none": 2}
EFFECT_LABEL = {"direct": "affects Google Search", "indirect": "indirect / AI engines", "none": "no effect on Google Search"}
FONTS_HREF = "https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"


# ---------------------------------------------------------------- data helpers
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
    if not url or url == "site":
        return "site-wide"
    p = urlsplit(url)
    return (p.path or "/") + (("?" + p.query) if p.query else "")


def signal_group(signal: str) -> str:
    s_ = (signal or "").lower()
    for group, rx in SIGNAL_GROUPS:
        if re.search(rx, s_):
            return group
    return "other"


def effect_of(f: dict) -> str:
    """Explicit findings[].seo_effect wins; otherwise infer 'none' for retired / ignored signals, else 'direct'."""
    e = f.get("seo_effect")
    if e in EFFECT_ORDER:
        return e
    return "none" if NO_EFFECT_RE.search(f.get("signal", "") or "") else "direct"


def effective(findings: list[dict]) -> list[dict]:
    return [f for f in findings if effect_of(f) != "none"]


def status_counts(findings: list[dict], dim: str) -> dict[str, int]:
    c = {"fail": 0, "warn": 0, "pass": 0}
    for f in findings:
        if f.get("dimension") == dim and f.get("status") in c:
            c[f["status"]] += 1
    return c


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


def dominant_group(findings: list[dict], dim: str) -> str:
    gc = group_counts(findings, dim)
    if not gc:
        return ""
    return max(gc, key=lambda kv: (kv[1]["fail"] + kv[1]["warn"], kv[1]["pass"]))[0]


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


def headline_for(doc: dict, findings: list[dict]) -> str:
    if doc.get("headline"):
        return str(doc["headline"])
    open_ = [f for f in effective(findings) if f.get("status") in ("fail", "warn")]
    n_crit = sum(1 for f in open_ if f.get("priority") == "critical")
    n_quick = sum(1 for f in open_ if f.get("priority") == "quick-win")
    scores = {d: doc.get("scores", {}).get(d, {}).get("score") for d in ("seo", "geo", "aeo")}
    valid = {d: s for d, s in scores.items() if isinstance(s, int)}
    if not valid:
        return "Audit collected; scores not assessed yet."
    best = max(valid, key=valid.get)
    worst = min(valid, key=valid.get)
    blockers = f"{n_crit} critical blocker{'s' if n_crit != 1 else ''}" if n_crit else "no critical blockers"
    quick = f", {n_quick} quick win{'s' if n_quick != 1 else ''}" if n_quick else ""
    if best == worst:
        return f"{blockers}{quick} — {DIM_NAME[best]} at {valid[best]}/10."
    return f"{blockers}{quick} — {DIM_NAME[best]} is the strongest at {valid[best]}/10, {DIM_NAME[worst]} the weakest at {valid[worst]}/10."


# ---------------------------------------------------------------- CSS
CSS = """
:root{color-scheme:light;--bg:#FFFFFF;--ink:#14131F;--ink2:#221F3C;--body:#3B3853;--muted:#5A5775;--muted2:#6E6B85;--faint:#918EA8;--faint2:#B4B1C6;
--line:#E2E0F0;--card:#FFFFFF;--panel:#F7F6FD;--panel-indigo:#F1EFFE;--panel-indigo-ink:#221F3C;--nav:#4A4760;--nav-hover:#EBE9FA;
--indigo:#5B4BFF;--indigo-soft:#7C6BFF;--coral:#FF5C39;--coral-soft:#FF8F72;--lime:#C6F24E;--lime-ink:#6E8C10;--lime-bg:#EDF8CF;--lime-bg-ink:#5F7C0B;
--amber:#FFC93D;--amber-bg:#FFEEB8;--amber-ink:#7A5B00;--amber-ink2:#6B5A24;--amber-body:#3E3520;--amber-soft-bg:#FFF6DC;
--green-ink:#1F7A52;--green-bg:#E6F6EC;--red-ink:#C23A16;--red-bg:#FFEDE7;--high-bg:#FFD9CC;--high-ink:#8A2D12;
--dark:#1A1830;--dark2:#221F3C;--dark3:#2C2A4A;--dark-ring:#35315C;--dark-muted:#9C97C4;--dark-text:#DAD7EC;--dark-label:#B7B3D6;--dark-green:#8FE3B8;--dark-coral:#FF8F72}
/* single light theme on purpose: the report stays white in a dark viewer too */
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 'Instrument Sans',system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}
.mono,code,.evidence-text{font-family:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
a{color:inherit}
.page{max-width:1280px;margin:0 auto;display:grid;grid-template-columns:236px 1fr;gap:44px;padding:0 36px}
.side{padding:34px 0 60px}
.side .stick{position:sticky;top:34px;display:grid;gap:28px}
.dots{display:flex;align-items:center;gap:8px}
.dots span{height:10px;width:10px;border-radius:99px;display:inline-block}
.dots span:first-child{width:22px;background:var(--indigo)}.dots span:nth-child(2){background:var(--lime)}.dots span:nth-child(3){background:var(--coral)}
.side .host{font-size:18px;font-weight:700;letter-spacing:-.02em;margin-top:14px;color:var(--ink);word-break:break-all}
.side .sub{font-size:13px;color:var(--muted2);margin-top:4px;line-height:1.5}
.side nav{display:grid;gap:2px;border-top:1px solid var(--line);padding-top:18px}
.side nav a{font-size:13.5px;color:var(--nav);text-decoration:none;padding:9px 10px;border-radius:8px;display:flex;gap:10px}
.side nav a b{font-weight:600;color:var(--faint);font-family:'JetBrains Mono',monospace;font-size:11.5px;letter-spacing:.06em;min-width:22px}
.side nav a:hover{background:var(--panel);color:var(--ink)}
.print-btn{appearance:none;border:none;background:var(--lime);color:#14131F;border-radius:10px;padding:13px 16px;font:inherit;font-weight:700;font-size:14px;cursor:pointer;text-align:left;width:100%}
.print-btn:hover{filter:brightness(.96)}
.print-btn:focus-visible{outline:2px solid var(--indigo);outline-offset:2px}
.toolbar{font-size:12px;color:var(--faint);margin-top:8px;line-height:1.5}
main{padding:34px 0 96px;max-width:900px;min-width:0}
.hero{background:var(--dark);border-radius:26px;padding:40px 38px 34px;color:#FFFFFF}
.chips{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.chips span{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--dark-label);background:var(--dark3);border-radius:99px;padding:7px 12px}
.chips span.lime{color:#C6F24E}
.hero h1{margin:24px 0 0;font-size:34px;line-height:1.15;font-weight:700;letter-spacing:-.032em;color:#FFFFFF;max-width:660px;text-wrap:balance}
.scores{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:30px}
.score-card{background:var(--dark2);border-radius:18px;padding:22px 22px 24px}
.score-card .top{display:flex;align-items:center;gap:16px}
.ring{width:62px;height:62px;border-radius:50%;display:grid;place-items:center;flex:none}
.ring>div{width:46px;height:46px;border-radius:50%;background:var(--dark2);display:grid;place-items:center;color:#FFFFFF;font-weight:700;font-size:22px;font-variant-numeric:tabular-nums}
.score-card .dim{font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#FFFFFF;font-weight:600}
.score-card .sub{font-size:12.5px;color:var(--dark-muted);line-height:1.5;margin-top:3px}
.score-card .counts{margin-top:16px;font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--dark-green)}
.score-card .counts.has-fail{color:var(--dark-coral)}
.score-card .counts b{font-weight:600}
.score-card .groups{font-size:11.5px;color:var(--dark-muted);margin-top:8px;line-height:1.5}
.score-card .groups strong{color:var(--dark-label);font-weight:600}
section{padding:52px 0 0}
.shead{display:flex;align-items:center;gap:11px;margin-bottom:22px}
.shead .num{font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.14em;color:var(--indigo);font-weight:600}
.shead .lbl{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted2);font-weight:600;white-space:nowrap}
.shead .rule{flex:1;height:1px;background:var(--line)}
.shead .note{font-size:12.5px;color:var(--faint);white-space:nowrap}
.lead{margin:0;font-size:19px;line-height:1.45;letter-spacing:-.01em;color:var(--ink2);text-wrap:pretty}
.after{margin:14px 0 0;font-size:14.5px;color:var(--muted);line-height:1.6;max-width:720px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:26px}
.card,.fcard,.mcard,.phase,.tablewrap,.gcard,.since,.decision{border:1px solid var(--line)}
.card{background:var(--card);border-radius:18px;padding:24px 26px 26px}
.card.tight{padding:20px 22px}
.label{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.18em;text-transform:uppercase;font-weight:600;color:var(--faint)}
.label.coral{color:var(--coral)}.label.lime{color:var(--lime-ink)}.label.indigo{color:var(--indigo)}.label.amber{color:var(--amber-ink)}
.card .title{font-size:17px;font-weight:600;letter-spacing:-.018em;color:var(--ink);margin-top:10px}
.card .text{font-size:14px;color:var(--muted);margin-top:8px;line-height:1.6}
.card .text code{font-size:12.5px;color:var(--ink)}
.card ul.items{margin:10px 0 0;padding:0;list-style:none;display:grid;gap:6px;font-size:14px;color:var(--ink2)}
.tablewrap{background:var(--card);border-radius:18px;padding:8px 24px 20px;overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}
th{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--faint);font-weight:600;text-align:left;padding:18px 12px 14px 0;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:15px 12px 15px 0;border-bottom:1px solid var(--line);vertical-align:top;color:var(--muted)}
td.k{color:var(--ink);font-weight:500}
td.faint{color:var(--faint2)}
tr:last-child td{border-bottom:0}
.chip{display:inline-block;font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.12em;text-transform:uppercase;font-weight:600;border-radius:6px;padding:5px 9px;white-space:nowrap}
.chip.pass{color:var(--green-ink);background:var(--green-bg)}
.chip.fail{color:#FFFFFF;background:var(--coral)}
.chip.warn{color:var(--amber-ink);background:var(--amber-bg)}
.chip.not-assessed,.chip.info{color:var(--faint);background:var(--panel)}
.chip.none{color:var(--faint);background:transparent;border:1px dashed var(--faint2)}
.chip.p-critical{color:#FFFFFF;background:var(--coral)}
.chip.p-high{color:var(--high-ink);background:var(--high-bg)}
.chip.p-medium{color:var(--amber-ink);background:var(--amber-bg)}
.chip.p-quick-win{color:#14131F;background:var(--lime)}
.chip.working{color:var(--green-ink);background:var(--green-bg)}
.dimhead{display:flex;align-items:center;gap:12px;margin:34px 0 14px}
.dimhead:first-child{margin-top:0}
.dimhead .pill{font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.14em;text-transform:uppercase;font-weight:700;border-radius:8px;padding:6px 11px;color:#FFFFFF}
.dimhead .pill.seo{background:var(--lime);color:#14131F}.dimhead .pill.geo{background:var(--indigo)}.dimhead .pill.aeo{background:var(--coral)}
.dimhead .sub{font-size:14px;color:var(--muted2)}
.dimhead .cnt{margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:11.5px;color:var(--faint);white-space:nowrap}
.bygroup{font-size:12.5px;color:var(--faint);margin:-6px 0 12px}
.bygroup strong{color:var(--muted);font-weight:600}
.stack{display:grid;gap:12px}
.fcard{background:var(--card);border-radius:18px;padding:22px 24px 24px}
.fcard .row{display:flex;align-items:center;gap:11px;flex-wrap:wrap}
.fcard .sig{font-size:17px;font-weight:700;letter-spacing:-.02em;color:var(--ink)}
.fcard .sev{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--faint)}
.fcard .path{margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:12.5px;color:var(--muted2)}
.panels{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:16px}
.panel{background:var(--panel);border-radius:12px;padding:14px 16px 16px}
.panel.indigo{background:var(--panel-indigo)}
.panel .label{margin-bottom:8px}
.panel.indigo .label{color:var(--indigo)}
.panel .body{font-size:14px;line-height:1.6;color:var(--body)}
.panel.indigo .body{color:var(--panel-indigo-ink)}
.evidence-text{font-size:12.5px;line-height:1.6;color:var(--body);word-break:break-word}
.also ul{margin:10px 0 0;padding:0;list-style:none;display:grid;gap:8px;font-size:14px;color:var(--muted)}
.also li{display:grid;grid-template-columns:16px 1fr;gap:8px}
.also li .d{font-size:10px;line-height:1.9}
.also li .d.seo{color:var(--lime-ink)}.also li .d.geo{color:var(--indigo)}.also li .d.aeo{color:var(--coral)}
.mcard{background:var(--card);border-radius:18px;padding:22px 24px;display:grid;grid-template-columns:130px 1fr 220px;gap:24px;align-items:start}
.mcard .meta{font-family:'JetBrains Mono',monospace;font-size:11.5px;color:var(--faint);margin-top:10px;line-height:1.6}
.mcard .title{font-size:16px;font-weight:600;letter-spacing:-.018em;color:var(--ink)}
.mcard .text{font-size:14px;color:var(--muted);margin-top:6px;line-height:1.6}
.mcard .verify{background:var(--panel);border-radius:12px;padding:12px 14px}
.mcard .verify .body{font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.6;color:var(--body);margin-top:6px;word-break:break-word}
.phases{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.phase{background:var(--card);border-radius:18px;padding:22px 22px 24px}
.phase .when{display:flex;align-items:center;gap:9px;font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.16em;text-transform:uppercase;font-weight:600}
.phase .when i{width:9px;height:9px;border-radius:99px;display:inline-block}
.phase.coral .when{color:var(--coral)}.phase.coral .when i{background:var(--coral)}
.phase.lime .when{color:var(--lime-ink)}.phase.lime .when i{background:var(--lime)}
.phase.amber .when{color:var(--amber-ink)}.phase.amber .when i{background:var(--amber)}
.phase .title{font-size:18px;font-weight:700;letter-spacing:-.02em;color:var(--ink);margin-top:12px}
.phase .blurb{font-size:13.5px;color:var(--muted);margin-top:6px;line-height:1.55}
.phase ul{margin:14px 0 0;padding:0;list-style:none;display:grid;gap:7px;font-size:14px;color:var(--ink2)}
.phase ul .mono{font-size:12.5px;color:var(--muted2)}
.ongoing{background:var(--dark);border-radius:18px;padding:22px 24px 24px;margin-top:14px;color:var(--dark-text)}
.ongoing .when{display:flex;align-items:center;gap:9px;font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.16em;text-transform:uppercase;font-weight:600;color:var(--dark-label)}
.ongoing .when i{width:9px;height:9px;border-radius:99px;background:var(--indigo-soft);display:inline-block}
.ongoing .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px 32px;margin-top:16px}
.ongoing .item{display:grid;grid-template-columns:76px 1fr;gap:14px;font-size:13.5px;line-height:1.55}
.ongoing .item span:first-child{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.14em;text-transform:uppercase;font-weight:600;padding-top:2px}
.ongoing .decide{color:var(--dark-coral)}.ongoing .prove{color:#C6F24E}.ongoing .watch{color:var(--indigo-soft)}
.decision{background:var(--amber-bg);border-radius:18px;padding:24px 26px 26px;margin-bottom:14px}
.decision .label{color:var(--amber-ink)}
.decision .title{font-size:18px;font-weight:700;letter-spacing:-.02em;color:var(--ink);margin-top:10px}
.decision .ev{font-family:'JetBrains Mono',monospace;font-size:12.5px;color:var(--amber-ink2);margin-top:10px;line-height:1.6;word-break:break-word}
.decision .text{font-size:14.5px;color:var(--amber-body);margin-top:12px;line-height:1.6;max-width:720px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.wcard .row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.wcard .row .sig{font-size:15px;font-weight:600;color:var(--ink)}
.wcard .ev{font-size:13.5px;color:var(--body);margin-top:12px;line-height:1.6;word-break:break-word}
.wcard .ev.mono{font-size:12.5px}
.ncard .sig{font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:600;color:var(--ink)}
.ncard .needs{font-size:13.5px;color:var(--muted);margin-top:8px;line-height:1.55}
.ncard .inst{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--faint2);margin-top:14px}
.ncard .inst.yes{color:var(--green-ink)}
.optional .fcard{opacity:.85}
.bands{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-top:20px}
.band{border-radius:12px;padding:14px 14px 16px}
.band b{display:block;font-size:20px;font-weight:700;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.band span{display:block;font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.12em;text-transform:uppercase;margin-top:4px}
.band.b1{background:var(--red-bg);color:var(--red-ink)}.band.b2{background:var(--amber-soft-bg);color:var(--amber-ink)}.band.b3{background:var(--panel-indigo);color:var(--indigo)}.band.b4{background:var(--lime-bg);color:var(--lime-bg-ink)}.band.b5{background:var(--dark);color:#FFFFFF}.band.b5 span{color:#C6F24E}
.gloss{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.gcard{background:var(--card);border-radius:14px;padding:18px 20px}
.gcard .term{font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.14em;text-transform:uppercase;font-weight:600;color:var(--indigo)}
.gcard .def{font-size:13.5px;color:var(--muted);margin-top:8px;line-height:1.55}
.since{background:var(--card);border-radius:18px;padding:22px 26px;margin-top:26px}
.since .delta{font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--muted);margin-top:8px}
.since .up{color:var(--green-ink);font-weight:600}.since .down{color:var(--red-ink);font-weight:600}
.since .cols{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:14px}
.since ul{margin:6px 0 0;padding-left:18px;font-size:13.5px;color:var(--body)}
.foot{margin-top:60px;font-family:'JetBrains Mono',monospace;font-size:11.5px;color:var(--faint);line-height:1.7}
@media (max-width:960px){.page{grid-template-columns:1fr;gap:0;padding:0 18px}.side{padding:24px 0 8px}.side .stick{position:static}.side nav{grid-template-columns:repeat(auto-fill,minmax(140px,1fr))}
.scores,.phases,.grid3,.bands{grid-template-columns:1fr 1fr}.two,.panels,.grid2,.gloss,.ongoing .grid,.since .cols{grid-template-columns:1fr}.mcard{grid-template-columns:1fr}.hero{padding:28px 24px}.hero h1{font-size:26px}}
@media (max-width:560px){.scores,.phases,.grid3,.bands{grid-template-columns:1fr}}
@page{margin:14mm}
@media print{
  :root{--bg:#FFFFFF;--ink:#14131F;--ink2:#221F3C;--body:#3B3853;--muted:#5A5775;--muted2:#6E6B85;--faint:#918EA8;--faint2:#B4B1C6;--line:#E2E0F0;--card:#F7F6FD;--panel:#F1F0F8;--panel-indigo:#F1EFFE;--panel-indigo-ink:#221F3C;--lime-ink:#6E8C10;--lime-bg:#EDF8CF;--lime-bg-ink:#5F7C0B;--amber-bg:#FFEEB8;--amber-ink:#7A5B00;--amber-ink2:#6B5A24;--amber-body:#3E3520;--amber-soft-bg:#FFF6DC;--green-ink:#1F7A52;--green-bg:#E6F6EC;--red-ink:#C23A16;--red-bg:#FFEDE7;--high-bg:#FFD9CC;--high-ink:#8A2D12}
  body{font-size:12px;background:#fff;color:#14131F}
  .no-print,.toolbar{display:none!important}
  .page{display:block;padding:0;max-width:none}
  main{max-width:none;padding:0}
  .hero,.score-card,.ring,.ring>div,.chip,.chips span,.ongoing,.band,.decision,.pill,.dimhead .pill,.phase .when i{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .hero{border-radius:14px;padding:26px 24px}
  .hero h1{font-size:24px}
  section{padding:26px 0 0}
  #findings,#matrix{break-before:page;page-break-before:always}
  .fcard,.mcard,.phase,.card,.score-card,tr{page-break-inside:avoid;break-inside:avoid}
  .shead,.dimhead{page-break-after:avoid;break-after:avoid}
  .tablewrap{overflow:visible}
  a{text-decoration:none}
}
@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}
"""


# ---------------------------------------------------------------- render
def shead(num: int, label: str, note: str = "") -> str:
    return (f'<div class="shead"><span class="num">{num:02d}</span><span class="lbl">{esc(label)}</span><span class="rule"></span>'
            + (f'<span class="note">{esc(note)}</span>' if note else "") + "</div>")


def code_in(text: str) -> str:
    """Escape text, then render <…> tags and backticked spans in monospace."""
    t = esc(text)
    t = re.sub(r"(&lt;[^&]{1,80}&gt;)", r'<code class="mono">\1</code>', t)
    t = re.sub(r"`([^`]{1,120})`", r'<code class="mono">\1</code>', t)
    return t


def render(doc: dict, collect: dict | None = None, prev: dict | None = None) -> tuple[str, str]:
    """Return (title, body_html). body_html is the whole .page grid (sidebar + main)."""
    site = doc.get("site", {})
    host = site.get("host", "site")
    mode = site.get("mode", "quick")
    date = (doc.get("generated_at") or "")[:10]
    col = doc.get("collection", {})
    tiers = col.get("tiers", {})
    scores = doc.get("scores", {})
    findings = doc.get("findings", [])
    eff = effective(findings)
    facts: dict[str, dict] = {}
    if collect:
        for p in collect.get("pages", []):
            facts[p.get("url")] = p
    st = site.get("site_type") or {}
    st_type = st.get("type") if isinstance(st, dict) else (st if isinstance(st, str) else "")
    st_conf = st.get("confidence", "") if isinstance(st, dict) else ""
    st_signals = (st.get("signals", {}).get(st_type, []) if isinstance(st, dict) else []) or []

    open_ = [f for f in eff if f.get("status") in ("fail", "warn")]
    crit = [f for f in open_ if f.get("priority") == "critical"]
    quick = [f for f in open_ if f.get("priority") == "quick-win"]
    matrix = sorted(open_, key=lambda f: (PRIORITY_ORDER.get(f.get("priority"), 9), SEVERITY_ORDER.get(f.get("severity"), 9)))
    optional = [f for f in findings if effect_of(f) == "none" and f.get("status") in ("fail", "warn")]
    decisions = [f for f in findings if f.get("severity") == "info" and f.get("owner") == "human"]
    strengths = doc.get("strengths", [])
    na_items = doc.get("not_assessed", [])
    leading = [f for f in eff if f.get("leading_indicator")]
    pages = doc.get("pages", [])

    sections: list[tuple[str, str]] = []  # (id, label) for nav
    out: list[str] = []

    # ---- hero
    chips = [f'<span class="lime">{esc(col.get("pages_fetched", "?"))} of {esc(col.get("pages_selected", "?"))} pages fetched</span>',
             '<span>Tier A · plain fetch</span>']
    if tiers.get("b"):
        chips.append("<span>Tier B · rendered DOM</span>")
    if tiers.get("c"):
        chips.append("<span>connectors</span>")
    if st_type and st_type != "unknown":
        chips.append(f"<span>{esc(SITE_TYPE_LABEL.get(st_type, st_type))}</span>")
    out.append('<header class="hero"><div class="chips">' + "".join(chips) + "</div>")
    out.append(f"<h1>{esc(headline_for(doc, findings))}</h1>")
    out.append('<div class="scores">')
    ring_color = {"seo": "#C6F24E", "geo": "#7C6BFF", "aeo": "#FF5C39"}
    for d in ("seo", "geo", "aeo"):
        s = scores.get(d, {})
        score = s.get("score")
        label, cls = score_status(score)
        if s.get("band") == "not-assessed":
            label, cls = "Not assessed", "na"
        turn = (score / 10) if isinstance(score, int) else 0
        c = status_counts(eff, d)
        n_opt = sum(1 for f in findings if f.get("dimension") == d and effect_of(f) == "none" and f.get("status") in ("fail", "warn"))
        counts_cls = "counts has-fail" if c["fail"] else "counts"
        out.append(f'<div class="score-card" data-status="{cls}"><div class="top">'
                   f'<div class="ring" style="background:conic-gradient({ring_color[d]} 0turn {turn:.2f}turn, var(--dark-ring) {turn:.2f}turn 1turn)"><div>{esc(score) if isinstance(score, int) else "—"}</div></div>'
                   f'<div><div class="dim">{DIM_NAME[d]}</div><div class="sub">{DIM_SUB[d]}<br>band {esc(str(s.get("band", "—")).replace("-", " "))} · {esc(label)}</div></div></div>'
                   f'<div class="{counts_cls}"><b>{c["fail"]}</b> fail · <b>{c["warn"]}</b> warn · <b>{c["pass"]}</b> pass' + (f" · {n_opt} optional (no Google effect)" if n_opt else "") + "</div>"
                   + (f'<div class="groups">{group_line(eff, d)}</div>' if group_counts(eff, d) else "") + "</div>")
    out.append("</div></header>")

    # ---- 01 summary
    n = 1
    sections.append(("summary", "Summary"))
    out.append(f'<section id="summary">{shead(n, "Executive summary")}')
    summary = doc.get("summary")
    if summary:
        out.append(f'<p class="lead">{esc(summary)}</p>')
    else:
        parts = []
        for d in ("seo", "geo", "aeo"):
            s = scores.get(d, {})
            lab, _ = score_status(s.get("score"))
            parts.append(f"{DIM_NAME[d]} {s.get('score', '—')}/10 ({lab})")
        top = sorted(open_, key=lambda f: PRIORITY_ORDER.get(f.get("priority"), 9))
        first = f" First fix: {top[0].get('fix')} ({path_of(top[0].get('page', ''))})." if top else ""
        out.append(f'<p class="lead">{esc(", ".join(parts))}.{esc(first)}</p>')
    after = []
    if st_type and st_type != "unknown":
        sig = "; ".join(v if isinstance(v, str) else ", ".join(v) for v in st_signals[:3])
        after.append(f"Site type: <strong>{esc(SITE_TYPE_LABEL.get(st_type, st_type))}</strong> ({esc(st_conf)} confidence" + (f" — {esc(sig)}" if sig else "") + ").")
    if decisions:
        after.append(f"{len(decisions)} decision{'s' if len(decisions) != 1 else ''} for the owner in section {'06' if pages else '05'}.")
    if optional:
        after.append(f"{len(optional)} item{'s' if len(optional) != 1 else ''} with no effect on Google Search listed last.")
    if after:
        out.append(f'<p class="after">{" ".join(after)}</p>')
    out.append('<div class="two">')
    for label_cls, label, items, empty in (("coral", "Fix first", crit, "No critical items."), ("lime", "Quick wins", quick, "No quick wins tagged.")):
        out.append(f'<div class="card"><h3 class="label {label_cls}" style="margin:0">{label}</h3>')
        if items:
            f0 = items[0]
            out.append(f'<div class="title">{esc(f0.get("signal"))} · {esc(path_of(f0.get("page", "")))}</div><div class="text">{code_in(f0.get("fix", ""))}</div>')
            if len(items) > 1:
                out.append('<ul class="items">' + "".join(f'<li>{esc(f.get("signal"))} · <span class="mono">{esc(path_of(f.get("page", "")))}</span></li>' for f in items[1:4]) + "</ul>")
        else:
            out.append(f'<div class="text">{empty}</div>')
        out.append("</div>")
    out.append("</div>")
    if prev:
        cmp = compare(doc, prev)
        bits = []
        for d, (a, b) in cmp["scores"].items():
            if isinstance(a, int) and isinstance(b, int):
                cls_ = "up" if b > a else "down" if b < a else ""
                bits.append(f'{DIM_NAME[d]} {a} → <span class="{cls_}">{b}</span>')
        out.append(f'<div class="since" id="since"><div class="label indigo">Since last audit — {esc(cmp["previous_date"])}</div>'
                   f'<div class="delta">{" · ".join(bits)} · fixed <strong>{len(cmp["fixed"])}</strong> · new <strong>{len(cmp["new"])}</strong> · still open <strong>{len(cmp["still"])}</strong></div><div class="cols">')
        for label, items in (("Fixed", cmp["fixed"]), ("New", cmp["new"])):
            out.append(f'<div><h3 class="label" style="margin:0">{label}</h3>' + ('<ul>' + "".join(f'<li>{esc(f.get("signal"))} · <span class="mono">{esc(path_of(f.get("page", "")))}</span></li>' for f in items[:12]) + '</ul>' if items else '<div class="text" style="color:var(--faint)">none</div>') + '</div>')
        out.append("</div></div>")
    out.append("</section>")

    # ---- 02 pages
    per_page: dict[str, dict[str, int]] = {}
    for f in open_:
        per_page.setdefault(f.get("page", ""), {"fail": 0, "warn": 0})[f["status"]] += 1
    if pages:
        n += 1
        sections.append(("pages", "Pages"))
        out.append(f'<section id="pages">{shead(n, "Pages audited", f"{len(pages)} URL{"s" if len(pages) != 1 else ""} in scope")}<div class="tablewrap"><table><thead><tr><th>Page</th><th>Role</th><th>Status</th><th>Sitemap</th><th>Findings</th>'
                   + ("<th>Words</th><th>Links in / depth</th>" if facts else "") + "<th>Schema</th></tr></thead><tbody>")
        for p in pages:
            f = facts.get(p.get("url"), {})
            s_ = p.get("status")
            st_cls = "pass" if s_ == 200 else "fail"
            pc = per_page.get(p.get("url", ""), {})
            cnt = " ".join(x for x in ((f'<span class="chip fail">{pc["fail"]} fail</span>' if pc.get("fail") else ""), (f'<span class="chip warn">{pc["warn"]} warn</span>' if pc.get("warn") else "")) if x) or '<span style="color:var(--faint2)">clean</span>'
            schema = ", ".join((f.get("schema_types") if f else None) or [])
            row = (f'<tr><td class="k mono">{esc(path_of(p.get("url", "")))}</td><td>{esc(p.get("role", ""))}</td>'
                   f'<td><span class="chip {st_cls}">{esc(s_)}</span></td><td>{"yes" if p.get("in_sitemap") else "no"}</td><td>{cnt}</td>')
            if facts:
                dep = f.get("depth")
                row += f'<td>{esc(f.get("word_count", "—"))}</td><td>{esc(f.get("inlinks", "—"))} / {"—" if dep is None else esc(dep)}</td>'
            row += f'<td class="{"faint" if not schema else "mono"}">{esc(schema) if schema else "none"}</td></tr>'
            out.append(row)
        out.append("</tbody></table>" + ("" if facts else '<div class="toolbar" style="margin-top:12px">Links in and crawl depth are not captured in this collection tier.</div>') + "</div></section>")

    # ---- 03 findings
    n += 1
    sections.append(("findings", "Findings"))
    n_open = len(open_)
    out.append(f'<section id="findings">{shead(n, "Findings", f"{n_open} open · {sum(1 for f in eff if f.get("status") == "pass")} pass")}')
    for d in ("seo", "geo", "aeo"):
        rows = [f for f in eff if f.get("dimension") == d and f.get("status") in ("fail", "warn")]
        passes = [f for f in eff if f.get("dimension") == d and f.get("status") == "pass"]
        none_rows = [f for f in optional if f.get("dimension") == d]
        c = status_counts(eff, d)
        dom = dominant_group(eff, d)
        out.append(f'<section id="{d}" style="padding:0"><div class="dimhead"><span class="pill {d}">{DIM_NAME[d]}</span><span class="sub">{DIM_SUB[d]}' + (f" — group {esc(dom)}" if dom else "") + f'</span><span class="cnt">{c["fail"]} fail · {c["warn"]} warn · {c["pass"]} pass</span></div>')
        if group_counts(eff, d):
            out.append(f'<p class="bygroup">By group: {group_line(eff, d)}</p>')
        out.append('<div class="stack">')
        for f in sorted(rows, key=lambda f: (EFFECT_ORDER[effect_of(f)], PRIORITY_ORDER.get(f.get("priority"), 9), SEVERITY_ORDER.get(f.get("severity"), 9))):
            stt = f.get("status", "")
            e = effect_of(f)
            is_decision = f.get("owner") == "human"
            out.append(f'<div class="fcard"><div class="row"><span class="sig">{esc(f.get("signal"))}</span><span class="chip {esc(stt)}">{esc(STATUS_LABEL.get(stt, stt))}</span>'
                       f'<span class="sev">{esc(f.get("severity"))} severity' + (f' · {EFFECT_LABEL["indirect"]}' if e == "indirect" else "") + f'</span><span class="path">{esc(path_of(f.get("page", "")))}</span></div>'
                       f'<div class="panels"><div class="panel"><div class="label">Evidence</div><div class="evidence-text">{esc(f.get("evidence"))}</div></div>'
                       f'<div class="panel indigo"><div class="label">{"Decision" if is_decision else "Fix"}</div><div class="body">{code_in(f.get("fix", ""))}</div></div></div></div>')
        also = [f'<li><span class="d {d}">◆</span><span>{esc(f.get("evidence") or f.get("signal"))}</span></li>' for f in passes]
        drivers = [x for x in scores.get(d, {}).get("drivers", []) if not any((f.get("signal") or "zzz").split("-")[0] in x.lower() and path_of(f.get("page", "")) in x for f in rows)]
        also += [f'<li><span class="d {d}">◆</span><span>{esc(x)}</span></li>' for x in drivers[:4]]
        if not rows and not also:
            out.append('<div class="fcard"><div class="text" style="color:var(--faint)">No findings recorded for this dimension.</div></div>')
        if also:
            out.append(f'<div class="fcard also"><div class="label">Also observed</div><ul>{"".join(also)}</ul></div>')
        if none_rows:
            out.append('<div class="fcard also" style="opacity:.8"><div class="label">Not affecting Google Search — listed in the optional section</div><ul>'
                       + "".join(f'<li><span class="d {d}">◇</span><span>{esc(f.get("signal"))} · <span class="mono">{esc(path_of(f.get("page", "")))}</span> <span class="chip none">{EFFECT_LABEL["none"]}</span></span></li>' for f in none_rows) + "</ul></div>")
        out.append("</div></section>")
    out.append("</section>")

    # ---- 04 matrix
    n += 1
    sections.append(("matrix", "Priority"))
    owners = sorted({f.get("owner", "") for f in matrix if f.get("owner")})
    efforts = {f.get("effort") for f in matrix}
    note = (("all small effort" if efforts == {"S"} else f"{len(matrix)} items") + (" · " + ", ".join(owners) if owners else ""))
    out.append(f'<section id="matrix">{shead(n, "Priority matrix", note if matrix else "")}')
    if matrix:
        out.append('<div class="stack">')
        for f in matrix:
            pr = f.get("priority", "medium")
            right = (f'<div class="verify"><div class="label">Verify</div><div class="body">{esc(f.get("verify"))}</div></div>' if f.get("verify")
                     else f'<div class="verify"><div class="label">Owner</div><div class="body">{esc(f.get("owner", "—"))}</div></div>')
            out.append(f'<div class="mcard"><div><span class="chip p-{esc(pr)}">{esc(PRIORITY_LABEL.get(pr, pr))}</span><div class="meta">{esc(DIM_NAME.get(f.get("dimension"), ""))}<br>effort {esc(f.get("effort", "—"))} · impact {esc(f.get("impact", "—"))}<br>{esc(f.get("owner", ""))}</div></div>'
                       f'<div><div class="title">{esc(f.get("signal"))} · {esc(path_of(f.get("page", "")))}</div><div class="text">{code_in(f.get("fix", ""))}</div></div>{right}</div>')
        out.append("</div>")
    else:
        out.append('<div class="card"><div class="text">Nothing to fix — every check passed or was not assessed.</div></div>')
    out.append("</section>")

    # ---- 05 roadmap
    n += 1
    sections.append(("roadmap", "Roadmap"))
    out.append(f'<section id="roadmap">{shead(n, "Roadmap")}<div class="phases">')
    for when, title, key, blurb, cls in PHASES:
        wanted = set(key.split("+"))
        items = [f for f in matrix if f.get("priority") in wanted]
        out.append(f'<div class="phase {cls}"><div class="when"><i></i>{esc(when)}</div><div class="title">{esc(title)}</div><div class="blurb">{esc(blurb)}</div>'
                   + ('<ul>' + "".join(f'<li>{esc(f.get("signal"))} · <span class="mono">{esc(path_of(f.get("page", "")))}</span></li>' for f in items[:8]) + '</ul>' if items else '<ul><li class="mono" style="color:var(--faint2)">nothing in this phase</li></ul>') + "</div>")
    out.append("</div>")
    ongoing = [("decide", "Decide", f'{esc(f.get("signal"))} — {esc(f.get("fix"))}') for f in decisions]
    ongoing += [("prove", "Prove", f'{esc(x.get("signal"))} — needs {esc(x.get("needs"))}') for x in na_items]
    ongoing += [("watch", "Watch", esc(f.get("leading_indicator"))) for f in leading]
    ongoing.append(("watch", "Re-audit", "The next report diffs against this one by finding id."))
    out.append('<div class="ongoing"><div class="when"><i></i>Ongoing — decide, measure, re-audit</div><div class="grid">'
               + "".join(f'<div class="item"><span class="{cls}">{lab}</span><span>{txt}</span></div>' for cls, lab, txt in ongoing) + "</div></div></section>")

    # ---- 06 owner calls and strengths
    n += 1
    sections.append(("owner", "Owner calls"))
    out.append(f'<section id="owner">{shead(n, "Owner calls and strengths", f"{len(decisions)} decision{"s" if len(decisions) != 1 else ""} · {len(strengths)} working")}')
    out.append('<section id="decisions" style="padding:0">')
    for f in decisions:
        out.append(f'<div class="decision"><div class="label">Decision for the owner</div><div class="title">{esc(f.get("signal"))}</div><div class="ev">{esc(f.get("evidence"))}</div><div class="text">{esc(f.get("fix"))}</div></div>')
    if not decisions:
        out.append('<div class="card tight" style="margin-bottom:14px"><div class="text" style="margin:0;color:var(--faint)">No decisions pending for the owner.</div></div>')
    out.append("</section>")
    out.append('<section id="strengths" style="padding:0">')
    if strengths:
        out.append('<div class="grid2">' + "".join(
            f'<div class="card wcard"><div class="row"><span class="chip working">Working</span><span class="sig">{esc(s.get("signal"))} · {esc(path_of(s.get("page", "")))}</span></div><div class="ev mono">{esc(s.get("evidence"))}</div></div>' for s in strengths) + "</div>")
    else:
        out.append('<div class="card tight"><div class="text" style="margin:0;color:var(--faint)">No strengths recorded.</div></div>')
    out.append("</section></section>")

    # ---- 07 not assessed
    if na_items:
        n += 1
        sections.append(("not-assessed", "Not assessed"))
        out.append(f'<section id="not-assessed">{shead(n, "Not assessed", f"{len(na_items)} signal{"s" if len(na_items) != 1 else ""} need a tool")}<div class="grid3">'
                   + "".join(f'<div class="card ncard"><div class="sig">{esc(x.get("signal"))}</div><div class="needs">{esc(x.get("needs"))}</div><div class="inst {"yes" if x.get("installed") else ""}">{"installed — run it" if x.get("installed") else "not installed"}</div></div>' for x in na_items) + "</div></section>")

    # ---- 08 optional — no effect on Google Search, listed last on purpose
    if optional:
        n += 1
        sections.append(("optional", "No effect"))
        out.append(f'<section id="optional" class="optional">{shead(n, "No effect on Google Search", "optional · listed last on purpose")}'
                   '<p class="after" style="margin:0 0 16px">These signals do not change crawling, indexing or ranking in Google Search (rich results retired, or the file is ignored). They may still help other answer engines. Do nothing here before the sections above are clean.</p><div class="stack">')
        for f in optional:
            out.append(f'<div class="fcard"><div class="row"><span class="sig">{esc(f.get("signal"))}</span><span class="chip none">{EFFECT_LABEL["none"]}</span><span class="path">{esc(path_of(f.get("page", "")))}</span></div>'
                       f'<div class="panels"><div class="panel"><div class="label">Why no effect</div><div class="evidence-text">{esc(f.get("evidence"))}</div></div><div class="panel"><div class="label">Optional change</div><div class="body">{code_in(f.get("fix", ""))}</div></div></div></div>')
        out.append("</div></section>")

    # ---- 09 method
    n += 1
    sections.append(("method", "Method"))
    tiers_used = ["plain fetch (collect.py)"] + (["rolepod-uiproof rendered DOM / CWV / a11y"] if tiers.get("b") else []) + (["connectors"] if tiers.get("c") else [])
    out.append(f'<section id="method">{shead(n, "How to read the scores")}<div class="card"><p style="margin:0;font-size:14.5px;line-height:1.65;color:var(--body)">'
               'Each dimension is scored 1–10 from the checklist hit-rate, weighted by page role — home and money pages count more than posts, posts more than utility pages — and by site type when it was detected with high confidence. '
               'Every finding quotes the page and the tag; "missing" is claimed only after every fetched page was checked; anything the collection tier could not see is listed under Not assessed with the tool that would prove it. '
               f'Data tiers used: {esc(", ".join(tiers_used))}. Findings keep a stable id so the next audit can diff against this one. '
               'Findings are ordered by effect: what changes Google Search first, then indirect / AI-engine signals, then items marked "no effect on Google Search", which never enter the priority matrix or the roadmap.</p>'
               '<div class="bands"><div class="band b1"><b>1–3</b><span>critical</span></div><div class="band b2"><b>4–5</b><span>below baseline</span></div><div class="band b3"><b>6–7</b><span>solid</span></div><div class="band b4"><b>8–9</b><span>strong</span></div><div class="band b5"><b>10</b><span>model</span></div></div></div></section>')

    # ---- 10 glossary (Full mode)
    if mode == "full":
        n += 1
        sections.append(("glossary", "Glossary"))
        out.append(f'<section id="glossary">{shead(n, "Glossary")}<div class="gloss">' + "".join(f'<div class="gcard"><div class="term">{esc(t)}</div><div class="def">{esc(d_)}</div></div>' for t, d_ in GLOSSARY) + "</div></section>")

    out.append(f'<p class="foot">Generated {esc(doc.get("generated_at", ""))} · schema {esc(doc.get("schema", ""))} v{esc(doc.get("schema_version", ""))} · collector: {esc(", ".join(col.get("tools", [])))}</p>')

    # ---- sidebar
    nav = "".join(f'<a href="#{sid}"><b>{i + 1:02d}</b>{esc(lab)}</a>' for i, (sid, lab) in enumerate(sections))
    side = (f'<aside class="side no-print"><div class="stick"><div><div class="dots"><span></span><span></span><span></span></div>'
            f'<div class="host">{esc(host)}</div><div class="sub">SEO · GEO · AEO audit<br>{esc(mode)} mode · {esc(date)}</div></div>'
            f'<nav>{nav}</nav>'
            '<div><button type="button" class="print-btn" onclick="window.print()">Save as PDF ↗</button>'
            '<div class="toolbar">Opens the browser\'s print dialog — or press ⌘P / Ctrl+P → Save as PDF.</div></div></div></aside>')
    body = f'<div class="page">{side}<main>{"".join(out)}</main></div>'
    return host, body


def to_document(title: str, body: str) -> str:
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<title>{esc(title)}</title>\n<link rel=\"stylesheet\" href=\"{FONTS_HREF}\">\n<style>{CSS}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n")


def to_artifact(title: str, body: str) -> str:
    return f"<title>{esc(title)}</title>\n<link rel=\"stylesheet\" href=\"{FONTS_HREF}\">\n<style>{CSS}</style>\n{body}\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sidecar")
    ap.add_argument("--out")
    ap.add_argument("--collect", help="collector collect.json to add words / links-in / depth / schema to the pages table")
    ap.add_argument("--artifact", action="store_true", help="fragment form for the Claude Code Artifact tool")
    ap.add_argument("--previous", help="older sidecar for the same host — adds the Since-last-audit block")
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
