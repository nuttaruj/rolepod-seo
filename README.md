<p align="center"><img src="docs/assets/rolepod-seo-banner.png" alt="Rolepod SEO — search optimization" width="100%"></p>

# rolepod-seo

SEO + GEO + AEO site audit skills for AI coding agents. A sibling of
[`rolepod`](https://github.com/nuttaruj/rolepod): install it in the projects
that need search work, and it stays out of every other session.

Four skills, one workflow: `/seo-audit` fetches what a crawler sees,
checks it against three lenses, scores each 1–10 with quoted evidence and
ends in a priority matrix; `/seo-fix-plan` turns that matrix into
hand-offs other tools execute; `/seo-schema` writes and validates the
JSON-LD; `/seo-page-brief` briefs the copy. The lenses:

- **SEO** — classic search: titles, meta, headings, canonicals, robots,
  sitemap, redirects, structured data, internal links, content depth.
- **GEO** — generative engines (AI Overviews, ChatGPT search, Perplexity):
  E-E-A-T surface, entity clarity, citation-friendly structure, rich
  schema, AI-bot crawl policy reported as a decision.
- **AEO** — answer engines (featured snippets, People Also Ask, voice):
  direct-answer blocks, question headings, FAQ / HowTo / Speakable schema
  as structural signals only (Google retired their rich results),
  local signals.

Phase 1 is **skills only** — no MCP server, no hooks, zero per-session
tool-schema cost. The audit needs Python 3 and nothing else.

## The four skills

| Skill | Ask it | Gives you |
|---|---|---|
| `/seo-audit` | "audit example.com for SEO and AI search" | Quick / Full audit, three scores with evidence, markdown report + JSON sidecar, priority matrix |
| `/seo-fix-plan` | "apply the audit" | findings in dependency order, one block per item with owner, exact payload / snippet / brief and a verification command; runs approved WordPress writes through rolepod-wplab |
| `/seo-schema` | "add LocalBusiness schema to /contact" | JSON-LD from facts on the page, validated (`scripts/validate.py`, stdlib; warns on types whose Google rich result was retired, e.g. `FAQPage`), placement hand-off per platform |
| `/seo-page-brief` | "rewrite /pricing for '<query>'" | intent, 40–60-word answer block, question outline, entities and proof, schema, internal links — for content-strategist |

## What you get from an audit

| Tier | Deliverable | What it is |
|---|---|---|
| Chat | summary + priority matrix | one table (pages · date · three scores with band · top 3 priorities · biggest strength) and the matrix with colored priority dots (🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Quick win) |
| Files | markdown report + JSON sidecar | `reports/seo-audit-<host>-<date>.md` (findings tables with evidence, priority matrix, what's working, glossary) and `.json` with a stable, additive schema ([docs/report-schema.md](docs/report-schema.md)) that the other skills and outside tools consume |
| Visual | HTML report → Save as PDF (browser print) | `reports/seo-audit-<host>-<date>.html` rendered from the sidecar by a stdlib script: sidebar with numbered navigation, dark hero with a one-line headline and three ring-gauge score cards, fix-first / quick-wins cards, pages table, one card per finding with Evidence and Fix panels, priority matrix cards with a Verify panel, a roadmap (week 1 / weeks 2–3 / month 2 / ongoing), owner calls, strengths, not assessed, the optional "no effect on Google Search" list last, band cards, glossary. `--previous older.json` adds "Since last audit". Inline CSS, fonts embedded (Instrument Sans + JetBrains Mono, OFL), no external requests, single light theme. A "Save as PDF" button opens the browser's print dialog (or ⌘P / Ctrl+P) |
| PDF | `reports/seo-audit-<host>-<date>.pdf` | made by `export_pdf.py` with the print engine of a Chromium-family browser already on the machine (Chrome, Chromium, Edge, Brave, or rolepod-uiproof's Chromium) — same page as the HTML, fonts embedded; no PDF library |
| Claude Code | Artifact | the same HTML published as a private page with the PDF embedded; its Save as PDF button hands the file to the viewer (the viewer blocks printing) |

No docx export and no PDF library: the PDF is the browser's own print of
the HTML report ([docs/decisions.md](docs/decisions.md)).

Every finding quotes the page and the tag. "Missing" is claimed only after
every fetched page was checked. Anything the plain fetch cannot see (Core
Web Vitals, rendered DOM, Search Console data) is listed as "not assessed"
with the tool that would prove it.

## Install

### Claude Code

```bash
claude plugin marketplace add nuttaruj/rolepod-seo
claude plugin install rolepod-seo@rolepod-seo

# update
claude plugin marketplace update rolepod-seo
claude plugin install rolepod-seo@rolepod-seo
```

### Codex CLI

```bash
codex plugin marketplace add nuttaruj/rolepod-seo
codex plugin add rolepod-seo@rolepod-seo
```

Codex plugins are global; this plugin ships no tools, so the only
per-session cost is the skill index.

### Gemini CLI

```bash
gemini extensions install https://github.com/nuttaruj/rolepod-seo
```

Skills are auto-discovered from `skills/<name>/SKILL.md`. Restart the CLI.

### Cursor / opencode / anything else

Copy `skills/` into the workspace's skill directory. The collector is a
single Python file and runs anywhere Python 3 does.

See [docs/cli-support.md](docs/cli-support.md) for the per-CLI matrix.

## Quick start

```text
Audit https://example.com for SEO and AI search
```

The skill asks once — Quick (home + up to 6 key pages) or Full (every
meaningful page) — runs the collector, and writes the report:

```bash
python3 skills/seo-audit/scripts/collect.py https://example.com --mode quick
# → .rolepod-seo/collect-example.com-<date>/pages.md · site.json · collect.json
```

Add `.rolepod-seo/` and `reports/` to your `.gitignore` if you do not want
audit artifacts in git.

The collector refuses private, loopback and cloud-metadata targets (also
as redirect targets); pass `--allow-private` for a site you run locally.
It also builds the internal link graph of the fetched pages (inbound links,
click depth), flags near-duplicate pages, checks hreflang reciprocity on
multilingual sites and detects the site type (SaaS / e-commerce / local /
publisher / agency) so the report can say what matters most for that kind
of site.

## Works with

| Companion | What it adds | Detected how |
|---|---|---|
| [rolepod-uiproof](https://github.com/nuttaruj/rolepod-uiproof) | rendered-DOM checks (`audit_seo`), Core Web Vitals (`measure_cwv`), JS-only nav discovery (`discover_flows`) | tool presence — Tier B turns on |
| [rolepod-wplab](https://github.com/nuttaruj/rolepod-wplab) | executes WordPress fixes: `rolepod_wp_seo_set` (Yoast / RankMath), `rolepod_wp_redirect_set` | tool presence — hand-offs become executable |
| [rolepod](https://github.com/nuttaruj/rolepod) parent | `content-strategist` writes the copy, `frontend-developer` writes the code, a scout runs the sweep on the cheap tier | standard role delegation |

Nothing breaks when a companion is absent: the report marks the checks it
would have added as "not assessed (needs …)".

## Roadmap

- **0.1.0** — `/seo-audit`.
- **0.2.0** — `/seo-fix-plan`, `/seo-schema`, `/seo-page-brief`.
- **0.3.0** — visual tier: HTML report rendered from the sidecar, Artifact
  on Claude Code, colored chat priority matrix.
- **0.4.x** — facts refreshed (FAQ / retired rich results / llms.txt),
  collector hardening, link graph + site type, roadmap + quick wins +
  since-last-audit, signal-group breakdown.
- **0.5.0** — hreflang reciprocity, site-type emphasis in scoring and
  briefs (this release). Phase 1 is complete: everything runs inside the
  plugin with Python 3 and no key.
- **Phase 2** — connectors as a small MCP server in this repo: Google
  Search Console (read-only), keyword / SERP data, rank and AI-visibility
  tracking, log-file bot analysis. Each only when a real need is stated.

Not planned: a hosted SaaS, backlink crawling, programmatic content
factories.

## Development

```bash
make test          # test-static + test-fixture (bash + python3, no Node)
python3 skills/seo-audit/scripts/render_report.py tests/fixtures/sample-report.json --out /tmp/report.html   # see the HTML tier
python3 skills/seo-audit/scripts/export_pdf.py /tmp/report.html                                         # and the PDF
make render        # copy skills/ + manifests into plugins/rolepod-seo/
make version-bump VERSION=0.2.0
make serve-fixture # tests/fixtures/site-a on :8765 for a manual audit run
```

Decisions taken during the scaffold: [docs/decisions.md](docs/decisions.md).

`tests/fixtures/site-a` is a tiny fictional plumbing site with deliberate
defects (cross-domain canonical, FAQ without schema, noindex page in the
sitemap, blocked AI bots …) — see its README.

## License

MIT — see [LICENSE](LICENSE). The audit methodology is written from
scratch for this repo; the checks it encodes are industry-standard facts.
