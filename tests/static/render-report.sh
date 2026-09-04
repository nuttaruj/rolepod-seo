#!/usr/bin/env bash
# The HTML renderer: structure, print CSS, no external assets, score → status
# mapping, artifact vs document forms.
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=tests/fixture/.out/render; rm -rf "$OUT"; mkdir -p "$OUT"
python3 skills/seo-audit/scripts/render_report.py tests/fixtures/sample-report.json --out "$OUT/report.html" >/dev/null
python3 skills/seo-audit/scripts/render_report.py tests/fixtures/sample-report.json --artifact --out "$OUT/report.artifact.html" >/dev/null
# an older sidecar: one finding gone (fixed), one new, scores lower
python3 - "$OUT" <<'PY2'
import json, sys
d = json.load(open("tests/fixtures/sample-report.json"))
d["generated_at"] = "2026-08-01T10:00:00Z"
d["scores"]["seo"]["score"] = 4; d["scores"]["seo"]["band"] = "below-baseline"
d["findings"] = [f for f in d["findings"] if f["id"] != "aeo-faq-schema-faq"]
d["findings"].append(dict(id="seo-title-missing-about", dimension="seo", signal="title", page="http://127.0.0.1:8765/about.html", severity="critical", status="fail", evidence="<title></title>", fix="add a title", owner="frontend-developer", effort="S", impact="H", priority="critical"))
json.dump(d, open(sys.argv[1] + "/previous.json", "w"))
PY2
prev_line=$(python3 skills/seo-audit/scripts/render_report.py tests/fixtures/sample-report.json --previous "$OUT/previous.json" --out "$OUT/report.prev.html" 2>&1 >/dev/null)
printf '%%PDF-1.4\n%%fake minimal pdf for the embed test\n' > "$OUT/fake.pdf"
python3 skills/seo-audit/scripts/render_report.py tests/fixtures/sample-report.json --artifact --pdf "$OUT/fake.pdf" --out "$OUT/report.pdf.html" >/dev/null
grep -q "since 2026-08-01: SEO 4→6, GEO 5→5, AEO 5→5 · fixed 1 · new 1 · still open 2" <<<"$prev_line" || { echo "  ✗ --previous one-liner: $prev_line"; exit 1; }
python3 - "$OUT" <<'PY'
import importlib.util, re, sys
sys.dont_write_bytecode = True
out = sys.argv[1]
spec = importlib.util.spec_from_file_location("r", "skills/seo-audit/scripts/render_report.py")
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
bad = 0
def check(cond, msg):
    global bad
    if not cond: print("  ✗ " + msg); bad = 1
# score → status mapping (table-tested)
for score, want in [(10, ("On Track", "good")), (8, ("On Track", "good")), (7, ("Needs Work", "warn")), (5, ("Needs Work", "warn")),
                    (4, ("Critical", "bad")), (1, ("Critical", "bad")), (None, ("Not assessed", "na")), ("7", ("Not assessed", "na"))]:
    check(r.score_status(score) == want, f"score_status({score!r}) = {r.score_status(score)} != {want}")
doc = open(f"{out}/report.html", encoding="utf-8").read()
art = open(f"{out}/report.artifact.html", encoding="utf-8").read()
check(doc.startswith("<!doctype html>") and "<html" in doc and "</body>" in doc, "document form has doctype/html/body")
check(not re.search(r"<!doctype|<html[\s>]|<head[\s>]|<body[\s>]", art, re.I), "artifact form has no document wrapper")
check(art.startswith("<title>127.0.0.1:8765</title>"), "artifact title is the host")
check("<title>127.0.0.1:8765</title>" in doc, "document title is the host")
for sec in ("summary", "pages", "seo", "geo", "aeo", "matrix", "decisions", "strengths", "not-assessed", "glossary"):
    check(f'<section id="{sec}"' in doc, f"section #{sec} present (full mode)")
