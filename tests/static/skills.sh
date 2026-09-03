#!/usr/bin/env bash
# Skill contract: frontmatter, line cap, supporting-file cap, pointers resolve,
# effort ceiling, clean-room guard.
set -euo pipefail
cd "$(dirname "$0")/../.."
fail=0
n=0
for dir in skills/*/; do
  dir="${dir%/}"; name="$(basename "$dir")"; f="$dir/SKILL.md"; n=$((n+1))
  [ -f "$f" ] || { echo "  ✗ $name: SKILL.md missing"; fail=1; continue; }
  [ "$(head -1 "$f")" = "---" ] || { echo "  ✗ $name: no frontmatter"; fail=1; }
  fm="$(awk 'NR==1{next} /^---$/{exit} {print}' "$f")"
  grep -q "^name: $name\$" <<<"$fm" || { echo "  ✗ $name: frontmatter name != directory"; fail=1; }
  grep -Eq '^description: [^[:space:]]' <<<"$fm" || { echo "  ✗ $name: description missing"; fail=1; }
  lines=$(wc -l <"$f" | tr -d ' ')
  [ "$lines" -le 240 ] || { echo "  ✗ $name: SKILL.md is $lines lines (> 240)"; fail=1; }
  find "$dir" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
  count=$(find "$dir" -type f ! -name SKILL.md ! -name .DS_Store ! -name '*.pyc' | wc -l | tr -d ' ')
  [ "$count" -le 5 ] || { echo "  ✗ $name: $count supporting files (> 5)"; fail=1; }
  for p in $(grep -oE '(^|[^A-Za-z0-9/-])(references|examples|templates|scripts)/[A-Za-z0-9_.-]+' "$f" | sed -E 's/^[^a-z]*//' | sort -u); do
    [ -e "$dir/$p" ] || { echo "  ✗ $name: pointer $p does not exist"; fail=1; }
  done
  for p in $(grep -oE '\bseo-[a-z-]+/(references|examples|templates|scripts)/[A-Za-z0-9_.-]+' "$f" | sort -u); do
    [ -e "skills/$p" ] || echo "  ! $name: cross-skill pointer $p not shipped yet"
  done
  if grep -rEiq '(effort|reasoning)[^a-z\n]{0,12}\b(max|ultra)\b' "$dir"; then
    echo "  ✗ $name: effort max/ultra (ceiling is xhigh)"; fail=1
  fi
  for py in $(find "$dir" -name '*.py'); do
    python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$py" || { echo "  ✗ $py: syntax"; fail=1; }
  done
done
[ "$n" -ge 1 ] || { echo "  ✗ no skills found"; fail=1; }
# clean-room guard — distinctive sentences from the reference repo must not appear
banned=0
while IFS= read -r phrase; do
  [ -z "$phrase" ] && continue
  case "$phrase" in \#*) continue;; esac
  if grep -rFiq -- "$phrase" skills README.md docs 2>/dev/null; then
    echo "  ✗ banned phrase present: \"$phrase\""; fail=1; banned=$((banned+1))
  fi
done < tests/static/banned-phrases.txt
[ $fail -eq 0 ] && echo "  ✓ $n skill(s): frontmatter, ≤240 lines, ≤5 files, pointers resolve, effort ≤ xhigh, clean-room guard"
exit $fail
