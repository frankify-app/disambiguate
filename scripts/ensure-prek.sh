#!/usr/bin/env bash
# SessionStart bootstrap: make "prek must pass on every commit" enforceable.
#
# Copier runs `prek install` at generation time, but git hooks do not
# survive `git clone` — a fresh checkout (every remote agent session)
# has no pre-commit hook and nothing blocking lint-dirty commits.
# Best-effort and quiet: a broken bootstrap must never block a session.
set -u

if ! command -v prek >/dev/null 2>&1 && command -v uv >/dev/null 2>&1; then
    uv tool install prek >/dev/null 2>&1 || true
    hash -r 2>/dev/null || true
fi

if command -v prek >/dev/null 2>&1; then
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        prek install --install-hooks >/dev/null 2>&1 \
            || echo "ensure-prek: 'prek install' failed — lint-dirty commits are NOT blocked; run scripts/doctor.sh" >&2
    fi
else
    echo "ensure-prek: prek unavailable (and uv missing to install it) — lint-dirty commits are NOT blocked; run scripts/doctor.sh --install" >&2
fi