check(doc.count('class="score-card"') == 3, "three score cards")
check(doc.count('data-status="warn"') == 3, "sample scores 6/5/5 → three Needs Work cards")
check(doc.count('conic-gradient(') == 3 and "0.60turn" in doc and "0.50turn" in doc, "ring gauges sized by score")
check('class="side no-print"' in doc and doc.count('<nav>') == 1 and '<b>01</b>Summary' in doc, "sidebar with numbered nav")
check("@media print" in doc and "@page" in doc, "print CSS present")
check("prefers-color-scheme: dark" not in doc and "data-theme" not in doc and "color-scheme:light" in doc and "--bg:#F5F4FB" in doc, "single light theme on the design's page colour, no dark overrides")
check(doc.count("@font-face{font-family:'Instrument Sans'") == 2 and doc.count("@font-face{font-family:'JetBrains Mono'") == 2 and "data:font/woff2;base64," in doc, "embedded variable fonts (latin + latin-ext) from assets/fonts.css")
check("Open Font License" in doc, "font licence notice travels with the report")
check("var(--bg)" in doc and "body{margin:0;background:var(--bg)" in doc, "body background painted explicitly from a token")
ext = re.findall(r'(?:<link[^>]+href|<script[^>]+src|@import|url\()\s*=?\s*["\']?(https?://[^"\')\s]+)', doc)
check(not ext, f"no external requests at all — fonts are embedded (found {ext[:3]})")
check('class="chip p-critical">Critical<' in doc and 'class="chip p-quick-win">Quick win<' in doc, "priority chips rendered")
check('class="chip fail">Fail<' in doc and 'class="label">Also observed</div>' in doc and 'class="chip working">Working<' in doc, "status chips + also-observed + working cards rendered")
check(doc.count('class="mcard"') == 2 and "effort S · impact H" in doc, "matrix rendered as cards with effort / impact meta")
check("#findings>section:first-of-type>.dimhead{margin-top:0}" in doc and ".dimhead{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:34px 0 14px}" in doc, "dimension headers keep 34px above them except the first")
check("ai-bot-policy" in doc and 'id="decisions"' in doc, "info/human finding lands in Decisions")
prevdoc = open(f"{out}/report.prev.html", encoding="utf-8").read()
check('<section id="roadmap"' in doc and ">Unblock<" in doc and "Ongoing — decide, measure, re-audit" in doc, "roadmap phases derived from priorities")
check(">Fix first</h3>" in doc and ">Quick wins</h3>" in doc, "fix-first + quick-wins cards in the summary")
check("<h1>Solid foundations, three blockers between this site and both search engines.</h1>" in doc, "sidecar headline on the cover")
gen = r.headline_for({"scores": {"seo": {"score": 6}, "geo": {"score": 5}, "aeo": {"score": 4}}}, [{"priority": "critical", "status": "fail", "signal": "canonical"}, {"priority": "quick-win", "status": "fail", "signal": "h1"}])
check(gen == "1 critical blocker, 1 quick win — SEO is the strongest at 6/10, AEO the weakest at 4/10.", f"generated headline fallback ({gen})")
check('<section id="method"' in doc and "How to read the scores" in doc, "methodology section")
check("Site type: <strong>local service</strong>" in doc, "site type line from site.site_type")
check('class="label">Verify</div>' in doc and "canonical_ok = self" in doc, "verify panel on matrix cards")
check('class="watch">Watch</span><span>Search Console' in doc, "leading indicator lands in the Ongoing card")
check('1 fail</span>' in doc and 'class="chip fail">404</span>' in doc, "per-page finding counts + status chips in the pages table")
check(doc.count("</b> fail · <b>") == 3 and "1 optional (no Google effect)" in doc, "fail/warn/pass counts on the three cards + optional count")
check("By group: <strong>technical</strong> — 2 fail" in doc, "SEO findings broken down by signal group (canonical + h1 → technical)")
check("<strong>trust</strong> — 1 pass" in doc, "GEO ai-bot-policy → trust")
check('<section id="optional"' in doc and "No effect on Google Search" in doc and 'class="sig">faq-schema</span><span class="chip none">' in doc, "seo_effect none → optional section, labelled")
check(doc.index('<section id="roadmap"') < doc.index('<section id="strengths"') < doc.index('<section id="not-assessed"') < doc.index('<section id="optional"') < doc.index('<section id="method"'), "optional section sits after everything that affects Google Search")
mat = doc[doc.index('<section id="matrix"'):doc.index('<section id="roadmap"')]
check("faq-schema" not in mat, "no-effect finding excluded from the priority matrix")
check("faq-schema" not in doc[doc.index(">Quick wins</h3>"):doc.index('<section id="pages"')], "no-effect finding excluded from quick wins")
aeo = doc[doc.index('<section id="aeo"'):doc.index('<section id="matrix"')]
check("0 fail · 0 warn · 0 pass" in aeo and 'chip none">no effect on Google Search' in aeo, "AEO section counts exclude the none row but still lists it, labelled")
for f_, want in (({"signal": "faq-schema"}, "none"), ({"signal": "llms-txt"}, "none"), ({"signal": "howto-schema"}, "none"), ({"signal": "canonical"}, "direct"), ({"signal": "faq-schema", "seo_effect": "direct"}, "direct"), ({"signal": "author", "seo_effect": "indirect"}, "indirect")):
    check(r.effect_of(f_) == want, f"effect_of({f_}) = {r.effect_of(f_)} != {want}")
for sig, want in (("canonical", "technical"), ("faq-schema", "schema"), ("answer-block", "answer"), ("ai-bot-policy", "trust"), ("content-depth", "content"), ("click-depth", "technical"), ("mixed-content", "technical"), ("organization-schema", "schema"), ("xyz", "other")):
    check(r.signal_group(sig) == want, f"signal_group({sig!r}) = {r.signal_group(sig)} != {want}")
check('id="since"' in prevdoc and ">Fixed</h3>" in prevdoc and ">New</h3>" in prevdoc, "since-last-audit block with --previous")
check('id="since"' not in doc, "no since block without --previous")
for needle in ("<script src", "javascript:", "download=", "blob:", "jspdf"):
    check(needle not in doc.lower(), f"no {needle} in the report")
check(doc.count("<script") == 1 and 'id="pdf-btn"' in doc and "window.print()" in doc and "claude.use('downloads')" in doc and "Ctrl+P" in doc, "one inline script: Save as PDF via downloads capability, print fallback, keyboard hint")
check(doc.count("window.print()") == 1, "exactly one print call")
check('id="pdf-data"' not in doc, "no PDF embedded unless --pdf")
pdfdoc = open(f"{out}/report.pdf.html", encoding="utf-8").read()
check('<script type="application/pdf" id="pdf-data" data-filename="seo-audit-127.0.0.1-8765-2026-09-03.pdf">JVBERi0xLjQK' in pdfdoc, "--pdf embeds the PDF as base64 with the report filename")
check(".no-print,.toolbar{display:none!important}" in doc and "break-before:page" in doc and "print-color-adjust:exact" in doc, "print rules: hide toolbar, page breaks, exact colors")
check(".scores,.phases,.grid3{grid-template-columns:repeat(3,1fr)}" in doc[doc.index("@media print"):], "print keeps the three-column grids (A4 is narrower than the mobile breakpoint)")
sys.exit(bad)
PY
echo "  ✓ render: document + artifact forms, roadmap, quick wins, since-last-audit, verify column, methodology, print CSS + Save as PDF, tokens, no external assets"
