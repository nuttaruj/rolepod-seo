# GEO checks — generative engines

Read when analyzing the GEO dimension: what an AI answer engine (AI
Overviews, ChatGPT search, Perplexity, Copilot) needs before it will cite a
page. Three groups: trust surface, synthesizability, technical access.

## E-E-A-T surface — can an engine tell who is speaking and why to trust them?

| Check | Threshold | Evidence to quote | Severity |
|---|---|---|---|
| Named author on articles | byline with a real name | the byline text; `author_present` | high on blog / guides |
| Author bio + credentials | a sentence of qualification per author | the bio text or its absence | medium |
| Author pages | one page per author, linked from bylines | URL | low |
| `Person` schema linked via `author` | Article → author → Person with `name` (+ `url`) | the JSON-LD | medium |
| About page substance | who, since when, why trust; leadership named | the sentences | high (site-wide) |
| Contact in HTML | address, phone, email as text, not images | `contact_signals` | medium |
| Trust proof with sources | testimonials / case studies with numbers, certifications, press, awards — each attributable | quote one, note the source | medium |
| `Organization` schema | `name`, `logo`, `url`, `sameAs` to real profiles | the block; missing keys | medium |
| Consistent brand naming | one name for the company across pages and schema | the two variants | low |

## Synthesizability — can an engine lift an answer cleanly?

| Check | Threshold | Evidence | Severity |
|---|---|---|---|
| Claim-first paragraphs | answer in the first 1–2 sentences of each section | quote a section's first sentence | high on money / answer pages |
| Factual density | numbers, dates, named entities, definitions present | quote three facts, or note their absence | medium |
| Citations out | links to primary sources for claims | `links_external`, the anchor | medium on guides |
| Original signals | first-hand data, measured results, unique point of view | quote it | medium |
| Entity clarity | one canonical name per product / person / brand; glossary when jargon | the variants | low |
| Content without JavaScript | Tier A text ≈ rendered text (uiproof `audit_seo` diff) | word count A vs B | high when the gap is large |
| Definition patterns | "X is …" for the core term | the sentence | low |

## Technical GEO — access and rich signals

| Check | Threshold | Evidence | Severity |
|---|---|---|---|
| AI-bot crawl policy | see below — a decision, not a defect | `robots.agents` verdicts | info (decision) |
| Rendered-only content | none of title / description / body only after JS | Tier A vs Tier B | high |
| Rich schema beyond basics | `Person` for authors; `Dataset` / `ClaimReview` only when honest; `speakable` on key answers | `schema_types` | low |
| `llms.txt` | Google Search ignores it (AI optimization guide, 2026-05-15, updated 2026-07-10: neither helps nor harms); harmless; optional for other services | `llms_txt.present` | info, `seo_effect: none` — report presence, never recommend it, never call it a citation lever |
| Clean HTML structure | headings carry the outline; no heading-as-styling | the heading list | low |
| Agent actionability | interactive elements are real `<button>` / `<a>` / labelled inputs with programmatic names, visible in the accessibility tree, stable layout (CLS), no critical action hidden behind an overlay — what Lighthouse's *Agentic Browsing* category (13.3, default since 2026-05-07, pass-ratio not a score) checks | rolepod-uiproof `audit_a11y` findings (names / labels, tree) + `measure_cwv` CLS; or `npx lighthouse <url> --only-categories=agentic-browsing` | medium on money / booking / checkout pages; **not assessed** until one of those ran |

### AI-bot policy — how to report it

`site.json → robots.agents` gives a verdict per user agent: GPTBot (OpenAI
training + search), ClaudeBot (Anthropic), PerplexityBot, Google-Extended
(Gemini training; does not affect Search or AI Overviews), CCBot (Common
Crawl, feeds many models), plus Googlebot / Bingbot for reference.

Report it as a policy choice with both sides, then let the owner decide:

- **Open** (no Disallow): maximum chance of being cited in AI answers;
  content may be used for training; more bot traffic.
- **Block training, allow search** (e.g. Disallow `Google-Extended`, allow
  Googlebot): AI Overviews still possible; Gemini training opted out.
- **Block all AI bots**: protects content from reuse; no citations from
  those engines; GEO score is capped and the report says why.

Never mark a block as a defect. Note when a block is probably accidental —
e.g. `Disallow: /` under `User-agent: *` — that is an SEO critical.

Also note that robots.txt is advisory and not every agent honors it; the
report should not promise enforcement.

### Dated facts this file relies on

| Claim | Date | Source |
|---|---|---|
| Google Search ignores `llms.txt` and other AI text files | guide published 2026-05-15, updated 2026-07-10 | https://developers.google.com/search/docs/fundamentals/ai-optimization-guide |
| Lighthouse Agentic Browsing category, default on | 13.3 (2026-05-07), Chrome 150+ | https://developer.chrome.com/docs/lighthouse/agentic-browsing/scoring |
| `Google-Extended` controls Gemini training, not Search or AI Overviews | ongoing | https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers |
