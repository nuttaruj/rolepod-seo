# AEO checks — answer engines and voice

Read when analyzing the AEO dimension: featured snippets, People Also Ask,
voice assistants, and the "direct answer" slot in AI search. AEO is about
the shape of the answer on the page; GEO is about trust and access.

## Direct answers

| Check | Threshold | Evidence to quote | Severity |
|---|---|---|---|
| Answer block under question heading | 40–60 plain words directly under a question-phrased H2 / H3, for each core query | the heading + first sentence | high on answer / money pages |
| Definition pattern | "X is …" in one sentence for the core term | the sentence | medium |
| Ordered steps | numbered list for any "how to" query | `lists`, the first two steps | medium on procedural pages |
| Comparison table | a table when the query implies "vs", "best", "pricing" | `tables` | medium on pricing / comparison |
| Answer before the fold | the answer is not below a hero, a form, or three paragraphs of context | position in the page | medium |

## Question coverage

| Check | Threshold | Evidence | Severity |
|---|---|---|---|
| Question-phrased headings | ≥3 H2 / H3 that read as questions on guide / FAQ pages | `question_headings` | medium |
| Coverage of the query family | who / what / when / where / why / how / cost / vs for the core topic | which are present, which are missing | medium |
| PAA-style sub-questions on posts | at least two per post | the headings | low |
| Jump links / table of contents | present on pages > ~1500 words | the TOC or its absence | low |

## Schema that mirrors the page

| Check | Threshold | Evidence | Severity |
|---|---|---|---|
| `FAQPage` where FAQ is visible | `faq_visible` true → `faq_schema` true | both flags + one Q/A | **low / info** — Google retired FAQ rich results for all sites on 2026-05-07; the block is a structural signal for answer engines only. Never write "missing FAQ schema" as a defect, never promise a SERP feature; `QAPage` for real user Q&A |
| `FAQPage` matches visible text | every `Question.name` appears on the page | a mismatch, if any | medium (misleading markup) |
| `HowTo` on procedural content | steps on the page = `HowToStep[]` | the block | low — no Google rich result since 2023-09-13; structural signal only |
| `speakable` on key answers | `SpeakableSpecification` with `cssSelector` or `xpath` on the answer block | the block | low |
| `Question` count sane | no schema for FAQs that are not on the page | the block vs the page | high (misleading markup) |

## Voice and local

| Check | Threshold | Evidence | Severity |
|---|---|---|---|
| Conversational phrasing | answers read aloud naturally: short sentences, no "click here" | quote one | low |
| NAP consistency | name, address, phone identical in HTML, footer, `LocalBusiness` schema | the three values | high for local businesses |
| Opening hours | visible text and `openingHoursSpecification` | both | medium for local |
| Service area | stated in text (`areaServed` in schema is a plus) | the sentence | low |
| Phone as `tel:` link | present | `contact_signals` | low |

## Scoring notes

- Answer pages (FAQ, guides, "how much does X cost") carry the most weight
  in AEO; a homepage without question headings is normal, not a finding.
- One well-formed visible answer block beats ten questions with no direct
  answer — score shape over count. Schema no longer moves the AEO score by
  more than a step; the visible answer does.
- When no target queries were given, infer 3–5 from titles and H1s and say
  which ones the assessment used.
