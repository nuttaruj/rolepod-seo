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
check(doc.count('class="card ') == 3, "three score cards")
check('class="card warn"' in doc and doc.count('class="card warn"') == 3, "sample scores 6/5/5 → three Needs Work cards")
check("@media print" in doc and "@page" in doc, "print CSS present")
check("prefers-color-scheme: dark" in doc and ':root[data-theme="dark"]' in doc and ':root:not([data-theme="light"])' in doc, "light/dark tokens in all three states")
check("var(--bg)" in doc and "body{margin:0;background:var(--bg)" in doc, "body background from a token")
ext = re.findall(r'(?:<link[^>]+href|<script[^>]+src|@import|url\()\s*=?\s*["\']?(https?://[^"\')\s]+)', doc)
check(not ext, f"no external assets (found {ext[:3]})")
check('class="chip p-critical">Critical<' in doc and 'class="chip p-quick-win">Quick win<' in doc, "priority chips rendered")
check('class="chip fail">Fail<' in doc and 'class="chip pass">Pass<' in doc, "status chips rendered")
check("<th>Exact change</th>" in doc and "<th>Owner</th>" in doc, "matrix columns")
check("ai-bot-policy" in doc and 'id="decisions"' in doc, "info/human finding lands in Decisions")
prevdoc = open(f"{out}/report.prev.html", encoding="utf-8").read()
check('<section id="roadmap"' in doc and "Week 1 — unblock" in doc and "Ongoing — decide, measure, re-audit" in doc, "roadmap phases derived from priorities")
check("<h3>Fix first</h3>" in doc and "<h3>Quick wins</h3>" in doc, "fix-first + quick-wins boxes in the summary")
check('<section id="method"' in doc and "How to read the scores" in doc, "methodology section")
check("Site type: <strong>local service</strong>" in doc, "site type line from site.site_type")
check("<th>Verify</th>" in doc and "canonical_ok = self" in doc, "verify column when a finding carries verify")
check("Watch: Search Console" in doc, "leading indicator lands in the Ongoing phase")
check('1 fail</span>' in doc and 'class="chip fail">404</span>' in doc, "per-page finding counts + status chips in the pages table")
check(doc.count("</b> fail · <b>") == 3 and "1 optional (no Google effect)" in doc, "fail/warn/pass counts on the three cards + optional count")
check("By group: <strong>technical</strong> — 2 fail" in doc, "SEO findings broken down by signal group (canonical + h1 → technical)")
check("<strong>trust</strong> — 1 pass" in doc, "GEO ai-bot-policy → trust")
check('<section id="optional"' in doc and "No effect on Google Search" in doc and 'faq-schema</strong> <span class="chip none">' in doc, "seo_effect none → optional section, labelled, listed after roadmap")
check(doc.index('<section id="roadmap"') < doc.index('<section id="optional"') < doc.index('<section id="strengths"'), "optional section sits after the roadmap")
mat = doc[doc.index('<section id="matrix"'):doc.index('<section id="roadmap"')]
check("faq-schema" not in mat, "no-effect finding excluded from the priority matrix")
check("faq-schema" not in doc[doc.index("<h3>Quick wins</h3>"):doc.index('<section id="pages"')], "no-effect finding excluded from quick wins")
aeo = doc[doc.index('<section id="aeo"'):doc.index('<section id="matrix"')]
check("0 fail · 0 warn · 0 pass" in aeo and 'chip none">no effect on Google Search' in aeo, "AEO section counts exclude the none row but still lists it, labelled")
for f_, want in (({"signal": "faq-schema"}, "none"), ({"signal": "llms-txt"}, "none"), ({"signal": "howto-schema"}, "none"), ({"signal": "canonical"}, "direct"), ({"signal": "faq-schema", "seo_effect": "direct"}, "direct"), ({"signal": "author", "seo_effect": "indirect"}, "indirect")):
    check(r.effect_of(f_) == want, f"effect_of({f_}) = {r.effect_of(f_)} != {want}")
for sig, want in (("canonical", "technical"), ("faq-schema", "schema"), ("answer-block", "answer"), ("ai-bot-policy", "trust"), ("content-depth", "content"), ("click-depth", "technical"), ("mixed-content", "technical"), ("organization-schema", "schema"), ("xyz", "other")):
    check(r.signal_group(sig) == want, f"signal_group({sig!r}) = {r.signal_group(sig)} != {want}")
check('<section id="since"' in prevdoc and "<h3>Fixed</h3>" in prevdoc and "<h3>New</h3>" in prevdoc, "since-last-audit section with --previous")
check('<section id="since"' not in doc, "no since section without --previous")
for needle in ("<script", "javascript:", "download=", "blob:", "jspdf"):
    check(needle not in doc.lower(), f"no {needle} in the report")
check('onclick="window.print()"' in doc and "Save as PDF" in doc and "Ctrl+P" in doc, "Save as PDF button (window.print) + keyboard fallback")
check(".no-print,.toolbar{display:none!important}" in doc and "break-before:page" in doc and "print-color-adjust:exact" in doc, "print rules: hide toolbar, page breaks, exact colors")
check(doc.count("window.print()") == 1, "exactly one print call, no other JS")
sys.exit(bad)
PY
echo "  ✓ render: document + artifact forms, roadmap, quick wins, since-last-audit, verify column, methodology, print CSS + Save as PDF, tokens, no external assets"
