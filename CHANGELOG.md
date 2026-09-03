# Changelog

All notable changes to this project are recorded here. Versions follow
[Semantic Versioning](https://semver.org/). Until v1.0 the JSON sidecar
schema is additive-only but the skills may change shape at any release.

## [Unreleased]

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

- `/seo-fix-plan`, `/seo-schema` (planned 0.2.0), `/seo-page-brief` (0.3.0).
- Any MCP server, hook, or connector (Phase 2).
