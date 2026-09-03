# Changelog

All notable changes to this project are recorded here. Versions follow
[Semantic Versioning](https://semver.org/). Until v1.0 the JSON sidecar
schema is additive-only but the skills may change shape at any release.

## [Unreleased]

## [0.3.1] — 2026-09-03

### Added

- **Save as PDF** button in the HTML report — calls `window.print()` only;
  the browser's print dialog makes the PDF. Next to it: "or press ⌘P /
  Ctrl+P → Save as PDF", because the Claude Artifact viewer blocks
  page-initiated downloads and may restrict print. No download link, no
  blob save, no PDF library.
- Print rules: toolbar hidden, light tokens forced in both themes, card /
  chip colours kept (`print-color-adjust: exact`), page breaks before the
  findings and the priority matrix, no breaks inside rows or cards.
- Test: the report carries exactly one `window.print()` call, the
  keyboard hint and the print rules, and no `download=`, `blob:`, jsPDF
  or `<script>`.

## [0.3.0] — 2026-09-03

### Added

- **HTML report** — `skills/seo-audit/scripts/render_report.py` (stdlib)
  renders the JSON sidecar into a self-contained page: navy cover with the
  host, mode, date, pages and tiers plus three score cards colored by band
  (8–10 On Track green, 5–7 Needs Work amber, 1–4 Critical red), executive
  summary, pages audited (title / words / schema with `--collect`), SEO /
  GEO / AEO findings tables with colored status cells, priority matrix with
  colored chips (Critical / High / Medium / Quick win) and Dim · Effort ·
  Impact · Owner · Exact change, decisions for the owner, what's working,
  not assessed, glossary in Full mode. Inline CSS only, no external assets,
  light / dark tokens, a small `@media print` block.
- **Artifact on Claude Code** — `render_report.py --artifact` emits the
  fragment the Artifact tool expects (title = host); `/seo-audit` step 7
  now publishes the HTML, not the markdown.
- **Chat priority matrix** with colored dots in the Priority column
  (🔴 Critical · 🟠 High · 🟡 Medium · 🟢 Quick win), shape in
  `references/report.md`.
- Sidecar schema (additive): optional `summary` (executive summary) and
  `scores.<dim>.status_label` (derived from the score; the renderer
  computes it when absent). `docs/report-schema.md` updated.
- Tests: `tests/static/render-report.sh` — document and artifact forms,
  every section present, three cards with the expected classes, print CSS,
  light / dark tokens in all three states, no external assets, no scripts,
  chips rendered, score → status mapping table-tested.
- Skill contract: supporting files (≤5) and scripts (≤3) are counted
  separately — scripts never enter the context window.

### Declined (owner, 2026-09-03)

- docx / PDF export of any kind. HTML + Artifact is the visual
  deliverable on every CLI; the print block is a zero-cost nicety, not a
  documented deliverable.

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
