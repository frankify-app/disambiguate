#!/usr/bin/env bash
# Reduce GitHub's secret-scanning alert list to value-silent ::error
# lines — layer 4's reporter (agentic-engineering-template#189, #104).
# Each alert carries the detected secret in its `secret` field, so
# only the secret type, the alert number and its link are printed.
# The input is what `gh api --paginate` writes for a list endpoint:
# one JSON array per page, back-to-back. Exits 1 iff any alert is
# open, so the workflow run itself is the alert.
set -euo pipefail

alerts_file="${1:?usage: secret-scanning-report.sh <alerts.json>}"

python3 - "$alerts_file" <<'PY'
import json
import sys

text = open(sys.argv[1]).read()
decoder = json.JSONDecoder()
pos = 0
count = 0
while True:
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos >= len(text):
        break
    page, pos = decoder.raw_decode(text, pos)
    if not isinstance(page, list):
        page = [page]
    for a in page:
        if not isinstance(a, dict) or "number" not in a:
            continue
        count += 1
        kind = a.get("secret_type_display_name") or a.get("secret_type") or "secret"
        where = a.get("html_url") or f"alert #{a['number']}"
        validity = a.get("validity") or "unknown"
        print(
            f"::error::{kind} alert #{a['number']} open at {where} "
            f"(validity: {validity}) — resolve it on the forge; the value is never printed here"
        )
print(f"{count} open alert(s)")
sys.exit(1 if count else 0)
PY
