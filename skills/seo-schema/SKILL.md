---
name: seo-schema
description: Add or fix structured data (JSON-LD) for a page or a site — Organization, LocalBusiness, WebSite, BreadcrumbList, Article, Product, FAQPage, HowTo, Person, Service, Event. Generates the block from facts already on the page, checks required properties per type, validates with a stdlib script (or rolepod-uiproof audit_seo when installed), and hands the snippet to rolepod-wplab or frontend-developer. Use when asked for schema markup, rich results, JSON-LD, or when /seo-audit flagged missing or invalid structured data.
---

# /seo-schema

Produces JSON-LD that mirrors what is visible on the page, validated
against a per-type minimum, and delivered as a snippet the right tool can
place. It never invents facts: a rating, a price or an author that is not
on the page does not go in the markup.

Parent judgment applies unchanged (verify-first, simplest viable, effort
ceiling `xhigh`).

## When to use

- "Add schema / structured data / JSON-LD to <page>", "get rich results".
- `/seo-audit` findings with signal `schema`, `faq-schema`, `json-ld`,
  `local-business`, `author`.
- After a template change that touched `<head>` and the block went missing.

## When NOT to use

- Deciding what the page should say → `/seo-page-brief`, then content.
- Whole-site audit → `/seo-audit`. Executing a list of fixes → `/seo-fix-plan`.
- Fake or self-serving ratings, hidden FAQ text, `HowTo` on non-procedural
  pages — refuse and explain the policy cost.

## Inputs

- Page URL (or "new page of type X") — required.
- Facts: prefer `.rolepod-seo/collect-*/collect.json` from a recent
  `/seo-audit`; otherwise fetch the page. Ask the user only for facts that
  are not on the page (logo URL, social profiles, founding date).
- Platform: WordPress (which SEO plugin), Next.js / other code, static —
  `site.platform_hints` in `collect.json` says; confirm if empty.

## Outputs

- One JSON-LD block per page (or one `@graph` for the site's shared
  nodes), in a fenced `json` block, plus the placement instruction.
- A validation line per node: `ok` / `FAIL … missing <property>`.
- A hand-off block for the owner that places it (below).

## Process

### 1. Decide the types from the page role

Home → `Organization` (or `LocalBusiness` subtype) + `WebSite`. Inner
page → `BreadcrumbList` + its type: post → `Article` with `author` →
`Person`; product → `Product`; FAQ → `FAQPage`; procedure → `HowTo`;
service page → `Service`; contact of a local business → `LocalBusiness`
with hours. Full table: `references/schema-minimums.md`.

### 2. Collect the facts from the page

Quote the source for each value — the visible text, the meta tag, the
footer address. For `FAQPage`, copy every question and answer verbatim;
count must equal the visible pairs. Anything not on the page → ask, or
leave the property out and say so.

### 3. Generate

- `@context: "https://schema.org"`, one `@graph` when there are several
  nodes, stable `@id` anchors (`#organization`, `#website`, `#webpage`,
  `#author-<slug>`), absolute URLs, ISO 8601 dates.
- Include every Required property; add Recommended ones only when the
  fact exists. Keep it short — markup is not a place for marketing copy.
- Preserve an existing block's `@id`s when replacing it, so other nodes
  keep resolving.

### 4. Validate

```bash
python3 <skill-dir>/scripts/validate.py block.json        # a file
python3 <skill-dir>/scripts/validate.py https://example.com/page   # after deploy
```

The script parses, walks the graph and reports each typed node with any
missing required property. With rolepod-uiproof installed, run
`audit_seo` with `checks: ["json_ld"]` on the live URL instead — it sees
the rendered DOM. Fix every `FAIL` before handing off.

### 5. Hand off the placement

| Platform | Owner | Exact hand-off |
|---|---|---|
| WordPress + RankMath / Yoast | rolepod-wplab | plugin schema settings where the type is supported; otherwise the block in the theme `<head>` via a child theme or a snippet plugin — name the file and hook (`wp_head`) |
| Next.js / React / other code | `frontend-developer` | a `JsonLd` component rendering `<script type="application/ld+json">` server-side, with the object built from the page's data; file path named |
| Static HTML | the user, or `frontend-developer` | the block pasted in `<head>` of the named file |
| Hosted builders (Wix, Squarespace, Webflow, Shopify) | human | the builder's custom-code / SEO panel; name the panel |

Every hand-off carries: the page URL, the full block, "replace" or
"add", and the verification command from step 4.

### 6. Verify after deploy

Re-run step 4 against the live URL; `/seo-audit` Tier B (`audit_seo`
`json_ld`) when available. Report `ok` lines, not "should work".

## Rules

1. Nothing in the markup that a reader cannot see on the page.
2. No `AggregateRating` / `Review` on the site's own `Organization` or
   `LocalBusiness`; no ratings without visible reviews.
3. `FAQPage` mirrors the visible FAQ exactly; `HowTo` only for real steps.
4. Rich-result eligibility is Google's call and changes; say "eligible
   per current documentation", never "will show".
5. One block per page per type; merge into `@graph` rather than duplicate.

## Examples

- `Add FAQ schema to /faq` → six visible Q/A pairs copied verbatim into
  `FAQPage.mainEntity`, validated `ok`, hand-off to wplab
  (RankMath FAQ block) or a JSON-LD component.
- `Our blog posts have no author schema` → `Article.author` → `Person`
  with `name` + `url` to the author page (created if missing — a task for
  content-strategist), one block per post template.
- `Local business schema for a plumber in Leeds` → `Plumber` subtype with
  the footer NAP, `openingHoursSpecification` from the contact page,
  `areaServed` from the service-area sentence; nothing the page does not say.
