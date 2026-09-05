# SEO checks — classic search

Read when analyzing the SEO dimension. Each row: what to check · threshold ·
what to quote as evidence · default severity. Severity moves one step up on
home / money pages and one step down on utility pages. `pages.tsv` and
`site.json` from the collector carry most of the raw values.

## Per page — technical on-page

| Check | Threshold | Evidence to quote | Severity |
|---|---|---|---|
| `<title>` present | non-empty | the title text and its length | critical |
| Title length | ~50–60 chars; >70 truncates, <25 wastes | title + `title_len` | medium |
| Title unique across site | no two pages share it | both paths + the shared text | high |
| Primary topic early in title | main phrase in first ~40 chars | the title | low |
| Meta description present | non-empty | the text + length | high |
| Description length | ~150–160; >170 truncates, <70 thin | length | low |
| Description unique | no two pages share it | both paths | medium |
| Description states the answer | says what the page delivers, not a slogan | the text | low |
| H1 | exactly one | `h1_count` + text(s) | high (0 or ≥2) |
| Heading hierarchy | H2 under H1, H3 under H2; no jump for styling | the heading list | low |
| URL readable | hyphenated words, no session params, no `?id=` | the URL | medium |
| Trailing-slash consistency | one convention site-wide | two differing URLs | low |
| Canonical present | `<link rel=canonical>` on every indexable page | `canonical_ok` | high |
| Canonical self or intentional | equals final URL after redirects; same host | canonical vs final URL | high (`other` / `cross-domain`) |
| No accidental noindex | no `noindex` in meta robots or `X-Robots-Tag` on money pages | the robots value | critical on money pages |
| Viewport meta | present | `viewport` | medium |
| `html lang` | present, matches content language | the value | medium |
| Charset | declared | `charset` | low |
| Image alt text | content images have alt | `images_no_alt` / `images` | medium |
| Hero image weight | flag obviously large hero (>500 KB) when size is visible | the file name + size | low (needs uiproof for real numbers) |
| Internal links | descriptive anchors; key pages ≤3 clicks from home | anchor text examples; `not_linked_from_home` | medium |
| Orphan key pages | every money page linked from nav / home | path | high |
| Open Graph | og:title, og:description, og:image, og:type | `og` column (t/d/i) | low; medium on share-worthy pages |
| Twitter Card | `twitter:card` present | value | low |
| Mixed content | no `http://` assets on an https page | `mixed_content` count | high |
| Favicon | `<link rel=icon>` | `favicon` | low |
| Inbound links | money / answer / trust pages have ≥2 inbound links from other fetched pages | `inlinks` (per page) + `link_graph.low_inlinks` | medium; high for a money page with 0–1 |
| Click depth | key pages ≤3 clicks from home | `depth` (per page); `link_graph.unreachable_from_home` | medium; high when unreachable |

## Site level — cross-page (from `site.json`)

| Check | Threshold | Evidence | Severity |
|---|---|---|---|
| robots.txt reachable | 200 | status | high if missing on a large site; low on small |
| robots.txt does not block CSS / JS | `blocks_assets` false | the Disallow line | high |
| robots.txt does not block key sections | no Disallow on money paths | the Disallow line | critical |
| Sitemap declared in robots.txt | `Sitemap:` line | `declared_in_robots` | low |
| Sitemap exists and parses | 200, valid XML | `files` + `errors` | high |
| Sitemap URLs return 200 | none 3xx / 4xx / 5xx | `listed_but_not_200` | medium |
| Sitemap excludes noindex URLs | none | `listed_but_noindex` | medium |
| Sitemap lastmod sane | present, not all identical, not in the future | `with_lastmod` / count | low |
| http → https redirect | `host_variants.http` ends on https, 1 hop | final URL + hops | high |
| www / non-www consistency | alternate host redirects to canonical host | `host_variants.alt-host` | medium |
| Redirect chains on nav links | ≤1 hop | `redirect_chains` | medium (≥2 hops) |
| Duplicate titles / descriptions | none | `duplicates` | see per-page rows |
| hreflang reciprocity | every alternate links back, every page lists itself, `x-default` present | `site.hreflang` (`non_reciprocal[]`, `missing_self[]`, `missing_x_default[]`; `alternates_not_fetched` in Quick mode) | high when multilingual; non-reciprocal pairs are ignored by Google |
| hreflang codes | valid ISO 639-1 language (`th`, `en-GB`, `x-default`); no invented codes | `site.hreflang.invalid_codes[]` | medium — an invalid code is silently dropped by search engines |
| Query overlap (cannibalization) | two pages target the same primary query (title / H1) with the **same** intent → consolidate or differentiate; same query, **different** intent → keep both, note it | `duplicates.titles`, matching H1s, the two paths | medium when both are money pages; different intent = info only |
| Third-party scripts | homepage loads a bounded set of third-party origins; analytics / tag managers named | `third_party.home_count`, `third_party.analytics`, per page `third_party_hosts[]` | low; high when >10 origins on a money page (performance, and content that only exists after a tag manager runs) |
| HTTPS everywhere | all fetched pages https | `https` | critical |
| HSTS | `Strict-Transport-Security` on the home response | `security.hsts` | low |
| Near-duplicate pages | no two fetched pages ≥70 % identical body text (templated location / service pages) | `near_duplicates[]` pairs with similarity | medium; high when both are money pages |

