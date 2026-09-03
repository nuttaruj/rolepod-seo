#!/usr/bin/env bash
# The HTML renderer: structure, print CSS, no external assets, score → status
# mapping, artifact vs document forms.
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=tests/fixture/.out/render; rm -rf "$OUT"; mkdir -p "$OUT"
python3 skills/seo-audit/scripts/render_report.py tests/fixtures/sample-report.json --out "$OUT/report.html" >/dev/null
python3 skills/seo-audit/scripts/render_report.py tests/fixtures/sample-report.json --artifact --out "$OUT/report.artifact.html" >/dev/null
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
for needle in ("<script", "javascript:"):
    check(needle not in doc.lower(), f"no {needle} in the report")
sys.exit(bad)
PY
echo "  ✓ render: document + artifact forms, print CSS, tokens, no external assets, chips"
