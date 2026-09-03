---
name: seo-audit
description: Audit a website for search readiness across SEO (classic search), GEO (generative engines — AI Overviews, ChatGPT search, Perplexity) and AEO (answer engines — featured snippets, People Also Ask, voice). Quick (home + key pages) or Full (every meaningful page) mode; scores each dimension 1–10 with quoted evidence; writes a markdown report + JSON sidecar and a priority matrix. Use when asked to audit a site, check SEO, check AI-search visibility, or review a domain's search readiness.
---

# /seo-audit

Turns "audit my site" into an evidence-backed report: fetch what a crawler
sees, check it against three lenses (SEO / GEO / AEO), score each 1–10, name
the fixes and who executes them. No API and no browser required — rendered
DOM and Core Web Vitals come from rolepod-uiproof when it is installed.

Parent judgment applies unchanged (verify-first, simplest viable, effort
ceiling `xhigh`): this skill adds procedure only.

## When to use

- "Audit / check / review SEO of <site>", "is my site ready for AI search",
  "why don't we show up in ChatGPT / Perplexity / AI Overviews", "GEO / AEO".
- Before a relaunch, after a migration, or as step one of an SEO project.
- Competitor comparison: run once per site, compare the summary tables.

## When NOT to use

- One page, rendered DOM only → rolepod-uiproof `/audit-seo`.
- Executing the fixes → `/seo-fix-plan` (hand-offs), `/seo-schema` (JSON-LD),
  `/seo-page-brief` (content). This skill stops at the priority matrix.
- Rank tracking, keyword volumes, backlinks, Search Console data → Phase 2;
  the report marks them "not assessed (needs …)".

## Inputs

- `url` — homepage or domain. Required.
- `mode` — `quick` | `full`. Asked once if not stated (step 1).
- Optional: key pages, target queries, output directory (default
  `reports/`), language hint.

## Outputs

1. **Chat summary** — one table: pages reviewed · date · SEO / GEO / AEO
   score with band · top 3 priorities (page named) · biggest strength.
2. **Report** — `reports/seo-audit-<host>-<YYYY-MM-DD>.md`, shape in
   `references/report.md`.
3. **JSON sidecar** — `reports/seo-audit-<host>-<YYYY-MM-DD>.json`, the
   stable shape in `references/report.md` § JSON. Other tools consume it.
4. **Artifact** — when the harness has an Artifact tool, publish the report
   as a private page and give the link. Skip silently elsewhere.
5. docx / PDF — only on explicit request and only when the runtime has the
   dependencies. The audit never depends on them.

## Process

### 1. Mode — one question, skipped when the request already says

Quick = homepage + up to 6 key pages, top issues, one screen. Full = every
meaningful page from nav / footer / sitemap (skip legal, login, tag and
paginated archives), all checks, priority matrix, glossary. Use the native
question UI when the harness has one; otherwise print a numbered question
with lettered options, mark the recommended default, and accept `1a` or
`defaults` as the answer.

### 2. Preamble — detect companions, state the tiers

Detect by tool presence, never by assumption:

- rolepod-uiproof tools (`audit_seo`, `measure_cwv`, `discover_flows`) → Tier B on.
- rolepod-wplab (`rolepod_wp_seo_set`) → WordPress hand-offs are executable.
- A subagent facility (Agent / scout / `spawn_agent`) → the sweep can be delegated.

Print one line: `Tier A fetch · Tier B <on|off> (rolepod-uiproof) · connectors: Phase 2`.

### 3. Collect — Tier A (always)

Run the bundled collector; it needs only Python 3, no packages:

```bash
python3 <skill-dir>/scripts/collect.py https://example.com --mode quick   # or --mode full
```

It fetches the homepage, robots.txt, sitemap(s), llms.txt and the selected
pages, then writes `pages.md` (one row per page), `site.json` (robots
verdict per bot, sitemap facts, duplicate titles / descriptions, redirect
chains, host variants) and `collect.json` under
`.rolepod-seo/collect-<host>-<date>/` (add `.rolepod-seo/` to the project's
`.gitignore`). Read `pages.md` and `site.json`. Open raw HTML only when a
finding needs a quote the table cannot give — then fetch that one page.

