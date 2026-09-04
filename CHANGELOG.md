# Changelog

All notable changes to this project are recorded here. Versions follow
[Semantic Versioning](https://semver.org/). Until v1.0 the JSON sidecar
schema is additive-only but the skills may change shape at any release.

## [Unreleased]

## [0.9.1] — 2026-09-04

### Fixed

- Print / PDF kept the desktop grids (three score cards, three roadmap
  cards, five band cards) — an A4 page is narrower than the 960 px mobile
  breakpoint, so the PDF had collapsed them to two columns.

## [0.9.0] — 2026-09-04

### Added

- **Real PDF.** `skills/seo-audit/scripts/export_pdf.py` (stdlib) prints
  the HTML report to `reports/seo-audit-<host>-<date>.pdf` with the print
  engine of a Chromium-family browser already on the machine — Google
  Chrome, Chromium, Microsoft Edge, Brave, Arc, or the Chromium that
  rolepod-uiproof's Playwright keeps in its cache (`ROLEPOD_SEO_CHROME`
  forces a binary). Same page as the HTML, fonts embedded; no PDF
  library, no LibreOffice. Chrome's new headless mode does not always
  exit after writing, so the exporter waits for the file to settle and
  ends the process itself. No browser → exit 2 with the ⌘P / Ctrl+P hint.
- **Save as PDF inside the Claude artifact.** `render_report.py --pdf`
  embeds that PDF; the button hands it to the viewer through the Artifact
  `downloads` capability (`capabilities: {downloads: true}` at publish),
  because the viewer sandbox blocks `window.print()`. Outside a viewer, or
  without an embedded PDF, the button still opens the browser's print
  dialog. One inline script, no external code.
- `/seo-audit` step 7 runs the exporter and publishes with the capability;
  `tests/static/export-pdf.sh` produces a real PDF when a browser exists
  and checks the hint path otherwise.

## [0.8.1] — 2026-09-04

### Fixed

- GEO and AEO dimension headers lost their 34 px top margin (the
  first-child rule matched every dimension section, not only the first);
  they now sit clear of the card above, as in the design.

## [0.8.0] — 2026-09-04

### Changed

- **Report matches the design export exactly**: every font size, weight,
  letter-spacing, padding, gap, radius and colour was measured from the
  owner's mock element by element (44 px headline, Instrument Sans
  labels, JetBrains Mono chips and evidence, accent top borders on the
  fix-first / quick-win and finding cards, the design's `#F5F4FB` page with
  white cards, dark hero, band cards, glossary grid).
- **Fonts embedded**: `skills/seo-audit/assets/fonts.css` carries
  Instrument Sans and JetBrains Mono (variable woff2, latin + latin-ext,
  SIL Open Font License notice included) so the report renders identically
  offline, in the Claude Artifact viewer and in print. The report makes no
  external request; the Google Fonts link remains only as a fallback when
  the asset file is missing.

## [0.7.2] — 2026-09-03

### Changed

- Report page background is white and the report is a single light theme
  on purpose (no dark-mode overrides), so it no longer turns dark inside a
  dark viewer; cards keep a 1 px border on the white page. Hero unchanged.

## [0.7.1] — 2026-09-03

### Fixed

- Static test for the cover headline (the sample sidecar now carries a
  written `headline`; the generated fallback is unit-tested instead).
  0.7.0 was tagged with this one test red — CI on that tag is expected to
  fail; nothing in the shipped skills changed.

## [0.7.0] — 2026-09-03

### Changed

- **HTML report redesigned** after the owner's Claude Design mock: sticky
  sidebar (host, mode · date, numbered section nav, lime Save as PDF), dark
  hero with a one-sentence `headline` and three ring-gauge score cards,
  numbered section headers, fix-first / quick-wins cards, pages table in a
  card, one card per open finding with Evidence and Fix panels plus an
  "Also observed" list, priority matrix as cards with a Verify panel,
  roadmap cards + a dark Ongoing card (Decide / Prove / Watch / Re-audit),
  owner-call cards, "Working" strength cards, not-assessed cards, the
  optional "no effect on Google Search" list, band cards, glossary cards.
  Instrument Sans + JetBrains Mono from Google Fonts with system fallbacks
  (the only external request); light / dark tokens; print rules keep the
  colours and drop the sidebar.
- Sidecar (additive): optional top-level `headline` for the cover; the
  renderer generates a count-based fallback.

## [0.6.0] — 2026-09-03

### Added

- **`findings[].seo_effect`** (`direct` | `indirect` | `none`, additive,
  schema v1). Everything that changes Google Search comes first in every
  table; `none` items (FAQ / HowTo rich results retired, `llms.txt`
  ignored, `speakable`) are labelled **"no effect on Google Search"**,
  listed last in their section and in a dedicated "No effect on Google
  Search — optional" section after the roadmap, and never enter the
  priority matrix, the roadmap, the quick wins, the per-page counts or the
  chat summary. The renderer infers `none` for those signals when the
  field is absent; an explicit value always wins. Score cards show the
  optional count separately. References mark the rows concerned.

## [0.5.1] — 2026-09-03

### Changed

