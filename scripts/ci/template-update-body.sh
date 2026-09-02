#!/usr/bin/env bash
# Compose the body of a template-update PR (#218).
#
# Usage: template-update-body.sh <release-section> [<existing-body>]
#
# A fresh PR gets the release section alone. Joining an existing PR —
# one a human opened and referenced a ticket from — must not throw that
# body away: the ticket gate reads the body, and a rewrite turns a green
# PR red. So the existing text is kept verbatim above the release
# section, and only a release section this script wrote before is
# replaced, so a PR that survives five releases carries one set of notes
# rather than five.
set -euo pipefail

MARKER='<!-- agentic-template-update -->'

release_file="${1:?release section file required}"
existing_file="${2:-}"

if [ -n "$existing_file" ] && [ -s "$existing_file" ]; then
  # Everything above the marker is the PR's own body. Without a marker
  # the whole thing is (the first join on a hand-authored PR).
  kept="$(awk -v marker="$MARKER" '
    index($0, marker) { exit }
    { print }
  ' "$existing_file")"
  # Drop trailing blank lines so the seam is one blank line, always.
  kept="$(printf '%s\n' "$kept" | sed -e :a -e '/^\s*$/{$d;N;ba' -e '}')"
  if [ -n "$kept" ]; then
    printf '%s\n\n' "$kept"
  fi
fi

printf '%s\n\n' "$MARKER"
cat "$release_file"
