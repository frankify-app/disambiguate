#!/usr/bin/env bash
# Claude Code SessionStart hook: prepend the agent shims to PATH for this
# agent session only. `env` in .claude/settings.json cannot express a PATH
# prepend (values are literal, no $PATH expansion), so we write an export
# to CLAUDE_ENV_FILE, which every Bash tool call in the session sources.
# The user's own shell and dotfiles are never touched.
set -euo pipefail

if [[ -n "${CLAUDE_ENV_FILE:-}" ]]; then
    shim_dir="${CLAUDE_PROJECT_DIR:-$(pwd)}/scripts/agent-shims"
    echo "export PATH=\"${shim_dir}:\$PATH\"" >>"$CLAUDE_ENV_FILE"
fi
