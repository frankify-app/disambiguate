#!/usr/bin/env bash
# lint-red.sh — TDD red-commit enforcement (tier 1)
# Usage:
#   lint-red.sh staged                # prek pre-commit: check staged changes + commit msg via $COMMIT_MSG_FILE
#   lint-red.sh commit <commit-ish>   # CI: check a single commit
#   lint-red.sh tree                  # CI merge gate: no red markers in worktree
set -euo pipefail

MARKERS='\.(fails|failing)\(|@pytest\.mark\.xfail\(strict=True\)|//go:build red|#\[ignore = "red"\]'
TEST_PATH='(^|/)(tests?|__tests__|spec)(/|$)|[._](test|spec)\.[a-z]+$|^test_|_test\.(go|py)$'
EMPTY_TREE=4b825dc642cb6eb9a060e54bf8d69288fbee4904

fail() { echo "FAIL: $*" >&2; exit 1; }

check_conventions() {
  # Go/Rust markers require red-tests CI job + name prefixes (invisible-marker prevention)
  local go_files rust_files
  go_files=$(grep -rl '//go:build red' --include='*_test.go' . 2>/dev/null || true)
  rust_files=$(grep -rl '#\[ignore = "red"\]' --include='*.rs' . 2>/dev/null || true)
  [ -z "$go_files$rust_files" ] && return 0

  grep -rqs 'red-tests' .forgejo/workflows .github/workflows .gitlab-ci.yml .woodpecker.yml 2>/dev/null \
    || fail "Go/Rust red markers present but no 'red-tests' CI job — markers invisible without inverse job"

  local f
  for f in $go_files; do
    grep -E '^func Test' "$f" | grep -qvE '^func TestRed' \
      && fail "$f: red-tagged file has test without TestRed prefix — invisible to inverse job"
  done
  for f in $rust_files; do
    awk '/#\[ignore = "red"\]/{p=1;next} p&&/fn /{if($0!~/fn red_/)exit 1; p=0}' "$f" \
      || fail "$f: red-ignored test without red_ prefix — invisible to inverse job"
  done
}

check_changes() {  # $1 = commit subject, $2 = changed files, $3 = diff
  local msg="$1" files="$2" diff="$3"
  if [[ "$msg" =~ ^test\(red\): ]]; then
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      [[ "$f" =~ $TEST_PATH ]] || fail "red commit touches non-test file: $f"
    done <<< "$files"
    grep -E '^\+' <<< "$diff" | grep -qE "$MARKERS" \
      || fail "red commit adds no red marker"
  else
    grep -E '^\+' <<< "$diff" | grep -qE "$MARKERS" \
      && fail "red marker added outside test(red) commit"
  fi
  check_conventions
}

mode="${1:?usage: lint-red.sh staged | commit <ref> | tree}"
case "$mode" in
  tree)
    if grep -rEn "$MARKERS" --exclude-dir={.git,node_modules,vendor,target} .; then
      fail "red markers in tree — behaviors never verified green"
    fi
    check_conventions
    ;;
  commit)
    ref="${2:-HEAD}"
    parent=$(git rev-parse -q --verify "$ref~1" 2>/dev/null || echo "$EMPTY_TREE")
    check_changes "$(git log -1 --format=%s "$ref")" \
                  "$(git diff-tree --no-commit-id --name-only -r "$ref")" \
                  "$(git diff "$parent" "$ref")"
    ;;
  staged)
    msg=$(head -n1 "${COMMIT_MSG_FILE:-.git/COMMIT_EDITMSG}")
    check_changes "$msg" \
                  "$(git diff --cached --name-only --diff-filter=ACMR)" \
                  "$(git diff --cached)"
    ;;
  *) fail "unknown mode: $mode (usage: lint-red.sh staged | commit <ref> | tree)" ;;
esac
echo "lint-red: OK"
