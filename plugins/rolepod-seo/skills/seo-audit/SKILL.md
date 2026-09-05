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
  `reports/`), language hint, a Search Console **Performance export**
  (zip / CSV — see `seo-fix-plan/scripts/gsc_csv.py`; never required, ask
  at most once).

## Outputs

1. **Chat summary** — one table: pages reviewed · date · SEO / GEO / AEO
   score with band · top 3 priorities (page named) · biggest strength.
2. **Report** — `reports/seo-audit-<host>-<YYYY-MM-DD>.md`, shape in
   `references/report.md`.
3. **JSON sidecar** — `reports/seo-audit-<host>-<YYYY-MM-DD>.json`, the
   stable shape in `references/report.md` § JSON. Other tools consume it.
4. **HTML report** — `reports/seo-audit-<host>-<YYYY-MM-DD>.html` rendered
   from the sidecar by `scripts/render_report.py` (stdlib, self-contained,
   fonts embedded). This is the visual deliverable on every CLI.
5. **PDF** — `reports/seo-audit-<host>-<YYYY-MM-DD>.pdf` from
   `scripts/export_pdf.py`: the print engine of a Chromium-family browser
   already on the machine (Chrome, Chromium, Edge, Brave, or the Chromium
   rolepod-uiproof keeps). No browser → say so; the HTML prints from any
   browser with ⌘P / Ctrl+P.
6. **Artifact** — on Claude Code, publish the `--artifact --pdf` form of
   the HTML as a private page with `capabilities: {downloads: true}`; its
   Save as PDF button hands the viewer the embedded PDF (the viewer sandbox
   blocks printing). Skip silently elsewhere. No docx.

## Process

### 1. Mode — one question with real numbers, Quick recommended

First run the plan (home + robots + sitemap only, seconds):

```bash
python3 <skill-dir>/scripts/collect.py https://example.com --plan
```

Then ask once, quoting its numbers: **Quick** (recommended) = homepage +
every main-menu item + one level of submenu (`quick.pages`, ~1 min);
**Full** = Quick + footer links + a per-section sample of the sitemap,
newest first (`full.pages` of `sitemap_urls`, e.g. 102 of 503); **All** =
every sitemap URL (`all.pages`, the estimate in seconds) — offer All only
when the user asks for every page. Skip the question when the request
already says. Native question UI when the harness has one; otherwise a
numbered question with lettered options, the default marked, `1a` or
`defaults` accepted.

### 2. Preamble — detect companions, state the tiers

Detect by tool presence, never by assumption:

- rolepod-uiproof tools (`audit_seo`, `measure_cwv`, `discover_flows`) → Tier B on.
- rolepod-wplab (`rolepod_wp_seo_set`) → WordPress hand-offs are executable.
- A subagent facility (Agent / scout / `spawn_agent`) → the sweep can be delegated.

Print one line: `Tier A fetch · Tier B <on|off> (rolepod-uiproof) · connectors: Phase 2`.

### 3. Collect — Tier A (always)

Run the bundled collector; it needs only Python 3, no packages:

```bash
python3 <skill-dir>/scripts/collect.py https://example.com --mode quick   # --mode full · --all · --sitemap-status
```

`--sitemap-status` adds a status-only sweep (HEAD) of every sitemap URL
not fetched — 404s, redirects, refusals — for "check every page" without
parsing 1,000 posts; `--all` fetches and parses everything. Both are
opt-in; a blog with a thousand posts stays a Quick or Full sample by
default, and the report says "sampled N of M — template findings apply to
the whole section".

It fetches the homepage, robots.txt, sitemap(s), llms.txt and the selected
pages, then writes `pages.md` (one row per page, with inbound links and
click depth), `site.json` (robots verdict per bot, sitemap facts, duplicate
titles / descriptions, near-duplicate pages, redirect chains, host
variants, link graph, detected site type) and `collect.json` under
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
out appears in the report as "could not fetch <url> (<status>)". The
collector refuses private, loopback and cloud-metadata targets; pass
`--allow-private` only for a site you run locally.

### 4. Collect — Tier B (when rolepod-uiproof is installed)

- `audit_seo` on the homepage and each money page: rendered title / meta /
  canonical / JSON-LD validity / OG / hreflang. Diff against Tier A — a
  value that exists only after JavaScript runs is itself a GEO finding.
- Full mode: `measure_cwv` on the homepage and two money pages.
- `audit_a11y` on the homepage and one booking / checkout / contact page:
  names, labels and tree integrity are the agent-actionability signal
  (Lighthouse Agentic Browsing checks the same things).
- `discover_flows` only when Tier A found no internal links on the
  homepage (JavaScript-only navigation).

Tier C (Search Console API, keyword, rank data) is Phase 2: list what it
would add under "not assessed". Exception without any key: a manual
Search Console export the user already has — run
`seo-fix-plan/scripts/gsc_csv.py --pages <sidecar>` and the
`queries-ctr-position` row moves from not assessed to assessed, with
`pages[].gsc` filled. Skip silently when there is no export.

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

Score from checklist hit-rate weighted by page role, then by site type
when `site.site_type.confidence` is `high` (table in
`references/seo-checks.md` § Site-type emphasis). Show the three findings
that drove each score. Never round up without evidence. A dimension with
no data is "not assessed (needs X)", never a number.

### 7. Report

Write the JSON sidecar first (it drives everything else), then the
markdown report, both from `references/report.md`. Render the HTML:

```bash
R=reports/seo-audit-<host>-<date>
python3 <skill-dir>/scripts/render_report.py $R.json --collect <collect.json> [--previous reports/seo-audit-<host>-<older-date>.json]
python3 <skill-dir>/scripts/export_pdf.py $R.html --out $R.pdf                                        # real PDF via an installed browser
python3 <skill-dir>/scripts/render_report.py $R.json --collect <collect.json> --artifact --pdf $R.pdf  # Claude Code only
```

Set `seo_effect` on every finding (`direct` / `indirect` / `none`). What
changes Google Search comes first in every table; `none` items (retired
rich results such as `FAQPage`, `llms.txt`) are labelled "no effect on
Google Search", listed last, and never enter the matrix, roadmap, quick
wins or the chat summary. Pass `--previous` whenever an older sidecar for
the same host exists in `reports/`: the report gains a "Since last audit" section (score deltas,
fixed / new / still-open findings by `id`) and the chat summary gets the
same line. The HTML also derives a phased roadmap (week 1 / weeks 2–3 /
month 2 / ongoing) and a quick-wins block from the priorities — no extra
input needed.

On Claude Code publish the `--artifact` file with the Artifact tool and
`capabilities: {downloads: true}` (`<title>` is the host; fonts embedded,
no external assets). If `export_pdf.py` found no browser, publish without
`--pdf`; the button then explains how to print the HTML. Then print the chat summary table and the chat priority matrix with
colored dots in the Priority column (🔴 Critical · 🟠 High · 🟡 Medium ·
🟢 Quick win), columns Priority · Issue · Dim · Effort · Impact · Owner ·
Exact change. "Exact change" carries the field and value or the snippet —
that is what lets `/seo-fix-plan`, rolepod-wplab, frontend-developer or
content-strategist execute without re-reading the audit.

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