**Sweep delegation.** When the selection is more than about 10 URLs and the
harness can spawn subagents, hand the collector run to a read-only scout on
the cheap tier and take back the output path plus a 10-line summary. The
Lead never reads the sweep's HTML.

**No Python?** Fetch the same pages with the CLI's fetch tool or `curl -sL`
and fill the same columns by hand: status, final URL, title, description,
H1 count, canonical, robots, word count, schema types, author, FAQ.

Failures are findings, not excuses: a page that returns 4xx / 5xx or times
out appears in the report as "could not fetch <url> (<status>)".

### 4. Collect — Tier B (when rolepod-uiproof is installed)

- `audit_seo` on the homepage and each money page: rendered title / meta /
  canonical / JSON-LD validity / OG / hreflang. Diff against Tier A — a
  value that exists only after JavaScript runs is itself a GEO finding.
- Full mode: `measure_cwv` on the homepage and two money pages.
- `discover_flows` only when Tier A found no internal links on the
  homepage (JavaScript-only navigation).

Tier C (Search Console, keyword, rank data) is Phase 2: list what it would
add under "not assessed".

### 5. Analyze — per dimension, then cross-page

Work through the references in this order; each is a checklist with the
threshold, the evidence to quote and the severity:

- `references/seo-checks.md` — per-page technical, site-level, content, structured data.
- `references/geo-checks.md` — E-E-A-T surface, synthesizability, AI-bot policy.
- `references/aeo-checks.md` — answer blocks, question coverage, FAQ / HowTo, local.

Cross-page checks (duplicates, canonical consistency, sitemap vs noindex,
redirect chains, hreflang reciprocity) come last, from `site.json`.

Weight by page role (`role` column in `pages.tsv`): home and money pages
count more than blog posts; blog posts more than utility pages.

### 6. Score — 1–10 per dimension, evidence attached

| Band | Score | Meaning |
|---|---|---|
| critical | 1–3 | effectively invisible, or at risk |
| below-baseline | 4–5 | several foundational gaps |
| solid | 6–7 | base is right, clear upside |
| strong | 8–9 | refinements only |
| model | 10 | rare; needs evidence on every check |

Score from checklist hit-rate weighted by page role. Show the three
findings that drove each score. Never round up without evidence. A
dimension with no data is "not assessed (needs X)", never a number.

### 7. Report

Write the markdown report and the JSON sidecar from `references/report.md`,
publish the Artifact when available, then print the chat summary table.
Close with the priority matrix (Priority · Issue · Dimension · Effort ·
Impact · Owner · Exact change). "Exact change" carries the field and value
or the snippet — that is what lets `/seo-fix-plan`, rolepod-wplab,
frontend-developer or content-strategist execute without re-reading the audit.

## Evidence rules

1. Every finding quotes the actual text, tag or URL and names the page.
2. "Missing" is claimed only after every fetched page was checked.
3. A claim beyond fetched HTML names the tool that would prove it and
   whether that tool is installed.
4. Severity is reported, not manufactured; strengths get the same standard.
5. AI-bot crawl policy (GPTBot, ClaudeBot, PerplexityBot, Google-Extended,
   CCBot) is reported as a decision with trade-offs, never as a defect.

## Hand-offs

| Finding class | Goes to |
|---|---|
| Rendered-DOM detail, CWV, JavaScript-only nav | rolepod-uiproof `audit_seo` / `measure_cwv` / `discover_flows` |
| WordPress meta, canonical, noindex, OG, redirects | rolepod-wplab `rolepod_wp_seo_set`, `rolepod_wp_redirect_set` |
| Code: metadata objects, JSON-LD components, sitemap route | `frontend-developer` |
| Copy, page briefs, E-E-A-T content | `content-strategist` (audience: prospect) via `/seo-page-brief` |
| Policy: AI-bot access, brand naming, which testimonials to show | human |

## Examples

- `Audit https://northwind.example for SEO and AI search` → asks Quick / Full,
  runs the collector, writes both report files, prints the summary.
- `Full SEO audit of acme.com, rolepod-uiproof is installed` → Tier B on,
  CWV on home + two money pages, scout runs the sweep, glossary included.
- `Quick check: why is /pricing not cited by Perplexity?` → Quick mode on
  home + pricing, GEO / AEO findings first.
