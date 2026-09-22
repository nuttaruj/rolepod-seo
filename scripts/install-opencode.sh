#!/usr/bin/env bash
# rolepod-seo → opencode. opencode discovers skills from plain files —
# ~/.config/opencode/skills/<id>/SKILL.md globally, <project>/.opencode/skills/<id>/SKILL.md
# per project (opencode.ai/v2/docs/skills) — and has no marketplace, so this
# script copies the skill directories there and writes a version marker.
#
# From a checkout:
#   scripts/install-opencode.sh [--project] [--uninstall]
# Without one (install and update are the same command):
#   curl -fsSL https://raw.githubusercontent.com/nuttaruj/rolepod-seo/main/scripts/install-opencode.sh | bash -s -- [--project] [--uninstall]
#
# Flags:
#   --project    write into $PWD/.opencode/ instead of ~/.config/opencode/
#   --uninstall  remove the rolepod-seo skills and the marker; nothing else is touched
# Env:
#   ROLEPOD_SEO_OPENCODE_TARGET  opencode config dir to write into (overrides both scopes)
#   ROLEPOD_SEO_REF              git ref to download when not run from a checkout (default main;
#                                ignored from a checkout, which installs its own skills/)
set -euo pipefail

REPO="nuttaruj/rolepod-seo"
RAW="https://raw.githubusercontent.com/$REPO/main/scripts/install-opencode.sh"
# Fallback for --uninstall when no usable marker is present;
# tests/static/opencode-install.sh pins this list to skills/.
FALLBACK_IDS="seo-audit seo-fix-plan seo-page-brief seo-schema"

SCOPE=global
MODE=install
for a in "$@"; do
  case "$a" in
    --project)   SCOPE=project ;;
    --uninstall) MODE=uninstall ;;
    -h|--help)
      cat <<'USAGE'
usage: install-opencode.sh [--project] [--uninstall]
  --project    install into $PWD/.opencode/skills/ (default: ~/.config/opencode/skills/)
  --uninstall  remove the rolepod-seo skills + marker from that directory
env: ROLEPOD_SEO_OPENCODE_TARGET=<config dir>  ROLEPOD_SEO_REF=<git ref, default main>
USAGE
      exit 0 ;;
    *) echo "install-opencode.sh: unknown flag: $a (try --help)" >&2; exit 2 ;;
  esac
done

# How this run was invoked — a checkout path, or the curl form when piped.
CHECKOUT=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  if [ -d "$here/skills" ] && [ -f "$here/.claude-plugin/plugin.json" ]; then CHECKOUT="$here"; fi
fi

if [ -n "${ROLEPOD_SEO_OPENCODE_TARGET:-}" ]; then
  TARGET="$ROLEPOD_SEO_OPENCODE_TARGET"
elif [ "$SCOPE" = project ]; then
  TARGET="$PWD/.opencode"
else
  TARGET="$HOME/.config/opencode"
  if [ -n "${OPENCODE_CONFIG_DIR:-}" ] && [ "$OPENCODE_CONFIG_DIR" != "$TARGET" ]; then
    echo "  ! OPENCODE_CONFIG_DIR=$OPENCODE_CONFIG_DIR — opencode started from this shell reads that directory as well (higher priority than $TARGET)." >&2
    echo "    Installing into $TARGET. To install there instead:" >&2
    if [ -n "$CHECKOUT" ]; then
      echo "      ROLEPOD_SEO_OPENCODE_TARGET=\"\$OPENCODE_CONFIG_DIR\" ${BASH_SOURCE[0]} $*" >&2
    else
      echo "      curl -fsSL $RAW | ROLEPOD_SEO_OPENCODE_TARGET=\"\$OPENCODE_CONFIG_DIR\" bash -s -- $*" >&2
    fi
  fi
fi
MARKER="$TARGET/rolepod-seo-version.json"

