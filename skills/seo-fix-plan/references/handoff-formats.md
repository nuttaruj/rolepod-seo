# Hand-off formats — one block per owner

Copy the block, fill every field. A block a role cannot execute without
asking a question is not finished.

## rolepod-wplab — meta on a post or term

```text
FP-<n> · <finding id> · <page url>
Owner: rolepod-wplab · Depends on: <FP-x or —>
Resolve: rolepod_wp_post_list { target_id, post_type: "<page|post|product>", search: "<slug>" } → post_id
Write:   rolepod_wp_seo_set {
           target_id: "<alias>", post_id: <id>,
           meta_title: "<≤60 chars>",
           meta_description: "<≤160 chars>",
           canonical: "<absolute url>",        # omit when unchanged
           noindex: false,                     # only when the finding is about indexation
           og_title: "…", og_description: "…", og_image: "<absolute image url>"
         }
Verify:  the tool's desc_in_head must be true; then
         python3 <seo-audit skill-dir>/scripts/collect.py <page url> --urls one.txt → pages.tsv row: title / description_len / canonical_ok
```

Term (category / tag): same block with `term_id` + `taxonomy` instead of
`post_id`. Yoast rebuilds its indexable on write; RankMath writes term
meta — the tool picks the right one.

## rolepod-wplab — redirect

```text
FP-<n> · <finding id> · <source url>
Owner: rolepod-wplab · Depends on: —
Write:  rolepod_wp_redirect_set { target_id: "<alias>", source: "/old-path", target: "https://host/new-path", code: 301 }
Note:   Rank Math writes directly; the Redirection plugin returns REDIRECT_BACKEND_MANUAL → add it in Tools → Redirection (human step); no backend → install one or use the host's rules.
Verify: collect.py on the source URL → hops = 1, final_url = target
```

## rolepod-wplab — sitemap / robots / schema settings

```text
FP-<n> · <finding id> · site
Owner: rolepod-wplab · Depends on: —
Change: <SEO plugin> → <screen> → <setting> = <value>   (e.g. RankMath → Sitemap Settings → exclude post IDs 123; Yoast → Search Appearance → <post type> → Show in search results: No)
Alt:    rolepod_wp_option_get / rolepod_wp_option_set on "<option key>" when the screen is known to map to one option; read first, write the merged value.
Verify: fetch /sitemap.xml (or the plugin's index) → the URL is gone; collect.py site.json → sitemap.listed_but_noindex = []
```

Schema blocks: RankMath / Yoast schema settings when the type is
supported; otherwise a child-theme `wp_head` snippet — hand the block from
`/seo-schema` with the file path (`wp-content/themes/<child>/functions.php`).

## frontend-developer — code

```text
FP-<n> · <finding id> · <page url or route>
Owner: frontend-developer · Depends on: <FP-x or —>
File:   <path, e.g. app/(site)/pricing/page.tsx | src/components/JsonLd.tsx | app/sitemap.ts | next.config.js redirects | app/robots.ts>
Change: <the snippet — a metadata export, a canonical, a component, a redirect entry>
Covers: <pages this template change fixes>
Verify: collect.py on one covered URL → the column and expected value; audit_seo json_ld when the change is schema
```

Keep the snippet complete: imports, the export, the values. Name the
framework version if it matters (Next.js App Router `metadata` vs Pages
`next/head`).

## content-strategist (audience: prospect) — copy

```text
FP-<n> · <finding id> · <page url>
Owner: content-strategist (audience: prospect) · Depends on: <FP-x or —>
Brief:  reports/seo-brief-<slug>-<date>.md   (from /seo-page-brief — run it first if missing)
Ask:    <one line: what the page must do that it does not do today, e.g. "40–60-word answer under the H1 for 'emergency plumber cost leeds'">
Verify: collect.py on the URL → word_count ≥ <target>, question_headings ≥ <n>, faq_visible / author_present as the brief requires
Leading indicator: <what the owner watches without re-auditing — e.g. Search Console impressions for "<query>" over 4 weeks, or the page's inbound links>
```

## human — decision

```text
FP-<n> · <finding id> · <scope>
Owner: human · Blocks: <FP-x…>
Decision: <one sentence>
Options:  A) <option> — <trade-off>   B) <option> — <trade-off>   (recommended: <A|B>, because <one clause>)
Evidence: <the quoted finding>
```

## rolepod-uiproof — proof needed first

```text
FP-<n> · <finding id> · <page url>
Owner: rolepod-uiproof · Unblocks: <FP-x>
Run:    audit_seo { url, checks: [<subset>] }  |  measure_cwv { url }  |  discover_flows { url, max_pages }
Then:   assign to <owner> with the rendered value as evidence
```
