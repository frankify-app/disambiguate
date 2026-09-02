#!/usr/bin/env bash
# Branch discipline (skills#147): a claude/* branch must match the
# vendored branch_pattern, or the ticket gate's branch-derived half
# silently never fires — a branch it cannot parse skips the check
# instead of failing it. Non-agent prefixes carry no constraint, and
# a repo without the keywords file (Forgejo forge) has no pattern to
# hold the branch to.
set -euo pipefail

branch="$(git symbolic-ref --quiet --short HEAD || true)"
case "$branch" in
    claude/*) ;;
    *) exit 0 ;;
esac

[ -f .github/reference-keywords.json ] || exit 0

python3 - "$branch" <<'PY'
import json
import re
import sys

branch = sys.argv[1]
pattern = json.load(open(".github/reference-keywords.json"))["branch_pattern"]
if re.match(pattern, branch):
    sys.exit(0)
sys.exit(
    f"branch {branch!r} does not match the agent branch shape "
    f"(branch_pattern {pattern!r}) — name it "
    "claude/<code><ticket>[-<code><ticket>...]-<desc>, e.g. "
    "claude/sk162-session-probe; the ticket gate binds each token's "
    "trailing number to a reference in the PR body"
)
PY