## Per page — content quality

| Check | Threshold | Evidence | Severity |
|---|---|---|---|
| Word count vs role | per-role floor below; any ranking page ≥ 300; utility exempt | `word_count` + role | medium (thin) |
| Topic focus | the primary query answered in the first screen | quote the first paragraph | medium |
| Freshness | visible date on time-sensitive content | `date_visible` | low; medium on news / guides |
| Scannability | short paragraphs, lists, tables where the reader compares | `lists` / `tables` | low |
| Thin duplicates | near-identical pages (tag / archive) | two paths | medium |

Word count in the collector is all visible text (nav and footer included);
subtract roughly 80–150 for chrome on a typical template before judging thin.

Per-role floors (heuristics, not Google rules — what a page of that role
usually needs to answer its query fully; a shorter page that answers is fine
and says so in the finding):

| Page role | Floor | Notes |
|---|---|---|
| home | 500 | value proposition, what / who / where, proof |
| money (service, feature, product) | 800 (product 400) | the offer, who it is for, proof, price / next step |
| answer (FAQ, guide) | 800 | each question gets its 40–60-word answer |
| blog / pillar | 1500 | depth; pillar pages 1500+ |
| trust (about, contact, case study) | 400 | contact pages exempt |
| category / listing | 400 | unique intro, not only a product grid |
| location pages | 500–600 each, ≥60 % unique | ≥30 near-identical location pages → warn; ≥50 → stop and ask the owner |

## Site-type emphasis

`site.site_type` from the collector (saas / ecommerce / local / publisher /
agency, with confidence and signals). When confidence is `high`, the
signals below move **one severity step up** for that site and their
pass / fail counts weigh more in the score; when `low`, mention the type
in the summary and keep default weights. Never invent a type — `unknown`
means default weights.

| Site type | Signals that matter more | Typical money pages |
|---|---|---|
| local | NAP consistency, `LocalBusiness` subtype schema, opening hours, service area, reviews with source, click-to-call, contact page depth | service pages, contact, location pages |
| ecommerce | `Product` + `offers` completeness, category-page intro content, canonical on filtered / paginated URLs, image alt, near-duplicate product text, `BreadcrumbList` | category and product pages |
| publisher | author byline + `Person`, visible dates, `Article` schema, thin / duplicate archives (tag, author, pagination), question headings, internal links between posts | pillar posts, category hubs |
| saas | pricing and features page depth, docs crawlability (not blocked, indexable), comparison tables, `Organization` + `sameAs`, `BreadcrumbList`, changelog freshness | pricing, features, integrations, docs landing |
| agency | case studies with numbers and sources, `Person` for leadership, `sameAs`, service page depth, portfolio pages not thin | service pages, case studies |

## Structured data

| Check | Threshold | Evidence | Severity |
|---|---|---|---|
| JSON-LD present | ≥1 block on home and money pages | `schema_types` | medium |
| JSON-LD parses | `jsonld_invalid` = 0 | the block or the parse error | high |
| Types match page role | see table below | `schema_types` vs role | medium |
| Required properties present | per type, below | the missing property name | medium (rich result ineligible) |
| Rendered-only schema | a block present in uiproof `audit_seo` but absent in Tier A | both results | GEO finding (see geo-checks) |

Required properties for rich-result eligibility (the compact set; the full
list with recommended fields ships with `/seo-schema` in
`seo-schema/references/schema-minimums.md`):

| Type | Where | Required |
|---|---|---|
| `Organization` | home | `name`, `url`, `logo`; recommend `sameAs`, `contactPoint` |
| `LocalBusiness` | home / contact | `name`, `address` (PostalAddress), `telephone`; recommend `openingHoursSpecification`, `geo`, `priceRange` |
| `WebSite` | home | `name`, `url`; `potentialAction` (SearchAction) only if the site has search |
| `BreadcrumbList` | inner pages | `itemListElement[]` with `position`, `name`, `item` |
| `Article` / `BlogPosting` | posts | `headline`, `datePublished`, `author` (Person with `name`), `image`; recommend `dateModified`, `publisher` |
| `Product` | product pages | `name`, `image`, plus `offers` (`price`, `priceCurrency`, `availability`) or `aggregateRating` or `review` |
| `FAQPage` | visible FAQ | `mainEntity[]` of `Question` with `name` + `acceptedAnswer.text`; must mirror visible text |
| `HowTo` | procedural | `name`, `step[]` (HowToStep with `text`) |
| `Person` | author / about | `name`; recommend `url`, `jobTitle`, `sameAs`, `worksFor` |
