# Fixture site A — "Northwind Plumbing" (fictional)

A tiny static site for `make test-fixture`. `__BASE__` is replaced with the
served origin at test time (`tests/fixture/serve.sh`). Deliberate defects:

| Page | Defect |
|---|---|
| `services.html` | two `<h1>`, one `<img>` without alt, short title, description duplicated with pricing |
| `pricing.html` | description duplicated with services; no og:description |
| `faq.html` | visible FAQ (6 question H2s) with **no** `FAQPage` schema |
| `contact.html` | NAP visible, no `LocalBusiness` schema |
| `blog/post-1.html` | canonical points to a different domain (`example.com`) |
| `blog/post-2.html` | `noindex` yet listed in the sitemap; no meta description; thin (<300 words) |
| `sitemap.xml` | lists `/old-page.html` (404); `contact.html` has no lastmod |
| `robots.txt` | blocks GPTBot + CCBot entirely; no `Sitemap:` line |
| `th/services.html` ↔ `services.html` | reciprocal hreflang pair, but `services.html` has no `x-default` |
| `th/pricing.html` → `pricing.html` | claims an `en` alternate that does not link back (non-reciprocal) |
| `th/services.html` | one alternate with an invalid language code (`xx`) |
| `index.html` | loads a third-party analytics script (plausible.io); nav is a `<ul>` with one submenu item (`services/boilers.html`) so Quick mode follows the real menu |
| site | no `llms.txt`; no author pages; About has no `Person` schema |
