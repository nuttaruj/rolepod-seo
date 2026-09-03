# JSON sidecar — `rolepod-seo/report` schema v1

Every `/seo-audit` run writes `reports/seo-audit-<host>-<date>.json` next to
the markdown report. The shape is stable and **additive**: new keys may
appear in later versions; existing keys keep their meaning. Consumers must
ignore unknown keys. The model-facing copy of this shape lives in
`skills/seo-audit/references/report.md` § 3; `make test-static` checks that
every field below is present there.

## Top level

| Field | Type | Meaning |
|---|---|---|
| `schema` | string | always `rolepod-seo/report` |
| `schema_version` | int | `1` |
| `generated_at` | string | ISO 8601 UTC |
| `site` | object | `base_url`, `host`, `mode` (`quick` \| `full`) |
| `collection` | object | what was collected and how (below) |
| `scores` | object | `seo`, `geo`, `aeo` (below) |
| `findings` | array | one object per finding (below) |
| `strengths` | array | `{ signal, page, evidence }` — same evidence standard as findings |
| `not_assessed` | array | `{ signal, needs, installed }` — what a tool or connector would add |
| `pages` | array | `{ url, role, status, in_sitemap }` — every page selected, fetched or not |

## `collection`

| Field | Type | Meaning |
|---|---|---|
| `collection.tiers` | object | `{ a, b, c }` booleans — plain fetch / rolepod-uiproof / connectors |
| `collection.tools` | array | tool names used, e.g. `collect.py`, `rolepod-uiproof.audit_seo` |
| `collection.pages_selected` | int | pages chosen for the run |
| `collection.pages_fetched` | int | pages that returned 200 |
| `collection.collect_path` | string | directory of the collector output (`pages.tsv`, `site.json`, `collect.json`) |

## `scores.<dimension>`

| Field | Type | Meaning |
|---|---|---|
| `scores.seo.score` | int 1–10 | absent when `band` is `not-assessed` |
| `scores.seo.band` | enum | `critical` (1–3) \| `below-baseline` (4–5) \| `solid` (6–7) \| `strong` (8–9) \| `model` (10) \| `not-assessed` |
| `scores.seo.drivers` | array of string | the top findings that drove the score, each naming a page |

`geo` and `aeo` carry the same three fields.

## `findings[]`

| Field | Type | Meaning |
|---|---|---|
| `findings[].id` | string | stable per site: `<dimension>-<signal>-<slug>` |
| `findings[].dimension` | enum | `seo` \| `geo` \| `aeo` |
| `findings[].signal` | string | the check name from the references (e.g. `canonical`, `faq-schema`, `author`) |
| `findings[].page` | string | absolute URL, or `site` for cross-page findings |
| `findings[].severity` | enum | `critical` \| `high` \| `medium` \| `low` \| `info` |
| `findings[].status` | enum | `fail` \| `warn` \| `pass` \| `not-assessed` |
| `findings[].evidence` | string | the quoted text / tag / URL |
| `findings[].fix` | string | the exact change: field + value, or the snippet |
| `findings[].owner` | enum | `uiproof` \| `wplab` \| `frontend-developer` \| `content-strategist` \| `human` |
| `findings[].effort` | enum | `S` \| `M` \| `L` |
| `findings[].impact` | enum | `H` \| `M` \| `L` |
| `findings[].priority` | enum | `critical` \| `high` \| `medium` \| `quick-win` |

AI-bot crawl policy is emitted with `severity: info`, `status: pass`, and
`owner: human` — it is a decision, not a defect (brief 02).

## Collector output (`collect.json`) — not the sidecar

`skills/seo-audit/scripts/collect.py` writes `collect.json` with
`tool: rolepod-seo/collect`, `version: 1`, `pages[]` (raw per-page facts:
title, description, headings, canonical, robots, word count, schema types,
author / FAQ signals …) and `site` (robots verdict per bot, sitemap facts,
duplicates, redirect chains, host variants). It is an input to the audit;
the sidecar above is the output. Both are additive.

## Sample

`tests/fixtures/sample-report.json` — a hand-written sidecar for the
fixture site, validated by `tests/static/report-schema.sh`.
