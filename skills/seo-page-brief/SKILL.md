---
name: seo-page-brief
description: Write a content brief for one page (existing or new) so a writer can produce copy that ranks and gets cited — search intent, the 40–60-word direct answer, the H2/H3 question set, entities and facts to name, sources to cite, schema type with required fields, internal links in and out, word-count target by page role, E-E-A-T elements. Hands the brief to the rolepod content-strategist; never writes the copy. Use when asked to "write / rewrite page X for query Y", "content brief", or when /seo-audit or /seo-fix-plan flagged thin or unfocused content.
---

# /seo-page-brief

Produces the brief, not the prose. The brief is precise enough that
content-strategist (audience: prospect) can write the page without a
follow-up question, and `/seo-audit` can verify the result by columns.

Parent judgment applies unchanged (verify-first, simplest viable, effort
ceiling `xhigh`).

## When to use

- "Write / rewrite <page> for <query>", "brief for the pricing page".
- `/seo-audit` findings: thin content, no answer block, no question
  headings, missing E-E-A-T elements, topic unfocused.
- A new page that must earn a query before it exists.

## When NOT to use

- The copy itself → content-strategist with this brief.
- Site-wide problems → `/seo-audit`; a list of fixes → `/seo-fix-plan`.
- Keyword research with volumes → Phase 2; the brief works from the
  queries the user gives or the ones the page already targets.

## Inputs

- Page URL, or "new page" with its intended path and role
  (home / money / trust / blog / answer).
- Target queries — ask once if none given; otherwise infer 3–5 from the
  audit (title, H1, existing question headings) and state them.
- Audience: who searches, what they already know, what they decide next.
- Optional: the audit sidecar (evidence for what is wrong today),
  competitor URLs the user names (fetched only if named).

## Outputs

- `reports/seo-brief-<slug>-<date>.md` from `templates/page-brief.md`.
- Chat summary: intent, the answer sentence, the heading list, the
  hand-off line to content-strategist.

## Process

### 1. Facts first

Existing page: run the collector on it (`collect.py <url> --urls one.txt`
from the seo-audit skill, or reuse a recent `collect.json`) and read the
row: title, H1, headings, word count, schema, author, date, links. New
page: collect the two or three most related existing pages instead, for
internal links and tone.

### 2. Intent

Classify each target query: informational / commercial / transactional /
navigational / local. Mixed intent → the page serves the dominant one and
links to the other. Write the reader's decision after reading in one line.

### 3. The answer block

Draft the 40–60-word plain answer to the primary query — the sentence a
snippet, a voice assistant or an AI answer would lift. Facts in it must
be true and sourced (the page, the user, a primary source). This is the
one piece of copy the brief contains, because everything else hangs on it.

### 4. Structure

- H1: one, the query in natural words.
- H2 / H3: question-phrased where the intent is a question; cover the
  query family (who / what / how / cost / vs / when / where) that the
  audience actually asks; order by decision flow.
- Where a comparison exists → a table; a procedure → numbered steps;
  a definition → "X is …" once, early.
- Word-count target by role: money / pillar 1200–2000; answer page
  600–1200; post 800–1500; utility as short as it needs. Not padding.

### 5. Trust and entities

Author (name, credential, page), visible date, proof (numbers, cases,
certifications) with sources, outbound citations to primary sources,
the canonical names of products / people / brand, glossary terms if any.

### 6. Schema and links

Type from `seo-schema/references/schema-minimums.md` with its required
fields listed in the brief; internal links in (which pages should link
here, with anchor text) and out (2–5 related pages); the canonical URL.

### 7. Hand off

Write the file, then hand to content-strategist (audience: prospect)
with the path and the verification columns (`word_count`,
`question_headings`, `author_present`, `date_visible`, `schema_types`).
`/seo-fix-plan` picks the same file up as the content item.

## Rules

1. Facts in the brief are sourced; unknowns are marked `[owner to confirm]`.
2. Queries the audience would not type are not targets — say why one was dropped.
3. No word count for its own sake; the target follows the role and the
   query family, and the brief says which sections carry the length.
4. The brief names what to cut on an existing page, not only what to add.

## Examples

- `Rewrite /pricing for "emergency plumber cost leeds"` → commercial
  intent, answer block with the £95 call-out fact, H2s for cost / what's
  included / weekend / how the fixed quote works, comparison table,
  `Service` + `FAQPage` schema, links from home and FAQ.
- `New page: boiler fault codes` → informational, answer block defining
  fault codes, H2 per brand, table of codes, `Article` with author, links
  from the services page and the burst-pipe post.
