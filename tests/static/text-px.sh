#!/usr/bin/env bash
# collect.py text_px: estimated SERP pixel width — combining marks are zero-width, glyph widths differ.
set -euo pipefail
cd "$(dirname "$0")/../.."
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import sys
sys.path.insert(0, "skills/seo-audit/scripts")
from collect import text_px
bad = 0
def check(c, m):
    global bad
    if not c: print("  ✗ " + m); bad = 1
check(text_px("", 20) == 0, "empty string is 0px")
check(text_px("Hello", 20) == 46, f"Arial table pinned: 'Hello' at 20px is 46px (got {text_px('Hello', 20)})")
check(text_px("a\n        b", 14) == text_px("a b", 14), "whitespace collapsed before measuring")
check(text_px("ที่นี่", 20) == text_px("ทน", 20), f"Thai marks add no width ({text_px('ที่นี่', 20)} vs {text_px('ทน', 20)})")
check(text_px("iiii", 20) < text_px("WWWW", 20), "narrow glyphs narrower than wide ones")
check(text_px("日本", 20) == 40, f"wide CJK is 1em each (got {text_px('日本', 20)})")
check(text_px("a", 14) < text_px("a", 20), "width scales with font size")
sys.exit(bad)
PY
echo "  ✓ text-px"
