#!/usr/bin/env python3
"""Cap on source file length, run over the files a commit touches (#239).

Nothing else in the stamped lint config reads file length, so a file
grows until a reader notices. This fails on any source file over the
limit, naming the path and the count, and exempts only what the repo's
own `.file-length-allowlist` names — each entry carrying the ticket
that will bring the file back under, so the list shrinks rather than
becoming permanent.

Three things make an entry leave the list, all of them checked here: a
ticket is missing, the file came back under the limit, or the file is
gone. The list is the repo's own file, seeded once and never stamped
again.

Stdlib only, and no repo state beyond the paths it is handed: prek runs
this on every commit, on whatever `python3` the contributor has.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

ALLOWLIST = ".file-length-allowlist"
DEFAULT_MAX_LINES = 800

# `#123` or `owner/repo#123`, the same reference shape the ticket gate
# reads on a pull request body.
TICKET = re.compile(r"(?:[\w.-]+/[\w.-]+)?#\d+")


def parse_allowlist(text: str) -> tuple[dict[str, str], list[str]]:
    """`{path: ticket}` from the allowlist, and a problem per bad entry.

    One entry per line: the path, then the ticket that will close it,
    after a `#`. A line carrying no ticket buys a permanent exemption,
    which is the one thing the list must not be able to hold, so it is
    reported rather than parsed.
    """
    entries: dict[str, str] = {}
    problems: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        path, _, comment = stripped.partition("#")
        path = path.strip()
        ticket = TICKET.search(f"#{comment}")
        if not path or not ticket:
            problems.append(
                f"{ALLOWLIST}:{number}: {stripped!r} names no ticket — an entry "
                "reads `<path>  # owner/repo#123`, so the exemption ends when "
                "the ticket does"
            )
            continue
        entries[path] = ticket.group(0)
    return entries, problems


def review(
    counts: dict[str, int],
    limit: int,
    allowlist: dict[str, str],
    missing: set[str],
) -> list[str]:
    """Every problem this run found, as lines a reader can act on.

    `counts` holds only the files this run was handed, which is why an
    untouched overrun elsewhere is nobody's commit to block: the hook
    judges what the commit touched. `missing` names allowlisted paths
    that are no longer on disk.
    """
    problems = []
    for path in sorted(counts):
        lines = counts[path]
        if lines <= limit or path in allowlist:
            continue
        problems.append(
            f"{path}: {lines} lines, over the {limit}-line limit — split it, "
            f"or add `{path}  # <ticket>` to {ALLOWLIST}"
        )
    for path, ticket in sorted(allowlist.items()):
        if path in missing:
            problems.append(
                f"{ALLOWLIST}: {path} no longer exists — remove its line "
                f"(ticket {ticket})"
            )
        elif path in counts and counts[path] <= limit:
            problems.append(
                f"{ALLOWLIST}: {path} is {counts[path]} lines, at or under the "
                f"{limit}-line limit — remove its line (ticket {ticket})"
            )
    return problems


def count_lines(path: str) -> int | None:
    """Lines in a text file, or None for anything that is not one."""
    try:
        with open(path, encoding="utf-8") as handle:
            return sum(1 for _ in handle)
    except (OSError, UnicodeDecodeError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max",
        dest="limit",
        type=int,
        default=DEFAULT_MAX_LINES,
        help=f"lines a source file may have (default {DEFAULT_MAX_LINES})",
    )
    parser.add_argument(
        "--allowlist",
        default=ALLOWLIST,
        help=f"the repo's exemption list (default {ALLOWLIST})",
    )
    parser.add_argument("paths", nargs="*", help="the files prek hands this hook")
    args = parser.parse_args(argv)

    allowlist: dict[str, str] = {}
    problems: list[str] = []
    if os.path.exists(args.allowlist):
        with open(args.allowlist, encoding="utf-8") as handle:
            allowlist, problems = parse_allowlist(handle.read())

    counts = {}
    for path in args.paths:
        lines = count_lines(path)
        if lines is not None:
            counts[path] = lines
    missing = {path for path in allowlist if not os.path.exists(path)}

    problems += review(counts, args.limit, allowlist, missing)
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
