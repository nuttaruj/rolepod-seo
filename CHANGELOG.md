# Changelog

All notable changes to this project are recorded here. Versions follow
[Semantic Versioning](https://semver.org/). Until v1.0 the JSON sidecar
schema is additive-only but the skills may change shape at any release.

## [Unreleased]

## [0.2.0] — 2026-09-03

### Added

- **`/seo-fix-plan`** — loads the audit sidecar (or the priority matrix),
  keeps `fail` / `warn` findings, orders them crawl blockers → indexation
  → canonical / duplicates → redirects → schema → content → polish, and
  emits one block per item with owner, exact change, dependency and the
  verification command. Hand-off formats per owner in
  `references/handoff-formats.md`: rolepod-wplab payloads
  (`rolepod_wp_seo_set`, `rolepod_wp_redirect_set`, plugin settings),
  frontend-developer file + snippet, content-strategist brief pointer,
  human decisions, rolepod-uiproof proof-first. Executes approved WordPress
  items only, under the companion's prod guard.
- **`/seo-schema`** — JSON-LD per page type from facts on the page,
  `@graph` with stable `@id`s, required + recommended properties per type
  in `references/schema-minimums.md` (14 types; single source — the
  seo-audit reference carries the compact table), placement hand-off per
  platform. `scripts/validate.py` (stdlib) parses a file, URL or stdin,
  walks the graph and reports missing required properties; `make
  test-static` keeps the doc and the validator in lockstep.
- **`/seo-page-brief`** — one-page content brief for content-strategist:
  intent per query, the 40–60-word direct answer (the only copy in the
  brief), question-phrased outline with shapes and lengths, entities /
  facts / proof with sources, E-E-A-T elements, schema type with required
  fields, internal links in and out, verification columns.
  `templates/page-brief.md` is the artifact shape. Landed a release
  earlier than the roadmap's 0.3.0 because it shares the fix-plan hand-off.
- Collector: `site.platform_hints` (generator meta + WordPress / Next.js /
  Shopify / Wix / Squarespace / Webflow / HubSpot / Framer / Astro /
  Drupal / Joomla signals) so `/seo-fix-plan` can pick the owner; CA-bundle
  discovery for https on python.org macOS builds; `--insecure` recorded as
  `tls_verify: false`; shallow-first key-page selection in Quick mode.
- `docs/decisions.md` — how the brief's open items were resolved.

## [0.1.0] — 2026-09-03

### Added

- **`/seo-audit`** — Quick (home + up to 6 key pages) or Full (every
  meaningful page) audit across SEO, GEO and AEO. Each dimension scored 1–10
  with the three findings that drove the score; every finding quotes the
  page and the tag. Deliverables: chat summary table, markdown report,
  JSON sidecar (`rolepod-seo/report` schema v1), Artifact on Claude Code.
- **Tier A collector** `skills/seo-audit/scripts/collect.py` — Python
  stdlib only. Fetches homepage, robots.txt, sitemap(s), llms.txt and the
  selected pages; writes `pages.md` / `pages.tsv` (one row per page),
  `site.json` (robots verdict per AI bot, sitemap facts, duplicates,
  redirect chains, host variants) and `collect.json`.
- **Tier B** hooks into rolepod-uiproof when installed: `audit_seo` on
  money pages, `measure_cwv` in Full mode, `discover_flows` for JS-only nav.
- References: `seo-checks.md`, `geo-checks.md` (AI-bot policy reported as
  a decision, never a defect), `aeo-checks.md`, `report.md` (three
  deliverable shapes, single source).
- Plugin manifests for Claude Code, Codex, Cursor, Gemini at 0.1.0; shipped
  tree under `plugins/rolepod-seo/` (`make render`).
- Tests: `make test-static` (manifests parse + version lockstep, skill
  contract, shipped-tree parity, report-schema drift, clean-room guard) and
  `make test-fixture` (collector run against `tests/fixtures/site-a`
  with golden tables). No Node, no LLM in tests.
- Docs: `docs/report-schema.md` (sidecar v1 for consumers),
  `docs/cli-support.md`.

### Not in this release

- `/seo-fix-plan`, `/seo-schema`, `/seo-page-brief` (shipped in 0.2.0).
- Any MCP server, hook, or connector (Phase 2).
