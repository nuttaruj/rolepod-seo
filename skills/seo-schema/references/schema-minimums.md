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
| `FAQPage` | `mainEntity` | — | `mainEntity[]` of `Question` with `name` + `acceptedAnswer.text`, verbatim from the page. Google retired FAQ rich results for every site on 2026-05-07 (see the retired table below): the type stays valid, existing blocks may stay, never add one for a Google benefit, and use `QAPage` for genuine user-submitted Q&A. Kept in the AEO checks as a structural signal only. |
| `HowTo` | `name`, `step` | `totalTime`, `tool`, `supply`, `image` | `step[]` of `HowToStep` with `text`. No Google rich result since 2023-09-13; keep the markup only where the page is genuinely procedural and another consumer wants it. |
| `Person` | `name` | `url`, `jobTitle`, `sameAs`, `worksFor`, `image`, `description`, `knowsAbout` | Author entities. Link from `Article.author`; give each author a page that is the `url`. |
| `Service` | `name`, `provider` | `serviceType`, `areaServed`, `description`, `offers`, `url` | No rich result; entity clarity for GEO. `provider` is the `Organization` / `LocalBusiness`. |
| `Event` | `name`, `startDate`, `location` | `endDate`, `offers`, `image`, `description`, `organizer`, `eventStatus` | `location` is a `Place` with `name` + `address`, or a `VirtualLocation`. |
| `VideoObject` | `name`, `thumbnailUrl`, `uploadDate` | `description`, `duration`, `contentUrl`, `embedUrl` | Needed for video rich results and key-moments. |
| `Review` | `itemReviewed`, `author`, `reviewRating` | `datePublished`, `reviewBody` | `reviewRating.ratingValue` required. Reviews must be visible on the page. |
| `AggregateRating` | `ratingValue`, `reviewCount / ratingCount` | `bestRating`, `worstRating` | Never self-serving: not on the site's own `Organization` / `LocalBusiness`. |

## Retired rich results (the schema.org types stay valid)

`scripts/validate.py` warns on these types with the date and source; the
lockstep test keeps this table and the script's `RETIRED` dict identical.
Every row must cite a Google-owned URL — third-party reports do not qualify.

| Type | Rich result retired | Source | What to do |
|---|---|---|---|
| `HowTo` | 2023-09-13 | https://developers.google.com/search/blog/2023/08/howto-faq-changes | Keep only for genuinely procedural pages; never recommend for a Google benefit |
| `FAQPage` | 2026-05-07 | https://developers.google.com/search/docs/appearance/structured-data/faqpage | Existing blocks may stay if they mirror the page; do not add for Google; `QAPage` for real user Q&A |
| `ClaimReview` | 2025-06-12 | https://developers.google.com/search/blog/2025/06/simplifying-search-results | Fact-check rich results discontinued; keep only if a non-Google consumer needs it |
| `CourseInfo` | 2025-06-12 | https://developers.google.com/search/blog/2025/06/simplifying-search-results | Use `Course` for entity clarity; no rich result |
| `EstimatedSalary` | 2025-06-12 | https://developers.google.com/search/blog/2025/06/simplifying-search-results | Remove from job pages; `JobPosting` unaffected |
| `LearningVideo` | 2025-06-12 | https://developers.google.com/search/blog/2025/06/simplifying-search-results | Plain `VideoObject` instead |
| `SpecialAnnouncement` | 2025-06-12 | https://developers.google.com/search/blog/2025/06/simplifying-search-results | Remove; announce in visible content |
| `VehicleListing` | 2025-06-12 | https://developers.google.com/search/blog/2025/06/simplifying-search-results | `Product` / `Car` for entity clarity; no rich result |

Search Console reports, the Rich Results Test and the appearance filters for
the June 2025 set were removed from 2025-09-09; FAQ reporting followed in
June–August 2026.

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
