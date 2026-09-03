# Structured data minimums — per page type

Single source for `/seo-schema` and the compact table in
`seo-audit/references/seo-checks.md`. "Required" is the rolepod minimum for
a block to be worth shipping; "Recommended" is what makes it useful to
engines. Google's structured-data documentation is the authority on rich
result eligibility and changes without notice — when it disagrees with
this table, it wins, and the table gets a fix.

`a.b` means a nested property. `x / y / z` means at least one of them.
`scripts/validate.py` carries the same Required column; `make test-static`
keeps the two in lockstep.

| Type | Required | Recommended | Notes |
|---|---|---|---|
| `Organization` | `name`, `url`, `logo` | `sameAs`, `contactPoint`, `address`, `description`, `foundingDate` | One per site, on the homepage. `logo` should be a real, crawlable image URL. `sameAs` lists profiles that exist. |
| `LocalBusiness` | `name`, `address`, `telephone` | `openingHoursSpecification`, `geo`, `url`, `image`, `priceRange`, `areaServed` | Use the most specific subtype (`Plumber`, `Dentist`, `Restaurant`). `address` is a `PostalAddress`. Must match the visible NAP. |
| `WebSite` | `name`, `url` | `potentialAction`, `publisher`, `inLanguage` | `potentialAction` (`SearchAction` with `target.urlTemplate` + `query-input`) only when the site has its own search. |
| `BreadcrumbList` | `itemListElement` | — | Each `ListItem` needs `position` and `name`; `item` (URL) on all but the last. Order = the visible trail. |
| `Article` | `headline`, `datePublished`, `author.name`, `image` | `dateModified`, `publisher`, `description`, `author.url`, `mainEntityOfPage` | `BlogPosting` and `NewsArticle` share this row. `headline` ≤ 110 chars. `author` is a `Person` (or `Organization` when genuinely corporate). |
| `Product` | `name`, `offers / review / aggregateRating` | `image`, `description`, `sku`, `brand`, `gtin` | `Offer` needs `price`, `priceCurrency`; add `availability`, `url`. Only real prices and real ratings. |
| `FAQPage` | `mainEntity` | — | `mainEntity[]` of `Question` with `name` + `acceptedAnswer.text`, verbatim from the page. Rich-result display has been limited by Google to well-known government / health sites since 2023; the markup still gives answer engines a clean Q/A structure, which is why it stays in the AEO checks. |
| `HowTo` | `name`, `step` | `totalTime`, `tool`, `supply`, `image` | `step[]` of `HowToStep` with `text`. Google retired the HowTo rich result in 2023; keep the markup only where the page is genuinely procedural. |
| `Person` | `name` | `url`, `jobTitle`, `sameAs`, `worksFor`, `image`, `description`, `knowsAbout` | Author entities. Link from `Article.author`; give each author a page that is the `url`. |
| `Service` | `name`, `provider` | `serviceType`, `areaServed`, `description`, `offers`, `url` | No rich result; entity clarity for GEO. `provider` is the `Organization` / `LocalBusiness`. |
| `Event` | `name`, `startDate`, `location` | `endDate`, `offers`, `image`, `description`, `organizer`, `eventStatus` | `location` is a `Place` with `name` + `address`, or a `VirtualLocation`. |
| `VideoObject` | `name`, `thumbnailUrl`, `uploadDate` | `description`, `duration`, `contentUrl`, `embedUrl` | Needed for video rich results and key-moments. |
| `Review` | `itemReviewed`, `author`, `reviewRating` | `datePublished`, `reviewBody` | `reviewRating.ratingValue` required. Reviews must be visible on the page. |
| `AggregateRating` | `ratingValue`, `reviewCount / ratingCount` | `bestRating`, `worstRating` | Never self-serving: not on the site's own `Organization` / `LocalBusiness`. |

## Cross-cutting rules

- **Mirror the page.** Every value in JSON-LD must appear on the page in
  some form (FAQ text, prices, ratings, dates, author names). Hidden or
  invented values are a policy violation and a GEO trust cost.
- **One graph, stable `@id`s.** On sites with several blocks, use one
  `@graph` with `@id` anchors (`#organization`, `#website`, `#webpage`,
  `#author-<slug>`) and reference them instead of repeating nodes.
- **Types by page role** — home: `Organization` (or `LocalBusiness`) +
  `WebSite`; inner pages: `BreadcrumbList` + the page-type node; posts:
  `Article` with `author` → `Person`; product pages: `Product`; FAQ:
  `FAQPage`; contact for a local business: `LocalBusiness` with hours.
- **`speakable`** — on `WebPage` / `Article`, a `SpeakableSpecification`
  with `cssSelector` (or `xpath`) pointing at the direct-answer block.
  Optional, low weight, harmless.
- **Placement** — one `<script type="application/ld+json">` in `<head>`,
  or wherever the platform puts it; server-rendered, not injected after
  load (Tier A vs Tier B diff in `/seo-audit` catches the latter).
- **Verification after deploy** — rolepod-uiproof `audit_seo` with
  `checks: ["json_ld"]` when installed; otherwise
  `python3 scripts/validate.py <url>` from this skill.
