#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:?usage: scripts/build_claude_bundle.sh VERSION}"
STAGING="$(mktemp -d)"
trap 'rm -rf "${STAGING}"' EXIT

# Pre-fetch the wheel and any future transitive deps from the local dist/
# directory so the bundle stays installable without PyPI access.
python3.12 -m pip download \
  "disambiguate==${VERSION}" \
  --dest "${STAGING}" \
  --platform manylinux2014_x86_64 \
  --python-version 3.12 \
  --only-binary=:all: \
  --no-index \
  --find-links dist/

BUNDLE="dist/disambiguate-v${VERSION}-claude-bundle.zip"
rm -f "${BUNDLE}"
(cd "${STAGING}" && zip -r "${OLDPWD}/${BUNDLE}" .)
echo "${BUNDLE}"
