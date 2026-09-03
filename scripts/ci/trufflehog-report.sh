#!/usr/bin/env bash
# Reduce a TruffleHog JSON findings stream to value-silent ::error
# lines — layer 3's reporter (agentic-engineering-template#189). The
# raw stream carries the matched secret (Raw/RawV2), so only the
# detector name (the denylist label for custom detectors) and the
# location are ever printed. Exits 1 iff findings exist, so the
# workflow run itself is the alert.
set -euo pipefail

findings_file="${1:?usage: trufflehog-report.sh <findings.jsonl>}"

python3 - "$findings_file" <<'PY'
import json
import sys

findings = 0
with open(sys.argv[1]) as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if "DetectorName" not in d:
            continue
        findings += 1
        name = (d.get("ExtraData") or {}).get("name") or d["DetectorName"]
        gh = ((d.get("SourceMetadata") or {}).get("Data") or {}).get("Github") or {}
        where = gh.get("link") or " ".join(
            str(gh.get(k)) for k in ("repository", "file", "line") if gh.get(k)
        ) or "unknown location"
        print(f"::error::{name} found at {where} — scrub the surface; the value is never printed here")
print(f"{findings} finding(s)")
sys.exit(1 if findings else 0)
PY
