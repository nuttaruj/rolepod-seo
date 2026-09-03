# Report shapes — chat summary + matrix, markdown report, JSON sidecar, HTML

Single source for the deliverables. Do not restate these shapes in the
skill body; fill them. Write the JSON first: the HTML report and the
Artifact are rendered from it.

## 1. Chat summary (always)

```text
| Site | <host> · <mode> · <N> pages reviewed · <YYYY-MM-DD> |
|---|---|
| SEO | <score>/10 · <band> — <one-line driver> |
| GEO | <score>/10 · <band> — <one-line driver> |
| AEO | <score>/10 · <band> — <one-line driver> |
| Top priorities | 1. <issue> (<page>) · 2. <issue> (<page>) · 3. <issue> (<page>) |
| Biggest strength | <what, with the page> |
| Report | reports/seo-audit-<host>-<date>.md · .json · <artifact link or "—"> |
```

### Chat priority matrix (always, after the summary)

```text
| Priority | Issue | Dim | Effort | Impact | Owner | Exact change |
|---|---|---|---|---|---|---|
| 🔴 Critical | <signal> · <path> | SEO | S | H | wplab | <field = value, or snippet> |
| 🟠 High | … | AEO | S | H | frontend-developer | … |
| 🟡 Medium | … | GEO | M | M | content-strategist | … |
| 🟢 Quick win | … | SEO | S | M | frontend-developer | … |
```

Dots: 🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Quick win. Sort: Critical, High,
Quick win, Medium; inside a band, higher severity first. Cap at ~10 rows in
chat; the full matrix lives in the report.

## 2. Markdown report — `reports/seo-audit-<host>-<date>.md`

```text
# SEO / GEO / AEO audit — <host>
<date> · mode: <quick|full> · tiers: A fetch, B <on|off>, C not in Phase 1

## Executive summary
<3–6 sentences: overall state, the one thing to fix first, the biggest strength.>

| Dimension | Score | Band | Drivers |
|---|---|---|---|
| SEO | n/10 | <band> | <top 3, each with page> |
| GEO | n/10 | <band> | … |
| AEO | n/10 | <band> | … |

## Pages audited
<paste pages.md from the collector; add a Tier B column when uiproof ran>
Could not fetch: <url (status)>, … — or "none".

## SEO findings
| Signal | Finding | Evidence | Page | Status |
|---|---|---|---|---|
<one row per finding; Status = fail | warn | pass | not-assessed>

## GEO findings
<same table; AI-bot policy appears here as a decision with the trade-offs>

## AEO findings
<same table>

## Cross-page
<duplicates, canonical consistency, sitemap vs noindex, redirects, hreflang>

## What's working
<strengths with the same evidence standard>

## Priority matrix
| Priority | Issue | Dimension | Effort | Impact | Owner | Exact change |
|---|---|---|---|---|---|---|
<Critical / High / Medium / Quick win · S/M/L · H/M/L · uiproof / wplab / frontend-developer / content-strategist / human · field + value, or the snippet>

## Not assessed
| Signal | Needs | Installed? |
|---|---|---|
<CWV → rolepod-uiproof measure_cwv · rendered DOM → audit_seo · queries / CTR → Search Console (Phase 2) · backlinks → index (not planned)>

## Glossary (Full mode)
<SEO, GEO, AEO, E-E-A-T, canonical, JSON-LD, PAA, CWV — one line each>
```

## 3. JSON sidecar — `reports/seo-audit-<host>-<date>.json`

Schema version 1. Additive changes only; consumers ignore unknown keys.

```json
{
  "schema": "rolepod-seo/report",
  "schema_version": 1,
  "generated_at": "2026-09-03T10:00:00Z",
  "site": { "base_url": "https://example.com/", "host": "example.com", "mode": "quick" },
  "summary": "Three to six sentences: overall state, the first fix, the biggest strength.",
  "collection": {
    "tiers": { "a": true, "b": false, "c": false },
    "tools": ["collect.py"],
    "pages_selected": 7,
    "pages_fetched": 6,
    "collect_path": ".rolepod-seo/collect-example.com-20260903/"
  },
  "scores": {
    "seo": { "score": 6, "band": "solid", "status_label": "Needs Work", "drivers": ["…", "…", "…"] },
    "geo": { "score": 4, "band": "below-baseline", "drivers": ["…"] },
    "aeo": { "score": 5, "band": "below-baseline", "drivers": ["…"] }
  },
  "findings": [
    {
      "id": "seo-canonical-cross-domain-blog-post-1",
      "dimension": "seo",
      "signal": "canonical",
      "page": "https://example.com/blog/post-1",
      "severity": "high",
      "status": "fail",
      "evidence": "<link rel=\"canonical\" href=\"https://other.example/blog/post-1\">",
      "fix": "Set canonical to https://example.com/blog/post-1",
      "owner": "wplab",
      "effort": "S",
      "impact": "H",
      "priority": "critical"
    }
  ],
  "strengths": [
    { "signal": "title", "page": "https://example.com/", "evidence": "…" }
  ],
  "not_assessed": [
    { "signal": "cwv", "needs": "rolepod-uiproof measure_cwv", "installed": false }
  ],
  "pages": [
    { "url": "https://example.com/", "role": "home", "status": 200, "in_sitemap": true }
  ]
}
```

Enumerations — `band`: critical | below-baseline | solid | strong | model |
not-assessed. `severity`: critical | high | medium | low | info.
`status`: fail | warn | pass | not-assessed. `owner`: uiproof | wplab |
frontend-developer | content-strategist | human. `effort`: S | M | L.
`impact`: H | M | L. `priority`: critical | high | medium | quick-win.
`id` is stable across runs of the same site: `<dimension>-<signal>-<slug>`.
`summary` (optional) is the executive summary; `status_label` (optional,
derived from the score: 8–10 On Track, 5–7 Needs Work, 1–4 Critical) is
what the HTML cover shows — the renderer computes it when absent.

## 4. HTML report — `reports/seo-audit-<host>-<date>.html`

Rendered from the sidecar by `scripts/render_report.py`; never hand-written.
Sections in order: cover (host, mode, date, pages, tiers; three score cards
colored by `status_label`), executive summary (`summary`, or generated
from scores + first fix), pages audited (+ title / words / schema with
`--collect`), SEO / GEO / AEO findings tables (Signal · Evidence · Fix ·
Page · Status chip), priority matrix (priority chip · Issue · Dim · Effort ·
Impact · Owner · Exact change), decisions for the owner (`info` + `human`
findings), what's working, not assessed, glossary (Full mode). Inline CSS
only, light / dark tokens, a "Save as PDF" button (`window.print()` only —
no download link, no PDF library; the Claude Artifact viewer blocks
page-initiated downloads and may restrict print, hence the ⌘P / Ctrl+P
hint next to it) and an `@media print` block. `--artifact`
emits the fragment the Claude Code Artifact tool expects, title = host.
