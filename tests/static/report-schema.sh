#!/usr/bin/env bash
# docs/report-schema.md (consumer doc) and the skill's report.md (model doc)
# describe the same JSON; the sample sidecar carries every required key.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 - <<'PY'
import json, re, sys
doc = open("docs/report-schema.md").read()
ref = open("skills/seo-audit/references/report.md").read()
fields = sorted(set(re.findall(r"^\| `([a-z_.\[\]]+)` \|", doc, re.M)))
bad = 0
for f in fields:
    leaf = f.split(".")[-1].replace("[]", "")
    if f'"{leaf}"' not in ref:
        print(f"  ✗ docs field `{f}` not in skills/seo-audit/references/report.md"); bad = 1
sample = json.load(open("tests/fixtures/sample-report.json"))
required = ["schema", "schema_version", "generated_at", "site", "collection", "scores", "findings", "not_assessed", "pages"]
for k in required:
    if k not in sample: print(f"  ✗ sample-report.json missing `{k}`"); bad = 1
if sample.get("schema") != "rolepod-seo/report" or sample.get("schema_version") != 1:
    print("  ✗ sample-report.json schema/version"); bad = 1
for d in ("seo", "geo", "aeo"):
    s = sample["scores"].get(d, {})
    if not (isinstance(s.get("score"), int) and 1 <= s["score"] <= 10) and s.get("band") != "not-assessed":
        print(f"  ✗ sample score {d} out of range"); bad = 1
fkeys = {"id", "dimension", "signal", "page", "severity", "status", "evidence", "fix", "owner", "effort", "impact", "priority"}
for i, f in enumerate(sample["findings"]):
    miss = fkeys - set(f)
    if miss: print(f"  ✗ finding[{i}] missing {sorted(miss)}"); bad = 1
if not fields: print("  ✗ docs/report-schema.md has no field table"); bad = 1
if bad: sys.exit(1)
print(f"  ✓ report schema: {len(fields)} documented fields present in the skill; sample sidecar valid")
PY
