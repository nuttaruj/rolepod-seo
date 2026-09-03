#!/usr/bin/env bash
# Fixture run: serve site-a, run the collector in both modes, compare the
# per-page table to the golden files, check the JSON shape. No LLM involved.
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=tests/fixture/.out
rm -rf "$OUT"; mkdir -p "$OUT"
BASE="$(bash tests/fixture/serve.sh 0 "$OUT")"
trap 'kill "$(cat '"$OUT"'/server.pid)" 2>/dev/null || true' EXIT
fail=0
# the collector must refuse a loopback target unless --allow-private is given
python3 skills/seo-audit/scripts/collect.py "$BASE/" --out "$OUT/refused" --quiet 2>"$OUT/refused.err" && rc=0 || rc=$?
[ $rc -eq 2 ] && grep -q "refused: private or reserved address" "$OUT/refused.err" || { echo "  ✗ collector should refuse 127.0.0.1 without --allow-private (rc=$rc)"; cat "$OUT/refused.err"; fail=1; }
python3 skills/seo-audit/scripts/collect.py http://169.254.169.254/latest/meta-data/ --out "$OUT/refused2" --quiet 2>"$OUT/refused2.err" && rc=0 || rc=$?
[ $rc -eq 2 ] && grep -q "refused: blocked hostname" "$OUT/refused2.err" || { echo "  ✗ collector should refuse the cloud metadata host"; fail=1; }
for mode in quick full; do
  python3 skills/seo-audit/scripts/collect.py "$BASE/" --mode "$mode" --out "$OUT/$mode" --quiet --allow-private --fixed-time 2026-01-01T00:00:00Z >/dev/null
  sed "s#$BASE#BASE#g" "$OUT/$mode/pages.tsv" > "$OUT/$mode/pages.norm.tsv"
  if ! diff -u "tests/fixture/golden-$mode.tsv" "$OUT/$mode/pages.norm.tsv" >"$OUT/$mode/diff.txt"; then
    echo "  ✗ $mode: pages.tsv differs from tests/fixture/golden-$mode.tsv"; head -30 "$OUT/$mode/diff.txt" | sed 's/^/     /'; fail=1
  fi
done
python3 - "$OUT" "$BASE" <<'PY' || fail=1
import json, sys
out, base = sys.argv[1], sys.argv[2]
bad = 0
def check(cond, msg):
    global bad
    if not cond: print("  ✗ " + msg); bad = 1
q = json.load(open(f"{out}/quick/collect.json")); f = json.load(open(f"{out}/full/collect.json"))
for name, d in (("quick", q), ("full", f)):
    check(d["tool"] == "rolepod-seo/collect" and d["version"] == 1, f"{name}: tool/version")
    check(d["collected_at"] == "2026-01-01T00:00:00Z", f"{name}: fixed time honored")
    check(set(d) >= {"base_url", "mode", "pages", "site"}, f"{name}: top-level keys")
    for p in d["pages"]:
        check(set(p) >= {"url", "role", "status", "final_url", "hops"}, f"{name}: page keys on {p['url']}")
        check("_internal_links" not in p, f"{name}: internal link list leaked into output")
