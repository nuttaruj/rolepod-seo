#!/usr/bin/env bash
# scripts/install-opencode.sh: syntax, fallback id list pinned to skills/, global +
# project installs land the exact skill trees + a marker in version lockstep, no
# download from a checkout, junk stripped, a re-run replaces stale files and drops
# ids no longer shipped, --uninstall removes only rolepod-seo and never follows
# a hostile marker outside skills/.
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$PWD"
fail=0
S=scripts/install-opencode.sh
bash -n "$S" || { echo "  ✗ $S: syntax"; exit 1; }
want="$(ls -d skills/*/ | xargs -n1 basename | sort | tr '\n' ' ' | sed 's/ $//')"
have="$(sed -n 's/^FALLBACK_IDS="\(.*\)"$/\1/p' "$S" | tr ' ' '\n' | sort | tr '\n' ' ' | sed 's/ $//')"
[ "$want" = "$have" ] || { echo "  ✗ FALLBACK_IDS ($have) != skills/ ($want)"; fail=1; }
v="$(python3 -c 'import json;print(json.load(open(".claude-plugin/plugin.json"))["version"])')"
T="$(mktemp -d -t rolepod-seo-octest.XXXXXX)"; trap 'rm -rf "$T"' EXIT
# From a checkout the script must never download: an impossible ref makes any download fail loudly.
export ROLEPOD_SEO_REF=not-a-ref-0000

# global scope (target overridden) — a foreign skill next to ours must survive everything
mkdir -p "$T/global/skills/other-skill"; echo "---" > "$T/global/skills/other-skill/SKILL.md"
ROLEPOD_SEO_OPENCODE_TARGET="$T/global" bash "$S" >/dev/null || { echo "  ✗ global install exited non-zero"; fail=1; }
for id in $want; do
  [ -f "$T/global/skills/$id/SKILL.md" ] || { echo "  ✗ global: skills/$id/SKILL.md missing"; fail=1; continue; }
  diff -r --exclude=__pycache__ --exclude=.DS_Store --exclude='*.pyc' "skills/$id" "$T/global/skills/$id" >/dev/null \
    || { echo "  ✗ global: skills/$id differs from source"; fail=1; }
done
mv="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["version"])' "$T/global/rolepod-seo-version.json" 2>/dev/null || echo none)"
[ "$mv" = "$v" ] || { echo "  ✗ marker version $mv != $v"; fail=1; }
ms="$(python3 -c 'import json,sys;print(" ".join(sorted(json.load(open(sys.argv[1]))["skills"])))' "$T/global/rolepod-seo-version.json" 2>/dev/null || echo none)"
[ "$ms" = "$want" ] || { echo "  ✗ marker skills ($ms) != skills/ ($want)"; fail=1; }

# re-run replaces a stale file instead of merging over it
echo stale > "$T/global/skills/seo-audit/stale.txt"
ROLEPOD_SEO_OPENCODE_TARGET="$T/global" bash "$S" >/dev/null || { echo "  ✗ global re-run exited non-zero"; fail=1; }
[ ! -e "$T/global/skills/seo-audit/stale.txt" ] || { echo "  ✗ re-run kept a stale file"; fail=1; }

# project scope → $PWD/.opencode/skills
mkdir -p "$T/proj"
( cd "$T/proj" && bash "$ROOT/$S" --project >/dev/null ) || { echo "  ✗ --project install exited non-zero"; fail=1; }
[ -f "$T/proj/.opencode/skills/seo-audit/SKILL.md" ] || { echo "  ✗ --project: .opencode/skills/seo-audit/SKILL.md missing"; fail=1; }
[ -f "$T/proj/.opencode/rolepod-seo-version.json" ] || { echo "  ✗ --project: marker missing"; fail=1; }

# a staged checkout with junk: __pycache__ / .pyc / .DS_Store must not be copied
mkdir -p "$T/fake/scripts" "$T/fake/.claude-plugin"
cp "$S" "$T/fake/scripts/"; cp -R skills "$T/fake/skills"; cp .claude-plugin/plugin.json "$T/fake/.claude-plugin/"
mkdir -p "$T/fake/skills/seo-audit/scripts/__pycache__"; echo x > "$T/fake/skills/seo-audit/scripts/__pycache__/collect.cpython-312.pyc"
echo x > "$T/fake/skills/seo-schema/junk.pyc"; echo x > "$T/fake/skills/seo-fix-plan/.DS_Store"
ROLEPOD_SEO_OPENCODE_TARGET="$T/strip" bash "$T/fake/scripts/install-opencode.sh" >/dev/null || { echo "  ✗ staged-checkout install exited non-zero"; fail=1; }
junk="$(find "$T/strip/skills" \( -name __pycache__ -o -name '*.pyc' -o -name .DS_Store \) | head -3 || true)"
[ -z "$junk" ] || { echo "  ✗ junk copied into the target: $junk"; fail=1; }
[ -f "$T/strip/skills/seo-audit/SKILL.md" ] || { echo "  ✗ staged checkout: seo-audit missing"; fail=1; }

