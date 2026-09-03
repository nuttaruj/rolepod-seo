# Report shapes — chat summary, markdown report, JSON sidecar

Single source for the three deliverables. Do not restate these shapes in
the skill body; fill them.

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
  "collection": {
    "tiers": { "a": true, "b": false, "c": false },
    "tools": ["collect.py"],
    "pages_selected": 7,
    "pages_fetched": 6,
    "collect_path": ".rolepod-seo/collect-example.com-20260903/"
  },
  "scores": {
    "seo": { "score": 6, "band": "solid", "drivers": ["…", "…", "…"] },
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