- Docs only: the last examples that still read as "add FAQ schema for
  Google" now carry the 2026-05-07 caveat (`/seo-schema` types table,
  rules and examples; `/seo-page-brief` example; README skills table).
  Behaviour was already correct since 0.4.0.

## [0.5.0] — 2026-09-03

### Added

- **hreflang reciprocity** in the collector: every page's `hreflang`
  alternates are recorded; Full mode fetches same-origin alternates that
  nav and sitemap missed; `site.hreflang` reports pages that do not list
  themselves, pages without `x-default`, non-reciprocal pairs (alternate
  does not link back — Google ignores those) and, in Quick mode, how many
  alternates went unchecked instead of guessing. Fixture gains a Thai /
  English pair with one broken direction.
- **Site-type emphasis** (guidance, no code): `seo-checks.md` § Site-type
  emphasis lists, per detected type (local / ecommerce / publisher / saas /
  agency), the signals that move one severity step up and weigh more when
  `site.site_type.confidence` is `high`; `/seo-audit` step 6 and
  `/seo-page-brief` read it; the brief template carries the type.

### Deferred (owner, 2026-09-03)

- Anything that needs an API key (PageSpeed Insights / CrUX field CWV,
  Search Console, Bing) stays Phase 2. The unauthenticated PSI quota is
  shared and was already exhausted (HTTP 429) on the first probe, so a
  keyless script would not be reliable. Phase 1 ends inside the plugin.

## [0.4.1] — 2026-09-03

### Added

- HTML report: each dimension is broken down **by signal group** (schema ·
  technical · content · trust · answer · other) on the score cards and
  under each findings header, so the reader sees where a 6/10 comes from
  without a fourth dimension. Groups are matched by keyword on the free-text
  `signal`, `signal_group()` is table-tested.

## [0.4.0] — 2026-09-03

### Changed — facts

- **FAQ rich results are gone for every site** (Google, 2026-05-07).
  `schema-minimums.md` and `aeo-checks.md` no longer describe the 2023
  government / health restriction; a visible FAQ without `FAQPage` is now a
  low / info structural signal, never a defect, and `QAPage` is named for
  real user Q&A. `validate.py` warns on `FAQPage`, `HowTo` (2023-09-13) and
  the seven types Google retired on 2025-06-12 (`ClaimReview`, `CourseInfo`,
  `EstimatedSalary`, `LearningVideo`, `SpecialAnnouncement`,
  `VehicleListing`) with the date and a Google-owned source; the static
  gate pins the reference table and the script together and rejects
  non-Google sources.
- **llms.txt**: Google's AI optimization guide (2026-05-15, updated
  2026-07-10) says Search ignores it — the GEO reference now reports
  presence only and never recommends it.
- New GEO row **agent actionability** (what Lighthouse's Agentic Browsing
  category checks): hands to rolepod-uiproof `audit_a11y` + `measure_cwv`
  or `npx lighthouse --only-categories=agentic-browsing`; "not assessed"
  until one ran. `/seo-audit` Tier B adds `audit_a11y` on the homepage and
  one booking / checkout / contact page.
- Dated claims in the references now carry their source URL.

### Added — collector

- Refuses private, loopback, link-local and cloud-metadata targets, also as
  redirect targets (`--allow-private` for a site you run locally). Sitemap
  XML is capped at 20 MiB and rejected when it carries a DOCTYPE; decoding
  honours BOM → header charset → `<meta charset>`.
- Link graph among fetched pages: `inlinks` and click `depth` per page,
  `link_graph.unreachable_from_home` and `low_inlinks` (money / answer /
  trust pages with ≤1 inbound link). Near-duplicate pages by word-shingle
  overlap (`near_duplicates[]`). Response-header facts (`security.hsts`,
  CSP, `X-Content-Type-Options`, server). Weighted **site type** detection
  (saas / ecommerce / local / publisher / agency with confidence and the
  signals). New `pages.md` column `in/depth`.

### Added — report

- Sidecar (additive, still schema v1): optional `findings[].verify`,
  `findings[].leading_indicator`, `site.site_type`.
- HTML: Fix-first and Quick-wins boxes in the summary, site type line,
  fail / warn / pass counts on the score cards and section headers,
  findings-per-page and links-in / depth in the pages table, a Verify
  column in the matrix, a **roadmap** derived from priorities (week 1 /
  weeks 2–3 / month 2 / ongoing with decisions, not-assessed and leading
  indicators), a "How to read the scores" section. `--previous
  older.json` adds **Since last audit** (score deltas, fixed / new / still
  open by finding id) and prints the same line for the chat summary.
- Chat summary gains Quick wins and Since-last-audit rows.
- `seo-checks.md`: per-role word-count floors and location-page thresholds
  (heuristics), inbound-link / click-depth / HSTS / near-duplicate rows.
  `handoff-formats.md`: a leading-indicator line for content items.

### Tests

- Skill lint now resolves every `references/` / `scripts/` / `templates/`
  mention in every file of a skill and fails on orphan supporting files.
- Fixture: collector refusal paths, link graph, site type, security
  headers, near-duplicates; render: roadmap, quick wins, delta, verify
  column, methodology; validator: retired-type warning and placeholder
  failure.

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
