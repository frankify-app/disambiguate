#!/usr/bin/env bash
# SessionStart bootstrap: make "prek must pass on every commit" enforceable.
#
# Copier runs `prek install` at generation time, but git hooks do not
# survive `git clone` — a fresh checkout (every remote agent session)
# has no pre-commit hook and nothing blocking lint-dirty commits.
# Best-effort and quiet when it installs somewhere: a broken bootstrap
# must never block a session. Installing NOWHERE warns, because that
# silent branch was the measured defect (#139): in a multi-repo session
# the project dir is the parent holding every clone and is itself no
# repository, so the old single-repo guard was false and the script
# exited 0 having installed nothing — in any clone, saying nothing.
set -u

if ! command -v prek >/dev/null 2>&1 && command -v uv >/dev/null 2>&1; then
    uv tool install prek >/dev/null 2>&1 || true
    hash -r 2>/dev/null || true
fi

if ! command -v prek >/dev/null 2>&1; then
    echo "ensure-prek: prek unavailable (and uv missing to install it) — lint-dirty commits are NOT blocked; run scripts/doctor.sh --install" >&2
    exit 0
fi

install_into() {
    # $1: a work tree. Failure warns and never blocks the session.
    (cd "$1" && prek install --install-hooks >/dev/null 2>&1) \
        || echo "ensure-prek: 'prek install' failed in $1 — lint-dirty commits are NOT blocked there; run scripts/doctor.sh" >&2
}

installed=0
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    # Single-repo session: the project dir is the clone, as before.
    install_into "$PWD"
    installed=1
else
    # Multi-repo session: install into every clone the session holds.
    for dir in */; do
        [ -e "$dir/.git" ] || continue
        install_into "$PWD/${dir%/}"
        installed=$((installed + 1))
    done
fi

if [ "$installed" -eq 0 ]; then
    echo "ensure-prek: no repository found at or under $PWD — no pre-commit hook installed anywhere; lint-dirty commits are NOT blocked" >&2
fi
