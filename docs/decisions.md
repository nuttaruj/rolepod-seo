# Decisions — how the scaffold resolved the brief's open items

The design brief lives outside git. These are the choices made during the
scaffold that later sessions need; the reasoning is short on purpose.

| # | Item | Decision | Why |
|---|---|---|---|
| O1 | Rendered `plugins/` tree | Yes — `plugins/rolepod-seo/` is a real copy of `skills/` + the Claude and Codex `plugin.json`, produced by `make render`; `tests/static/parity.sh` fails on drift | Same shape as rolepod-uiproof / rolepod-wplab (marketplaces point at `./plugins/<name>`); a copy survives every CLI's checkout, a symlink does not |
| O2 | JSON sidecar schema v1 | `docs/report-schema.md` for consumers, `skills/seo-audit/references/report.md` § 3 for the model; additive-only; `tests/static/report-schema.sh` checks every documented field appears in the skill copy and validates `tests/fixtures/sample-report.json` | One shape, two audiences; the test is the anti-drift |
| O3 | AI-bot robots policy | Reported as a decision with three options (open / block training only / block all) in `geo-checks.md`; `severity: info`, `owner: human` in the sidecar; an accidental `Disallow: /` under `*` stays an SEO critical | Owner's call, never a defect (brief 02) |
| O4 | `schema-minimums.md` sharing | Single source in `seo-schema/references/`; `seo-audit/references/seo-checks.md` carries a compact required-properties table and a cross-skill pointer; `validate.py` embeds the Required column and `tests/static/schema-minimums.sh` pins doc ↔ script | No symlink, no duplicate long file; the ≤5-files cap holds on both skills |
| O5 | Fixture site | `tests/fixtures/site-a` — fictional plumber, nine pages, `__BASE__` substituted at serve time; defects listed in its README (cross-domain canonical, FAQ without schema, noindex in sitemap, 404 in sitemap, blocked AI bots, duplicate description, two H1s, missing alt) | Every defect is something the collector must surface; golden tables pin the output |
| — | Tooling | bash + python3 only; no Node, no npm, no `package.json` | Skills-only plugin installs from GitHub on every CLI; Python stdlib is the one runtime every target has |
| — | Collector as a shipped script | `skills/seo-audit/scripts/collect.py` is part of the skill, not just a test helper | Makes Tier A deterministic and cheap on every CLI; a scout runs one command and returns a table |
| — | Release staging | 0.1.0 = `/seo-audit`; 0.2.0 = `/seo-fix-plan` + `/seo-schema` + `/seo-page-brief` (brief planned page-brief for 0.3.0) | page-brief is the content half of the fix-plan hand-off; shipping it with fix-plan avoided a dangling pointer for one release |

Still owned by the brief (not re-decided here): sibling repo, skills-only
Phase 1, clean-room rewrite, deliverables, tool reuse, effort ceiling
`xhigh`, pointer-only parent patches.