# a later release that drops a skill removes it from the target on re-install
rm -rf "$T/fake/skills/seo-schema"
ROLEPOD_SEO_OPENCODE_TARGET="$T/strip" bash "$T/fake/scripts/install-opencode.sh" >/dev/null || { echo "  ✗ re-install after a dropped skill exited non-zero"; fail=1; }
[ ! -d "$T/strip/skills/seo-schema" ] || { echo "  ✗ dropped skill seo-schema still installed"; fail=1; }
ms="$(python3 -c 'import json,sys;print(" ".join(sorted(json.load(open(sys.argv[1]))["skills"])))' "$T/strip/rolepod-seo-version.json" 2>/dev/null || echo none)"
[ "$ms" = "seo-audit seo-fix-plan seo-page-brief" ] || { echo "  ✗ marker after a dropped skill: $ms"; fail=1; }

# uninstall removes ours, keeps the foreign skill
ROLEPOD_SEO_OPENCODE_TARGET="$T/global" bash "$S" --uninstall >/dev/null || { echo "  ✗ --uninstall exited non-zero"; fail=1; }
for id in $want; do [ ! -d "$T/global/skills/$id" ] || { echo "  ✗ uninstall left skills/$id"; fail=1; }; done
[ ! -e "$T/global/rolepod-seo-version.json" ] || { echo "  ✗ uninstall left the marker"; fail=1; }
[ -f "$T/global/skills/other-skill/SKILL.md" ] || { echo "  ✗ uninstall removed a foreign skill"; fail=1; }
# uninstall with no marker, and with an empty skills list, falls back to the pinned id list
for case in bare empty; do
  mkdir -p "$T/$case/skills/seo-schema"; echo "---" > "$T/$case/skills/seo-schema/SKILL.md"
done
echo '{"name":"rolepod-seo","version":"0.0.0","skills":[]}' > "$T/empty/rolepod-seo-version.json"
for case in bare empty; do
  ROLEPOD_SEO_OPENCODE_TARGET="$T/$case" bash "$S" --uninstall >/dev/null || { echo "  ✗ --uninstall ($case marker) exited non-zero"; fail=1; }
  [ ! -d "$T/$case/skills/seo-schema" ] || { echo "  ✗ uninstall with $case marker left skills/seo-schema"; fail=1; }
done
# a hostile marker never removes anything outside skills/<id>
mkdir -p "$T/evil/skills/seo-audit" "$T/evil/skills/other-skill" "$T/evil/sibling"
echo "---" > "$T/evil/skills/seo-audit/SKILL.md"; echo "---" > "$T/evil/skills/other-skill/SKILL.md"; echo keep > "$T/evil/sibling/keep"
echo '{"skills":["..","../..","","other-skill/x","skills","seo-audit",".."]}' > "$T/evil/rolepod-seo-version.json"
ROLEPOD_SEO_OPENCODE_TARGET="$T/evil" bash "$S" --uninstall >/dev/null || { echo "  ✗ --uninstall (hostile marker) exited non-zero"; fail=1; }
[ -f "$T/evil/sibling/keep" ] && [ -f "$T/evil/skills/other-skill/SKILL.md" ] || { echo "  ✗ hostile marker escaped skills/<id>"; fail=1; }
[ ! -d "$T/evil/skills/seo-audit" ] || { echo "  ✗ hostile marker: the valid id was not removed"; fail=1; }
# unknown flag is an error
bash "$S" --nope >/dev/null 2>&1 && { echo "  ✗ unknown flag accepted"; fail=1; }

[ $fail -eq 0 ] && echo "  ✓ install-opencode.sh: global + project install ($v, $(echo $want | wc -w | tr -d ' ') skills), no download from a checkout, junk stripped, stale + dropped skills removed, uninstall keeps foreign skills and ignores hostile ids"
exit $fail
