#!/usr/bin/env bash
# Manifests parse, agree on one version, and point at paths that exist.
set -euo pipefail
cd "$(dirname "$0")/../.."
fail=0
for f in .claude-plugin/plugin.json .claude-plugin/marketplace.json .codex-plugin/plugin.json \
         .cursor-plugin/plugin.json .cursor-plugin/marketplace.json gemini-extension.json \
         .agents/plugins/marketplace.json plugins/rolepod-seo/.claude-plugin/plugin.json \
         plugins/rolepod-seo/.codex-plugin/plugin.json; do
  python3 -m json.tool "$f" >/dev/null 2>&1 || { echo "  ✗ $f: invalid JSON"; fail=1; }
done
python3 - <<'PY' || fail=1
import json, re, sys, os
v = json.load(open(".claude-plugin/plugin.json"))["version"]
bad = 0
for f in [".claude-plugin/marketplace.json", ".codex-plugin/plugin.json", ".cursor-plugin/plugin.json",
          ".cursor-plugin/marketplace.json", "gemini-extension.json",
          "plugins/rolepod-seo/.claude-plugin/plugin.json", "plugins/rolepod-seo/.codex-plugin/plugin.json"]:
    vs = set(re.findall(r'"version"\s*:\s*"([0-9]+\.[0-9]+\.[0-9]+)"', open(f).read()))
    if vs != {v}:
        print(f"  ✗ {f}: version(s) {sorted(vs)} != {v}"); bad = 1
if not re.search(r"^## \[" + re.escape(v) + r"\]", open("CHANGELOG.md").read(), re.M):
    print(f"  ✗ CHANGELOG.md has no [{v}] section"); bad = 1
mk = json.load(open(".claude-plugin/marketplace.json"))
src = mk["plugins"][0]["source"]
if not os.path.isdir(src): print(f"  ✗ claude marketplace source {src} missing"); bad = 1
ag = json.load(open(".agents/plugins/marketplace.json"))
p = ag["plugins"][0]["source"]["path"]
if not os.path.isdir(p): print(f"  ✗ codex marketplace path {p} missing"); bad = 1
cx = json.load(open(".codex-plugin/plugin.json"))
if "mcpServers" in cx or "hooks" in cx: print("  ✗ codex plugin.json declares mcpServers/hooks — Phase 1 is skills-only"); bad = 1
for f in [".claude-plugin/plugin.json", "gemini-extension.json"]:
    if "mcpServers" in json.load(open(f)): print(f"  ✗ {f} declares mcpServers — Phase 1 is skills-only"); bad = 1
sys.exit(bad)
PY
[ $fail -eq 0 ] && echo "  ✓ manifests parse, version $(python3 -c 'import json;print(json.load(open(".claude-plugin/plugin.json"))["version"])') in lockstep, skills-only"
exit $fail
