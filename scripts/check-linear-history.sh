#!/usr/bin/env bash
# Linear history (skills#147): a claude/* branch is updated by rebase
# onto the default branch, never by merging anything into it. The
# only legitimate merge commits are the ones the forge makes when it
# merges a PR. Measured 2026-08-16: main merged INTO a working branch
# dragged 45 upstream commits into its rebase range, and the repair
# took four steps.
#
# One script, three prek stages, one mode flag each:
#   --merge   pre-merge-commit: `git merge` is about to commit a merge
#             on the current branch. Refused on claude/*. git leaves
#             the merge staged (MERGE_HEAD) when the hook says no, so
#             the advice starts with the abort.
#   --commit  pre-commit: a conflicted merge is being finished with
#             `git commit`, which the merge stage never sees. Refused
#             on claude/* when MERGE_HEAD exists.
#   --push    pre-push: the backstop for a merge that got past both
#             (--no-verify). The pushed ref's own range — merges
#             reachable from the tip and not from the default branch
#             — must be empty; a merge main already holds is the
#             forge's and passes. Refs come from prek's environment
#             (PRE_COMMIT_LOCAL_BRANCH, PRE_COMMIT_TO_REF); run by
#             hand, HEAD stands in.
# Non-agent branches carry no constraint.
set -euo pipefail

mode="${1:-}"
case "$mode" in
    --merge|--commit|--push) ;;
    *) echo "usage: $0 --merge | --commit | --push" >&2; exit 2 ;;
esac

default="$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null || true)"
if [ -z "$default" ] && git rev-parse --verify --quiet origin/main >/dev/null 2>&1; then
    default=origin/main
fi
: "${default:=origin/main}"

refuse() {
    printf '\n⚠️  **LINEAR HISTORY: A WORKING BRANCH IS REBASED, NEVER MERGED INTO**  ⚠️\n\n' >&2
    printf '%s\n' "$@" >&2
    printf '\n' >&2
    exit 1
}

if [ "$mode" = --push ]; then
    ref="${PRE_COMMIT_LOCAL_BRANCH:-$(git symbolic-ref -q HEAD 2>/dev/null || true)}"
    tip="${PRE_COMMIT_TO_REF:-HEAD}"
    case "$ref" in
        refs/heads/claude/*) branch="${ref#refs/heads/}" ;;
        *) exit 0 ;;
    esac
    # Nothing to judge against: without the default branch on the
    # remote the forge's merges and a session's look alike.
    git rev-parse --verify --quiet "$default" >/dev/null 2>&1 || exit 0
    merges="$(git rev-list --merges "$tip" --not "$default")"
    [ -n "$merges" ] || exit 0
    first="$(printf '%s\n' "$merges" | tail -n 1)"
    count="$(printf '%s\n' "$merges" | grep -c .)"
    refuse \
        "    $branch carries $count merge commit(s) $default does not hold, the first being" \
        "      $(git log -1 --format='%h %s' "$first")" \
        "    A working branch is rebased onto $default, never merged into (skills#147);" \
        "    the only merge commits are the forge's own. The push is refused until" \
        "    the history is linear again:" \
        "" \
        "      git rebase $default"
fi

branch="$(git symbolic-ref -q --short HEAD 2>/dev/null || true)"
case "$branch" in
    claude/*) ;;
    *) exit 0 ;;
esac
if [ "$mode" = --commit ]; then
    git rev-parse -q --verify MERGE_HEAD >/dev/null 2>&1 || exit 0
fi
refuse \
    "    $branch is a working branch, and a merge commit on it is illegal: the only" \
    "    merge commits are the ones the forge makes when it merges a PR (skills#147)." \
    "    The merge is staged but not committed; undo it and take the upstream work" \
    "    by rebase:" \
    "" \
    "      git merge --abort && git rebase $default"
