#!/usr/bin/env bash
# export_pdf.py: browser discovery, and a real PDF from the sample report when a browser exists.
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=tests/fixture/.out/pdf; rm -rf "$OUT"; mkdir -p "$OUT"
python3 skills/seo-audit/scripts/render_report.py tests/fixtures/sample-report.json --out "$OUT/report.html" >/dev/null
browser=$(python3 skills/seo-audit/scripts/export_pdf.py --find-only) && rc=0 || rc=$?
if [ $rc -ne 0 ]; then
  out=$(python3 skills/seo-audit/scripts/export_pdf.py "$OUT/report.html" --out "$OUT/report.pdf" 2>&1) && rc2=0 || rc2=$?
  [ $rc2 -eq 2 ] && grep -q "Ctrl+P" <<<"$out" || { echo "  ✗ export_pdf.py should exit 2 with the print hint when no browser exists"; echo "$out"; exit 1; }
  echo "  ✓ export_pdf.py: no Chromium-family browser here — hint path verified, PDF export not exercised"
  exit 0
fi
python3 skills/seo-audit/scripts/export_pdf.py "$OUT/report.html" --out "$OUT/report.pdf" --timeout 120 >/dev/null || { echo "  ✗ export_pdf.py failed with $browser"; exit 1; }
python3 - "$OUT/report.pdf" <<'PYCHK'
import sys
p = sys.argv[1]; raw = open(p, "rb").read()
assert raw[:5] == b"%PDF-", "not a PDF"
assert len(raw) > 30000, f"suspiciously small PDF ({len(raw)} bytes)"
assert b"/Font" in raw, "no fonts in the PDF"
PYCHK
python3 skills/seo-audit/scripts/render_report.py tests/fixtures/sample-report.json --artifact --pdf "$OUT/report.pdf" --out "$OUT/report.artifact.html" >/dev/null
grep -q 'id="pdf-data" data-filename="seo-audit-127.0.0.1-8765-2026-09-03.pdf">JVBERi0' "$OUT/report.artifact.html" || { echo "  ✗ real PDF not embedded in the artifact form"; exit 1; }
echo "  ✓ export_pdf.py: $(basename "$browser") produced a $(( $(wc -c < "$OUT/report.pdf") / 1024 )) KB PDF with fonts; embedded into the artifact form"
