#!/usr/bin/env bash
# Turn PUSH_BLOCKLIST into a TruffleHog custom-detector config — the
# layer-3 audit's denylist bridge (agentic-engineering-template#189).
#
# PUSH_BLOCKLIST is |-separated values, each optionally labeled
# value=pb:name (= and | reserved in values; unlabeled entries fall
# back to their raw field position). The values ARE the secret: they
# go only into the config file named by $1, and everything this
# script prints is value-silent — labels and counts, never a value.
# Trailing newlines and stray pipes are tolerated, matching every
# other consumer of the variable.
#
# Config shape validated against trufflehog 3.97.1:
#   detectors: [{name, keywords: [v], regex: {match: v-escaped}}]
# keywords is TruffleHog's prefilter and must be a literal substring
# of the match, so the raw value serves as its own keyword.
set -euo pipefail

out="${1:?usage: trufflehog-detectors.sh <config-file>}"

list="$(printf %s "${PUSH_BLOCKLIST:-}" | tr -d '\r\n')"
if [ -z "${list//|/}" ]; then
    echo "PUSH_BLOCKLIST is empty — no denylist detectors generated (audit runs with stock rules only)"
    exit 0
fi

printf 'detectors:\n' >"$out"
n=0
count=0
IFS='|'
for entry in $list; do
    n=$((n + 1))
    [ -z "$entry" ] && continue
    value="${entry%%=*}"
    label="${entry#*=}"
    [ "$label" = "$entry" ] && label="entry $n"
    [ -z "$value" ] && continue
    # RE2 has no \Q..\E; escape every metacharacter individually.
    # The $ inside the sed class is a regex anchor, not a variable:
    # shellcheck disable=SC2016
    escaped="$(printf %s "$value" | sed -e 's/[.[\*^$()+?{}|\\]/\\&/g' -e 's/\]/\\]/g')"
    # Single-quoted YAML scalars: only ' is special (doubled below);
    # double quotes would treat the regex backslashes as YAML escapes
    # and trufflehog rejects the whole config. The quote lives in a
    # variable because bash 3.2 (macOS) keeps the backslashes of an
    # escaped-quote replacement string literal.
    q="'"
    yq_value="${value//"$q"/$q$q}"
    yq_escaped="${escaped//"$q"/$q$q}"
    yq_label="${label//"$q"/$q$q}"
    {
        printf "  - name: '%s'\n" "$yq_label"
        printf '    keywords:\n'
        printf "      - '%s'\n" "$yq_value"
        printf '    regex:\n'
        printf "      match: '%s'\n" "$yq_escaped"
    } >>"$out"
    count=$((count + 1))
    echo "detector: $label"
done
echo "$count denylist detector(s) written to $out"
