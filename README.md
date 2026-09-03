# rolepod-seo

SEO + GEO + AEO site audit skills for AI coding agents. A sibling of
[`rolepod`](https://github.com/nuttaruj/rolepod): install it in the projects
that need search work, and it stays out of every other session.

`/seo-audit` fetches what a crawler sees, checks it against three lenses,
scores each 1–10 with quoted evidence, and ends in a priority matrix that
other tools can execute:

- **SEO** — classic search: titles, meta, headings, canonicals, robots,
  sitemap, redirects, structured data, internal links, content depth.
- **GEO** — generative engines (AI Overviews, ChatGPT search, Perplexity):
  E-E-A-T surface, entity clarity, citation-friendly structure, rich
  schema, AI-bot crawl policy reported as a decision.
- **AEO** — answer engines (featured snippets, People Also Ask, voice):
  direct-answer blocks, question headings, FAQ / HowTo / Speakable schema,
  local signals.

Phase 1 is **skills only** — no MCP server, no hooks, zero per-session
tool-schema cost. The audit needs Python 3 and nothing else.

## What you get

| Deliverable | Where |
|---|---|
| Chat summary | one table: pages · date · three scores with band · top 3 priorities · biggest strength |
| Markdown report | `reports/seo-audit-<host>-<date>.md` — findings tables with evidence, priority matrix, what's working, glossary |
| JSON sidecar | `reports/seo-audit-<host>-<date>.json` — stable, additive schema ([docs/report-schema.md](docs/report-schema.md)) |
| Artifact | on Claude Code, the report as a private page |

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

## Works with

| Companion | What it adds | Detected how |
|---|---|---|
| [rolepod-uiproof](https://github.com/nuttaruj/rolepod-uiproof) | rendered-DOM checks (`audit_seo`), Core Web Vitals (`measure_cwv`), JS-only nav discovery (`discover_flows`) | tool presence — Tier B turns on |
| [rolepod-wplab](https://github.com/nuttaruj/rolepod-wplab) | executes WordPress fixes: `rolepod_wp_seo_set` (Yoast / RankMath), `rolepod_wp_redirect_set` | tool presence — hand-offs become executable |
| [rolepod](https://github.com/nuttaruj/rolepod) parent | `content-strategist` writes the copy, `frontend-developer` writes the code, a scout runs the sweep on the cheap tier | standard role delegation |

Nothing breaks when a companion is absent: the report marks the checks it
would have added as "not assessed (needs …)".

## Roadmap

- **0.1.0** — `/seo-audit` (this release).
- **0.2.0** — `/seo-fix-plan` (hand-offs grouped by owner, dependency
  order) and `/seo-schema` (JSON-LD per page type with required-property
  validation).
- **0.3.0** — `/seo-page-brief` (brief for content-strategist: intent,
  answer block, question set, schema, internal links).
- **Phase 2** — connectors as a small MCP server in this repo: Google
  Search Console (read-only), keyword / SERP data, rank and AI-visibility
  tracking, log-file bot analysis. Each only when a real need is stated.

Not planned: a hosted SaaS, backlink crawling, programmatic content
factories.

## Development

```bash
make test          # test-static + test-fixture (bash + python3, no Node)
make render        # copy skills/ + manifests into plugins/rolepod-seo/
make version-bump VERSION=0.2.0
make serve-fixture # tests/fixtures/site-a on :8765 for a manual audit run
```

`tests/fixtures/site-a` is a tiny fictional plumbing site with deliberate
defects (cross-domain canonical, FAQ without schema, noindex page in the
sitemap, blocked AI bots …) — see its README.

## License

MIT — see [LICENSE](LICENSE). The audit methodology is written from
scratch for this repo; the checks it encodes are industry-standard facts.
