# rolepod-seo release gate. Skills-only plugin: bash + python3, no Node.
#
#   make test-static   — fast: manifests parse + version lockstep + skill contract + parity + clean-room guard
#   make test-fixture  — serves tests/fixtures/site-a and runs the Tier A collector against it
#   make test          — test-static + test-fixture (release gate)
#   make render        — copy skills/ + manifests into plugins/rolepod-seo/ (the shipped tree)
#   make version-bump VERSION=0.x.y — bump every manifest, then re-render
#   make serve-fixture — serve the fixture site on :8765 for a manual audit run

.PHONY: help test test-static test-fixture render version-bump serve-fixture

help:
	@echo "rolepod-seo:"
	@echo "  make test-static                  — manifests + skill contract + parity + clean-room guard"
	@echo "  make test-fixture                 — collector run against tests/fixtures/site-a"
	@echo "  make test                         — release gate (static + fixture)"
	@echo "  make render                       — re-copy skills/ + manifests into plugins/rolepod-seo/"
	@echo "  make version-bump VERSION=0.x.y   — bump all manifests + render"
	@echo "  make serve-fixture                — python http.server on :8765 for a manual run"

test: test-static test-fixture

test-static:
	@echo "── test-static ──"
	@bash tests/static/manifests.sh
	@bash tests/static/skills.sh
	@bash tests/static/parity.sh
	@bash tests/static/report-schema.sh
	@bash tests/static/schema-minimums.sh
	@bash tests/static/render-report.sh
	@echo "  ✓ test-static passed"

test-fixture:
	@echo "── test-fixture ──"
	@bash tests/fixture/collect.sh
	@echo "  ✓ test-fixture passed"

render:
	@mkdir -p plugins/rolepod-seo/.claude-plugin plugins/rolepod-seo/.codex-plugin
	@rsync -a --delete --exclude .DS_Store --exclude __pycache__ skills/ plugins/rolepod-seo/skills/
	@cp .claude-plugin/plugin.json plugins/rolepod-seo/.claude-plugin/plugin.json
	@cp .codex-plugin/plugin.json plugins/rolepod-seo/.codex-plugin/plugin.json
	@echo "  ✓ rendered plugins/rolepod-seo/"

version-bump:
	@test -n "$(VERSION)" || { echo "usage: make version-bump VERSION=0.x.y"; exit 1; }
	@bash scripts/bump-version.sh "$(VERSION)"

serve-fixture:
	@echo "serving tests/fixtures/site-a on http://127.0.0.1:8765 (Ctrl-C to stop)"
	@python3 -m http.server 8765 --bind 127.0.0.1 --directory tests/fixtures/site-a
