#!/usr/bin/env bash
# schema-minimums.md (model doc) and validate.py (machine) must agree on the
# Required column; the validator must pass the fixture's good block and fail
# the deliberately incomplete one.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 - <<'PY'
import importlib.util, re, sys
spec = importlib.util.spec_from_file_location("v", "skills/seo-schema/scripts/validate.py")
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
doc = open("skills/seo-schema/references/schema-minimums.md").read()
rows = re.findall(r"^\| `([A-Za-z]+)` \| (.+?) \| .+? \| .+? \|$", doc, re.M)
bad = 0
seen = set()
for ty, req in rows:
    seen.add(ty)
    want = []
    for cell in req.split(", "):
        cell = cell.strip().strip("`")
        if " / " in cell:
            want.append(tuple(c.strip().strip("`") for c in cell.split(" / ")))
        else:
            want.append(cell)
    have = v.REQUIRED.get(ty)
    if have is None:
        print(f"  ✗ {ty}: in schema-minimums.md but not in validate.py REQUIRED"); bad = 1
    elif [tuple(x) if isinstance(x, tuple) else x for x in have] != want:
        print(f"  ✗ {ty}: doc {want} != validator {have}"); bad = 1
for ty in v.REQUIRED:
    if ty not in seen:
        print(f"  ✗ {ty}: in validate.py but missing from schema-minimums.md"); bad = 1
if bad: sys.exit(1)
print(f"  ✓ schema minimums: {len(rows)} types in lockstep between the reference and validate.py")
PY
out=$(python3 skills/seo-schema/scripts/validate.py tests/fixtures/site-a/index.html) && rc=0 || rc=$?
[ $rc -eq 0 ] && grep -q "ok .*Organization" <<<"$out" && grep -q "ok .*WebSite" <<<"$out" || { echo "  ✗ validate.py should pass the fixture home block"; echo "$out" | sed 's/^/     /'; exit 1; }
out=$(python3 skills/seo-schema/scripts/validate.py tests/fixtures/site-a/blog/post-1.html) && rc=0 || rc=$?
[ $rc -eq 1 ] && grep -q "FAIL .*BlogPosting .*missing image" <<<"$out" && grep -q "ok .*Person" <<<"$out" || { echo "  ✗ validate.py should flag BlogPosting without image on post-1"; echo "$out" | sed 's/^/     /'; exit 1; }
out=$(echo '{"@context":"https://schema.org","@type":"Product","name":"X"}' | python3 skills/seo-schema/scripts/validate.py -) && rc=0 || rc=$?
[ $rc -eq 1 ] && grep -q "missing offers / review / aggregateRating" <<<"$out" || { echo "  ✗ validate.py any-of rule"; echo "$out"; exit 1; }
out=$(echo '{"@type":"Product",' | python3 skills/seo-schema/scripts/validate.py -) && rc=0 || rc=$?
[ $rc -eq 1 ] && grep -q "does not parse" <<<"$out" || { echo "  ✗ validate.py parse failure path"; exit 1; }
echo "  ✓ validate.py: fixture home passes, post-1 fails on image, any-of + parse paths"
