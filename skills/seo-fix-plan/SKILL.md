---
name: seo-fix-plan
description: Turn an /seo-audit priority matrix (or its JSON sidecar) into an executable fix plan — findings grouped by owner (rolepod-wplab for WordPress, frontend-developer for code, content-strategist for copy, human for policy) in dependency order, each with the exact payload, snippet or brief and a verification step. Use after an audit, or when asked to "fix these SEO issues", "apply the audit", or "what do we change first".
---

# /seo-fix-plan

Converts findings into work other roles can execute without re-reading
the audit: one block per item with owner, exact change, dependency and
the command that proves it landed. It plans; it executes only the
WordPress items the user approves and only when rolepod-wplab is
connected.

Parent judgment applies unchanged (verify-first, simplest viable, effort
ceiling `xhigh`).

## When to use

- Right after `/seo-audit`, or when the user pastes a findings list.
- "Fix the SEO issues", "apply the audit", "what should we change first".
- A second audit shows the same findings — the plan becomes the diff.

## When NOT to use

- No audit yet → `/seo-audit` first; a plan without evidence is guesswork.
- Writing schema → `/seo-schema`. Writing the copy → `/seo-page-brief`
  then content-strategist. This skill points at them, it does not replace them.

## Inputs

- `reports/seo-audit-<host>-<date>.json` (preferred) or the markdown
  priority matrix. Ask for the path if several exist.
- Platform: `site.platform_hints` from the collector's `collect.json`;
  WordPress → is rolepod-wplab connected (`rolepod_wp_health_check`)?
  Code → repo path. Confirm when the hints are empty.
- Scope: everything, or one priority band / one page.

## Outputs

1. `reports/seo-fix-plan-<host>-<date>.md` — the plan, shape below.
2. Chat summary: items per owner, first three to do, what needs a human.
3. Optional execution log for wplab items the user approved.

## Process

### 1. Load and filter

Read the sidecar. Keep `status: fail | warn`. `info` findings with
`owner: human` go to the **Decisions** section (AI-bot policy, brand
naming, which testimonials). `pass` and strengths are dropped. Merge
findings that share one fix (one template change fixes forty pages).

### 1b. Optional — Search Console demand (never required)

If the user has a Search Console **Performance → Export** (zip or
Pages / Queries CSV) at hand, run it once and re-rank with real demand;
if they do not, skip this silently — the plan is complete without it and
the audit never depends on it. Ask at most once, never block on it.

```bash
python3 <skill-dir>/scripts/gsc_csv.py <export.zip | Pages.csv Queries.csv> --pages reports/seo-audit-<host>-<date>.json
```

`gsc.json` / `gsc.md` give quick wins (position 4–20 with impressions),
low-CTR top-3 pages, "seen but not clicked", top pages / queries, and the
join with audited URLs (plus Search Console pages the audit never
fetched — candidates for the next run). Use it to move items up when
their page has demand, to turn title / description fixes into
quick wins on low-CTR pages, and to add `pages[].gsc` to the sidecar so
the HTML shows Clicks / Impressions / Position.

### 2. Order by dependency

Fixed sequence — a later stage is pointless while an earlier one fails:

1. Crawl blockers — robots.txt disallow on money paths, blocked CSS / JS, https, host variants.
2. Indexation — accidental `noindex`, sitemap errors, sitemap listing noindex / 404 URLs.
3. Canonical and duplicates — cross-domain or wrong canonicals, duplicate titles / descriptions.
4. Redirects — chains, http → https, www.
5. Structured data — via `/seo-schema`.
6. Content — thin pages, answer blocks, E-E-A-T, via `/seo-page-brief`.
7. On-page polish — title length, OG tags, alt text, internal links.

Inside a stage, higher impact first, then lower effort.

### 3. Assign owners and write the exact change

Use `references/handoff-formats.md` for the block per owner:

- **rolepod-wplab** — `rolepod_wp_seo_set` payload per post / term
  (`meta_title`, `meta_description`, `canonical`, `noindex`, OG fields);
  `rolepod_wp_redirect_set` per chain; schema / robots / sitemap via the
  SEO plugin settings or the theme. Resolve `post_id` with
  `rolepod_wp_post_list` by slug before writing.
- **frontend-developer** — file + snippet: metadata export, canonical
  helper, JSON-LD component, sitemap route, redirect config, robots route.
- **content-strategist** (audience: prospect) — pointer to the
  `/seo-page-brief` output per page; never the copy itself.
- **human** — decisions with options and trade-offs; policy, budget, brand.
- **rolepod-uiproof** — when a finding needs rendered-DOM or CWV proof
  before it can be assigned.

Each item: id (from the sidecar), page, exact change, owner, depends-on,
verification (`collect.py --urls one.txt` and the column to read, or
`audit_seo`, or `validate.py`).

### 4. Execute what the user approves (WordPress only)

If rolepod-wplab is connected and the user says go: run the wplab
payloads in order, one page at a time, reading `prod_guard` first — the
companion refuses writes on production targets, and that is correct.
After each write, verify with the command in the item. Log what changed.
Code and content items are handed off, not executed here.

### 5. Report

Write the plan file, print the chat summary. When the plan is done,
suggest a re-audit; the sidecar `id`s make the before / after diff trivial.

## Plan shape

```text
# SEO fix plan — <host> · <date> · from seo-audit-<host>-<date>.json
## Summary   <n> items · wplab <n> · frontend-developer <n> · content-strategist <n> · human <n>
## Stage 1 — crawl blockers
### FP-01 · <finding id> · <page>
Owner: … · Depends on: — · Effort: S · Impact: H
Exact change: <payload | snippet | brief pointer>
Verify: <command + expected value>
## Stage 2 — indexation … (same)
## Decisions for the owner
<one block per info finding: options, trade-offs, recommended default>
## Deferred
<items waiting on Tier B / Phase 2 data, with what would unblock them>
```

## Rules

1. No item without a sidecar `id` or a quoted finding — no invented work.
2. "Exact change" is a value or a snippet, never "improve the title".
3. Production WordPress writes need the user's go and the prod guard's
   consent; never bypass either.
4. One fix per template beats forty per page; say which pages it covers.

## Examples

- `Apply the audit from yesterday` → loads the newest sidecar, 14 items in
  five stages, two wplab payloads executed after approval, four code items
  handed to frontend-developer, three briefs queued, one decision (GPTBot).
- `Just the critical ones` → filters `priority: critical`, keeps the
  dependency order, notes what the skipped items were waiting on.
