# Page brief — <path> · <date>

**Status today:** <existing: one line from the collector row (words, H1, schema, author) | new page>
**Role:** <home | money | trust | blog | answer> · **Site type:** <saas | ecommerce | local | publisher | agency | unknown> · **Canonical URL:** <absolute url>
**Audience:** <who searches, what they know, what they decide next>

## Target queries and intent

| Query | Intent | Priority | Why this query |
|---|---|---|---|
| <primary> | <informational / commercial / transactional / navigational / local> | primary | <one clause> |
| <secondary> | … | secondary | … |

Dropped: <query — reason>, …

## Meta

- Title (≤ 60): `<…>`
- Description (≤ 160): `<…>`
- H1: `<…>`

## Direct answer (40–60 words, appears directly under the H1)

> <the answer — every fact sourced; unknown facts marked [owner to confirm]>

Sources: <page / user / primary source per fact>

## Outline

| Heading | Level | Covers | Shape | Length |
|---|---|---|---|---|
| <question-phrased heading> | H2 | <query facet> | <paragraph / steps / table / definition> | <~n words> |
| … | H3 | … | … | … |

Total target: <n> words (<role rule>). Cut: <sections / paragraphs to remove on the existing page, or "—">.

## Entities, facts, proof

- Name exactly: <canonical product / person / brand names>
- Facts to include (with source): <number — source>, …
- Proof: <case / certification / number — source>
- Cite out: <primary source url — what it supports>
- Glossary terms: <term — one-line definition> (or "—")

## E-E-A-T

- Author: <name, credential, author page url> — [owner to confirm] if absent
- Visible date: <published / updated>
- First-hand signal: <what the author has done / measured>

## Schema

- Type: `<Type>` — required: <fields from seo-schema/references/schema-minimums.md>
- Facts available on the page after the rewrite: <list>; ask for: <list or "—">
- `FAQPage` only if the page carries a visible FAQ; mirror verbatim.

## Internal links

- In (add links to this page from): <page — anchor text>, …
- Out (this page links to): <page — anchor text>, …

## Verification after publish

`collect.py <url> --urls one.txt` → `word_count ≥ <n>`, `question_headings ≥ <n>`,
`author_present = y`, `date_visible = y`, `schema_types` includes `<Type>`.
Optional: rolepod-uiproof `audit_seo` for rendered checks.

## Hand-off

content-strategist (audience: prospect) · brief: `reports/seo-brief-<slug>-<date>.md` · ask: <one line>
