#!/usr/bin/env bash
# rolepod-seo version bump — rewrites every "version" leaf in the six source
# manifests, then re-renders the shipped copies under plugins/rolepod-seo/.
#
# Usage: scripts/bump-version.sh 0.2.0   (or: make version-bump VERSION=0.2.0)
# Consistency is pinned by tests/static/manifests.sh — run `make test-static` after.
set -euo pipefail

V="${1:?usage: bump-version.sh <x.y.z>}"
case "$V" in
  [0-9]*.[0-9]*.[0-9]*) ;;
  *) echo "expected x.y.z, got: $V" >&2; exit 1 ;;
esac

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

setver() {  # $1 = file, $2 = version
  python3 - "$1" "$2" <<'PY'
import re, sys
path, ver = sys.argv[1], sys.argv[2]
text = open(path).read()
out = re.sub(r'("version"\s*:\s*")[0-9]+\.[0-9]+\.[0-9]+(")',
             lambda m: m.group(1) + ver + m.group(2), text)
if out == text:
    sys.exit(f"{path}: no version field rewritten")
open(path, "w").write(out)
PY
  echo "  ✓ $1 → $2"
}

setver .claude-plugin/plugin.json      "$V"
setver .claude-plugin/marketplace.json "$V"
setver .codex-plugin/plugin.json       "$V"
setver .cursor-plugin/plugin.json      "$V"
setver .cursor-plugin/marketplace.json "$V"
setver gemini-extension.json           "$V"

echo "  → re-rendering plugins/rolepod-seo/"
make -s render
echo "  ✓ bumped to $V — verify: make test-static"