# A skill id is one path segment of [A-Za-z0-9._-]; anything else (.., a slash,
# an empty string) never reaches rm -rf.
valid_id() { case "$1" in ''|.|..|*/*|*[!A-Za-z0-9._-]*) return 1 ;; esac; return 0; }
marker_ids() {  # ids recorded in the marker, validated; empty when unusable
  local out="" id
  [ -f "$MARKER" ] || return 0
  set -f   # no globbing of marker entries before valid_id sees them
  for id in $(python3 -c 'import json,sys;print(" ".join(str(s) for s in json.load(open(sys.argv[1])).get("skills", [])))' "$MARKER" 2>/dev/null || true); do
    valid_id "$id" && out="$out $id"
  done
  set +f
  printf '%s' "${out# }"
}

# ── uninstall ────────────────────────────────────────────────────────────
if [ "$MODE" = uninstall ]; then
  ids="$(marker_ids)"
  [ -n "$ids" ] || ids="$FALLBACK_IDS"
  removed=0
  for id in $ids; do
    valid_id "$id" || continue
    if [ -d "$TARGET/skills/$id" ]; then rm -rf "$TARGET/skills/$id"; removed=$((removed+1)); fi
  done
  rm -f "$MARKER"
  echo "  ✓ rolepod-seo removed from $TARGET/skills ($removed skill dir(s)); other skills untouched"
  exit 0
fi

# ── source: this checkout, else a tarball of the repo ────────────────────
command -v python3 >/dev/null 2>&1 || { echo "install-opencode.sh: python3 is required (the skills run it too)" >&2; exit 1; }
SRC="$CHECKOUT"
TMP=""
if [ -z "$SRC" ]; then
  REF="${ROLEPOD_SEO_REF:-main}"
  TMP="$(mktemp -d -t rolepod-seo-install.XXXXXX)"
  trap 'rm -rf "$TMP"' EXIT INT TERM
  echo "  → downloading $REPO@$REF"
  curl -fsSL "https://github.com/$REPO/archive/$REF.tar.gz" | tar -xz -C "$TMP"
  for d in "$TMP"/*/; do SRC="${d%/}"; break; done
  [ -n "$SRC" ] && [ -d "$SRC/skills" ] && [ -f "$SRC/.claude-plugin/plugin.json" ] \
    || { echo "install-opencode.sh: download of $REPO@$REF is not a rolepod-seo tree (no skills/ + .claude-plugin/plugin.json)" >&2; exit 1; }
fi
VERSION="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["version"])' "$SRC/.claude-plugin/plugin.json")"

# ── install: replace each skill dir wholesale, drop ids the previous
#    install had that this release no longer ships, then write the marker ──
mkdir -p "$TARGET/skills"
old_ids="$(marker_ids)"
rm -f "$MARKER"   # a failed copy below leaves no marker; --uninstall then uses the fallback list
ids=""
for d in "$SRC"/skills/*/; do
  id="$(basename "$d")"
  [ -f "$d/SKILL.md" ] || continue
  valid_id "$id" || { echo "install-opencode.sh: skipping skill dir with an unusable name: $id" >&2; continue; }
  rm -rf "$TARGET/skills/$id"
  cp -R "${d%/}" "$TARGET/skills/$id"
  find "$TARGET/skills/$id" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
  find "$TARGET/skills/$id" \( -name '*.pyc' -o -name .DS_Store \) -type f -delete 2>/dev/null || true
  [ -f "$TARGET/skills/$id/SKILL.md" ] || { echo "install-opencode.sh: $TARGET/skills/$id/SKILL.md missing after copy" >&2; exit 1; }
  ids="$ids $id"
done
ids="${ids# }"
[ -n "$ids" ] || { echo "install-opencode.sh: no skills found in $SRC/skills" >&2; exit 1; }
dropped=""
for id in $old_ids; do
  case " $ids " in *" $id "*) ;; *) rm -rf "$TARGET/skills/$id"; dropped="$dropped $id" ;; esac
done
# $ids is a validated, space-separated list — word-splitting is the intent.
python3 - "$MARKER" "$VERSION" $ids <<'PY'
import json, sys
path, version, *ids = sys.argv[1:]
with open(path, "w") as f:
    json.dump({"name": "rolepod-seo", "version": version, "skills": ids,
               "note": "written by scripts/install-opencode.sh; opencode has no plugin manifest for skills"},
              f, indent=2)
    f.write("\n")
PY
echo "  ✓ rolepod-seo $VERSION → $TARGET/skills ($ids)"
[ -z "$dropped" ] || echo "    removed skills this release no longer ships:${dropped}"
echo "    restart opencode (or start it in this project) to load the skills"
