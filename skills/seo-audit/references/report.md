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
| Quick wins | <up to 3 one-file changes, page named — never a `seo_effect: none` item> |
| Biggest strength | <what, with the page> |
| Since last audit | <the render_report --previous line: "SEO 6→7 · fixed 3 · new 1 · still open 9" — or omit the row> |
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
<one row per finding, ordered direct → indirect → none; Status = fail | warn | pass | not-assessed; a `none` row says "no effect on Google Search" in the Finding cell>

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

## No effect on Google Search (optional, listed last)
<`seo_effect: none` items: signal · why no effect · optional change · page — never in the matrix or the roadmap>

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
  "site": { "base_url": "https://example.com/", "host": "example.com", "mode": "quick",
            "site_type": { "type": "local", "confidence": "high", "signals": { "local": ["home: address + phone"] } } },
  "headline": "One sentence for the cover: the state of the site in the reader's words.",
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
      "priority": "critical",
      "seo_effect": "direct",
      "verify": "collect.py --urls one.txt → canonical_ok = self",
      "leading_indicator": "Search Console: the post's own URL appears under Pages within 2 weeks"
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
`seo_effect`: `direct` (changes crawling / indexing / ranking in Google
Search) | `indirect` (trust and answer-structure signals, AI engines) |
`none` (no effect on Google Search — FAQ / HowTo rich results retired,
`llms.txt` ignored, `speakable`). **Set it on every finding.** The report
orders by effect and lists `none` items last under "No effect on Google
Search — optional"; they never enter the priority matrix, the roadmap,
the quick wins or the chat summary. The markdown report follows the same
order. `verify` and `leading_indicator` are optional per finding (see
`docs/report-schema.md`). `headline` (optional) is the one-sentence cover line — write it; the
renderer only generates a count-based fallback. `summary` (optional) is
the executive summary; `status_label` (optional,
derived from the score: 8–10 On Track, 5–7 Needs Work, 1–4 Critical) is
what the HTML cover shows — the renderer computes it when absent.

## 4. HTML report — `reports/seo-audit-<host>-<date>.html`

Rendered from the sidecar by `scripts/render_report.py`; never hand-written.
Layout: a sticky sidebar (host, mode · date, numbered section nav, Save as
PDF) beside a 900 px column. Sections in order: hero (chips: pages fetched,
tiers, site type; one-sentence `headline`; three score cards with a ring
gauge, band, status label, fail / warn / pass counts and the by-group
line), 01 executive summary (`summary` or generated text, site type line,
Fix-first and Quick-wins cards, since-last-audit block with
`--previous`), 02 pages audited (findings per page; + words / links-in /
depth / schema with `--collect`), 03 findings (per dimension: pill, group,
counts; one card per open finding with Evidence and Fix panels; "Also
observed" for pass items and remaining drivers; a muted pointer to the
optional section for `none` items), 04 priority matrix (cards: priority
chip + dim / effort / impact / owner · title + fix · Verify panel), 05
roadmap (Week 1 / Weeks 2–3 / Month 2 cards + a dark Ongoing card: Decide /
Prove / Watch / Re-audit), 06 owner calls and strengths, 07 not assessed,
08 no effect on Google Search (optional, listed last), 09 how to read the
scores (band cards), 10 glossary (Full mode). Instrument Sans + JetBrains
Mono are embedded from `assets/fonts.css` (variable fonts, latin +
latin-ext, SIL Open Font License) so the report renders identically
offline, in the Claude Artifact viewer and in print — no external
request at all. Single light theme on purpose (the design's `#F5F4FB`
page, white cards, dark hero) so it reads the same in a dark viewer.
`scripts/export_pdf.py` turns the HTML into `reports/…pdf` with an
installed Chromium-family browser's print engine; `render_report.py
--pdf` embeds that PDF so the artifact's Save as PDF button can hand it
over through the Artifact `downloads` capability (publish with
`capabilities: {downloads: true}`). Inline CSS
only, light / dark tokens, a "Save as PDF" button (`window.print()` only —
no download link, no PDF library; the Claude Artifact viewer blocks
page-initiated downloads and may restrict print, hence the ⌘P / Ctrl+P
hint next to it) and an `@media print` block. `--artifact`
emits the fragment the Claude Code Artifact tool expects, title = host.
