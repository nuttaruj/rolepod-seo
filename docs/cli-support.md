# CLI support — rolepod-seo Phase 1 (skills only)

| CLI | Install | Skills load | Question UI | Fetch | Tier B (rolepod-uiproof) | Sweep delegation | Artifact |
|---|---|---|---|---|---|---|---|
| Claude Code | `claude plugin marketplace add nuttaruj/rolepod-seo` → `claude plugin install rolepod-seo@rolepod-seo` | per project or global | native (AskUserQuestion) | `collect.py` via Bash; WebFetch fallback | when the uiproof plugin is installed (tools deferred, zero cost until used) | `Agent` → scout on the cheap tier | yes |
| Codex CLI | `codex plugin marketplace add nuttaruj/rolepod-seo` → `codex plugin add rolepod-seo@rolepod-seo` | global only (Codex plugins are global) | numbered questions, lettered options, `1a` / `defaults` | `collect.py` via shell | if the uiproof MCP server is configured | `spawn_agent` on the balanced model, never strong for a fetch sweep | no |
| Gemini CLI | `gemini extensions install https://github.com/nuttaruj/rolepod-seo` | auto-discovered from `skills/<name>/SKILL.md` | numbered fallback | `collect.py` via shell | if wired as an MCP server | native subagent when available | no |
| Cursor | team marketplace (enterprise) or copy `skills/` into the workspace | workspace skills | numbered fallback | `collect.py` via shell | if `.cursor/mcp.json` has uiproof | — | no |
| opencode | copy `skills/` into the project | project skills | numbered fallback | `collect.py` via shell | — | — | no |

Constant across CLIs: the collector and the HTML renderer (`python3`,
stdlib only), the markdown report, the JSON sidecar, the self-contained
HTML report, the evidence rules, the effort ceiling (`xhigh`). The Artifact
column is the only Claude-Code-only deliverable; every other CLI opens the
same HTML file in a browser.

Phase 1 ships **no MCP server and no hooks** on purpose:

- Codex plugins are global — every session would list any tool we shipped.
- Codex plugin hooks stay inert until trusted via `/hooks`.
- Claude Code defers tool schemas, but a skill still costs one index line
  per session; a tool would cost more. Skills only keeps the per-session
  price at four lines.

Phase 2 (connectors: Search Console, keyword / SERP, rank tracking) adds an
MCP server in this repo with a small, lazy tool surface — see brief 05.
