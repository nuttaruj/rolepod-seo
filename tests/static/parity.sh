#!/usr/bin/env bash
# The shipped tree plugins/rolepod-seo/ must equal the source (make render).
set -euo pipefail
cd "$(dirname "$0")/../.."
fail=0
[ -d plugins/rolepod-seo/skills ] || { echo "  ✗ plugins/rolepod-seo/skills missing — run make render"; exit 1; }
if ! diff -r --exclude=.DS_Store --exclude=__pycache__ skills plugins/rolepod-seo/skills >/dev/null; then
  echo "  ✗ plugins/rolepod-seo/skills differs from skills/ — run make render"; diff -rq --exclude=.DS_Store --exclude=__pycache__ skills plugins/rolepod-seo/skills | sed 's/^/     /'; fail=1
fi
cmp -s .claude-plugin/plugin.json plugins/rolepod-seo/.claude-plugin/plugin.json || { echo "  ✗ nested .claude-plugin/plugin.json differs — run make render"; fail=1; }
cmp -s .codex-plugin/plugin.json plugins/rolepod-seo/.codex-plugin/plugin.json || { echo "  ✗ nested .codex-plugin/plugin.json differs — run make render"; fail=1; }
[ $fail -eq 0 ] && echo "  ✓ plugins/rolepod-seo/ matches skills/ + manifests"
exit $fail
