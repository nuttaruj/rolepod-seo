#!/usr/bin/env bash
# collect.py Page: heading outline on malformed markup follows the browser's HTML tree rules.
set -euo pipefail
cd "$(dirname "$0")/../.."
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import sys
sys.path.insert(0, "skills/seo-audit/scripts")
from collect import Page
bad = 0
def check(c, m):
    global bad
    if not c: print("  ✗ " + m); bad = 1
def outline(html):
    p = Page("https://example.com/"); p.feed(html); p.close(); return p.outline
check(outline("<h1>A</h1><h2>B</h2>") == [(1, "A"), (2, "B")], "well-formed headings kept in order")
got = outline("<h1>A</h1><h3>Unclosed<h2>Next</h2>")
check(got == [(1, "A"), (3, "Unclosed"), (2, "Next")], f"a new heading closes an unclosed one, which stays in the outline (got {got})")
got = outline("<h2>Two</h4><p>after</p>")
check(got == [(2, "Two")], f"a mismatched end tag closes the open heading, as browsers do (got {got})")
sys.exit(bad)
PY
echo "  ✓ headings"