s = f["site"]
check(len(q["pages"]) == 7, f"quick selects home + 6 key pages (got {len(q['pages'])})")
check(q["site"]["site_type"]["type"] == "local", "quick mode also detects the site type")
check(len(f["pages"]) == 10, f"full selects every meaningful page incl. sitemap 404 (got {len(f['pages'])})")
check(not any("privacy" in p["url"] for p in f["pages"]), "legal page skipped in full mode")
check(s["robots"]["agents"]["GPTBot"]["verdict"] == "blocked-all", "GPTBot verdict blocked-all")
check(s["robots"]["agents"]["ClaudeBot"]["verdict"] == "partial", "ClaudeBot falls to wildcard partial")
check(s["robots"]["agents"]["Googlebot"]["via"] == "wildcard", "Googlebot via wildcard")
check(s["sitemap"]["declared_in_robots"] is False, "sitemap not declared in robots")
check(s["sitemap"]["url_count"] == 10, f"sitemap url_count 10 (got {s['sitemap']['url_count']})")
check(s["sitemap"]["listed_but_not_200"] == [f"{base}/old-page.html"], "sitemap 404 detected")
check(s["sitemap"]["listed_but_noindex"] == [f"{base}/blog/post-2.html"], "noindex-in-sitemap detected")
check(s["llms_txt"]["present"] is False, "llms.txt absent")
check(s["platform_hints"] == {"generator": "", "signals": []}, f"platform hints empty on the fixture (got {s.get('platform_hints')})")
check(s["tls_verify"] is True, "tls_verify recorded")
check(s["site_type"]["type"] == "local" and s["site_type"]["confidence"] == "high", f"site type local/high (got {s['site_type']['type']}/{s['site_type']['confidence']})")
check(s["security"] == {"hsts": False, "hsts_value": "", "csp": False, "x_content_type_options": "", "server": s["security"]["server"]}, "security headers recorded (none on the fixture)")
check(s["near_duplicates"] == [], f"no near-duplicate pages on the fixture (got {s['near_duplicates']})")
g = s["link_graph"]
check(g["pages_in_graph"] == 10, f"link graph covers every fetched row (got {g['pages_in_graph']})")
check(g["unreachable_from_home"] == [], f"every 200 page reachable from home (got {g['unreachable_from_home']})")
check("/blog/post-1.html" not in g["low_inlinks"] and set(g["low_inlinks"]) <= {"/faq.html", "/pricing.html", "/about.html", "/contact.html", "/services.html"}, f"low_inlinks only lists key pages (got {g['low_inlinks']})")
check(len(s["duplicates"]["descriptions"]) == 1, "duplicate description services/pricing")
check(s["host_variants"].get("note", "").startswith("not assessed"), "host variants skipped on local")
by = {p["url"].replace(base, ""): p for p in f["pages"]}
check(by["/blog/post-1.html"]["canonical_ok"] == "cross-domain", "post-1 canonical cross-domain")
check(by["/blog/post-1.html"]["author_present"] and "ld:author" in by["/blog/post-1.html"]["author_signals"], "post-1 author via JSON-LD + byline")
check(by["/faq.html"]["faq_visible"] and not by["/faq.html"]["faq_schema"], "faq visible without schema")
check(by["/faq.html"]["question_headings"] == 6, f"faq question headings 6 (got {by['/faq.html']['question_headings']})")
check(by["/services.html"]["h1_count"] == 2 and by["/services.html"]["images_no_alt"] == 1, "services h1x2 + img without alt")
check(by["/blog/post-2.html"]["noindex"] and by["/blog/post-2.html"]["description_len"] == 0 and by["/blog/post-2.html"]["word_count"] < 300, "post-2 noindex, no description, thin")
check(by["/"]["schema_types"] == ["Organization", "WebSite"], f"home schema types (got {by['/']['schema_types']})")
check(set(by["/contact.html"]["contact_signals"]) == {"address", "mailto", "tel"}, "contact NAP signals")
check(by["/old-page.html"]["status"] == 404, "old-page 404 recorded as a row")
check(by["/"]["depth"] == 0 and by["/about.html"]["depth"] == 1 and by["/blog/post-1.html"]["depth"] == 2, f"click depth home 0 / about 1 / post-1 2 (got {by['/']['depth']}, {by['/about.html']['depth']}, {by['/blog/post-1.html']['depth']})")
check(by["/contact.html"]["inlinks"] >= 5 and by["/blog/post-1.html"]["inlinks"] == 1, f"inlinks contact ≥5 / post-1 1 (got {by['/contact.html']['inlinks']}, {by['/blog/post-1.html']['inlinks']})")
check(by["/old-page.html"].get("depth") is None, "404 row has no depth")
sys.exit(bad)
PY
[ $fail -eq 0 ] && echo "  ✓ collector: refuses private/metadata targets; quick + full tables match golden; site facts, link graph, site type verified"
exit $fail
