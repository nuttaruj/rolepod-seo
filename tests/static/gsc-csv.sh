#!/usr/bin/env bash
# gsc_csv.py: CSV and zip exports, buckets, join with the audit sidecar. Optional input — must never be required by the audit.
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=tests/fixture/.out/gsc; rm -rf "$OUT"; mkdir -p "$OUT"
python3 - "$OUT" <<'PY'
import zipfile, sys
z = zipfile.ZipFile(f"{sys.argv[1]}/export.zip", "w")
z.write("tests/fixtures/gsc/Pages.csv", "Pages.csv"); z.write("tests/fixtures/gsc/Queries.csv", "Queries.csv"); z.close()
PY
python3 skills/seo-fix-plan/scripts/gsc_csv.py "$OUT/export.zip" --pages tests/fixtures/sample-report.json --out "$OUT/run" --fixed-time 2026-01-01T00:00:00Z >/dev/null
python3 - "$OUT/run/gsc.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); bad = 0
def check(c, m):
    global bad
    if not c: print("  ✗ " + m); bad = 1
check(d["tool"] == "rolepod-seo/gsc" and d["version"] == 1, "tool/version")
check({s["kind"] for s in d["sources"]} == {"pages", "queries"} and all(s["rows"] > 0 for s in d["sources"]), f"zip yields pages + queries tables ({d['sources']})")
p = d["pages"]; q = d["queries"]
check(p["summary"]["clicks"] == 181 and p["summary"]["impressions"] == 4850, f"page totals (got {p['summary']})")
check([r["item"].split("8765")[1] for r in p["quick_wins"]] == ["/services.html", "/pricing.html", "/areas/leeds.html"], f"quick wins = position 4–20 (got {[r['item'] for r in p['quick_wins']]})")
check([r["item"].split("8765")[1] for r in p["low_ctr_top3"]] == ["/blog/post-1.html"], f"low CTR top-3 (got {[r['item'] for r in p['low_ctr_top3']]})")
check([r["item"].split("8765")[1] for r in p["seen_not_clicked"]] == ["/pricing.html", "/blog/post-1.html", "/areas/leeds.html"], f"seen not clicked (got {[r['item'] for r in p['seen_not_clicked']]})")
check([r["item"] for r in q["quick_wins"]] == ["boiler repair leeds", "drain unblocking cost"], f"query quick wins (got {[r['item'] for r in q['quick_wins']]})")
check([r["item"] for r in q["low_ctr_top3"]] == ["plumber near me"], "query low CTR top-3")
j = d["pages_join"]
check(len(j["audited"]) == 4 and any(a["url"].endswith("/faq.html") and a["clicks"] == 40 for a in j["audited"]), f"audited pages joined by URL (got {len(j['audited'])})")
check(any(a.get("in_search_console") is False for a in j["audited"]), "audited page absent from the export is marked")
check([r["item"].split("8765")[1] for r in j["in_search_console_not_audited"]] == ["/pricing.html", "/blog/post-1.html", "/areas/leeds.html"], f"pages in Search Console but not audited, by impressions (got {[r['item'] for r in j['in_search_console_not_audited']]})")
sys.exit(bad)
PY
python3 skills/seo-fix-plan/scripts/gsc_csv.py tests/fixtures/gsc/Queries.csv --out "$OUT/q" --fixed-time 2026-01-01T00:00:00Z >/dev/null
python3 -c "import json,sys; d=json.load(open('$OUT/q/gsc.json')); sys.exit(0 if d['pages'] is None and d['queries']['summary']['rows']==5 else 1)" || { echo "  ✗ single Queries.csv works without a Pages table"; exit 1; }
printf 'Country,Clicks,Impressions,CTR,Position\nGB,1,2,50%%,1\n' > "$OUT/Countries.csv"
out=$(python3 skills/seo-fix-plan/scripts/gsc_csv.py "$OUT/Countries.csv" --out "$OUT/c" 2>&1) && rc=0 || rc=$?
[ $rc -eq 2 ] && grep -q "no Pages or Queries table" <<<"$out" || { echo "  ✗ unrelated CSV should exit 2 with a hint"; exit 1; }
grep -q "Quick wins" "$OUT/run/gsc.md" && grep -q "In Search Console but not audited" "$OUT/run/gsc.md" || { echo "  ✗ gsc.md sections"; exit 1; }
echo "  ✓ gsc_csv.py: zip + CSV exports parsed, buckets and audit join verified, unrelated CSV refused"
