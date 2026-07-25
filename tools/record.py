#!/usr/bin/env python3
"""Decision recorder — writer-side tooling for a decision-memory repo.

This docstring doubles as the CLI help text and is the AUTHORITATIVE
description of the recorder's behavior — there is no separate spec
file (design history: agentic-engineering-template issue #37 and the
backfilled decision records). The contract this tool must satisfy
(record schema, commit types, PR flow) lives with the data, in the
decision-memory repo's docs/conventions.md and CI guards.

Verbs:
  open     make the store repo available — clone it into an ephemeral
           temp dir, or reuse an already-attached checkout
           (--use <path>, matched against DECISION_MEMORY_URL by
           owner/repo) where cloning is impossible (e.g. managed
           environments); capture the preference-set SHA, create the
           session branch, run the stateless closed-unmerged-PR sweep
  record   mint + validate + write one decision record per input
           draft (stdin JSON object/array, or --from drafts.json),
           one commit per record; batch-local slug references
           (supersedes_slug, drill_down_of_slug, related_slugs)
           resolve to the minted IDs
  check    validate the entire decisions/ corpus + dangling refs +
           preferences.md token budget
  submit   compute two-stream hit rates (refined and near-tie
           bucketed separately), auto-bump pref-confirm counters for
           clean preference-driven hits, push, open the PR (or emit
           the managed-environment handoff)
  propose  write a preference-rule proposal file with its commit

Configuration: DECISION_MEMORY_URL (full git URL of the data repo;
never commit it anywhere public). Verbs after `open` find the clone
via DECISION_MEMORY_DIR or --dir.

Stdlib only. The file is split into a pure CONTRACT CORE (the dojo
lift-target) and an IO SHELL; keep the seam strict.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ========================== contract core ==========================
# Pure functions, no IO — the functions a future dojo package lifts
# verbatim. Validation is deliberately NOT defined here:
# DECISION: the validator is imported from the data-repo clone's
# vendored copy (single copier-vendored source shared with CI), so
# writer-side and CI validation cannot drift.

# Mint-side mirror of the envelope/ID grammar. The vendored
# decision_validator in the store checkout stays authoritative —
# minted records are re-validated against it; these constants only
# make minting fail fast with better messages.
SCHEMA_VERSION = 1
RECORD_TYPE = "decision"
MAX_SLUG_LENGTH = 40
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Replay-ready order: envelope, then input side (pre-ruling), then
# output side (post-ruling), then links. Unknown fields keep their
# draft order after these.
FIELD_ORDER = (
    "v",
    "type",
    "id",
    "date",
    "project",
    "question",
    "context",
    "options",
    "prediction_stream",
    "preference_set",
    "artifact_ref",
    "session",
    "chosen_slot",
    "chosen",
    "operative_reason",
    "correction",
    "rejections",
    "outcome",
    "drill_down_of",
    "closure_of",
    "related",
    "supersedes",
    "notes",
)


def mint_id(slug: str, now: dt.datetime) -> str:
    """Mint a record ID: <UTC timestamp>Z-<slug>."""
    if not SLUG_RE.match(slug):
        raise ValueError(f"slug {slug!r} must be lowercase kebab-case ([a-z0-9-])")
    if len(slug) > MAX_SLUG_LENGTH:
        raise ValueError(f"slug {slug!r} is {len(slug)} chars (max {MAX_SLUG_LENGTH})")
    timestamp = now.astimezone(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{slug}"


def mint_envelope(slug: str, now: dt.datetime) -> dict:
    """Mint the universal envelope: v, type, id."""
    return {
        "v": SCHEMA_VERSION,
        "type": RECORD_TYPE,
        "id": mint_id(slug, now),
    }


def draft_to_record(
    draft: dict,
    now: dt.datetime,
    session: str | None = None,
    preference_commit: str | None = None,
) -> dict:
    """Turn a draft record (schema minus tool-minted fields, plus
    ``slug``) into a full record.

    Draft-supplied values always win over minted defaults; unknown
    fields are preserved. Raises ValueError when ``slug`` is missing
    or malformed.
    """
    payload = dict(draft)
    slug = payload.pop("slug", None)
    if not isinstance(slug, str) or not slug:
        raise ValueError("draft is missing the writer-chosen 'slug' field")

    merged = mint_envelope(slug, now)
    merged["date"] = now.astimezone(dt.UTC).strftime("%Y-%m-%d")
    merged["session"] = payload.pop("session", None) or session
    preference_set = payload.pop("preference_set", None)
    if preference_set is None and preference_commit:
        preference_set = {"commit": preference_commit}
    if preference_set is not None:
        merged["preference_set"] = preference_set
    merged.update(payload)

    record = {key: merged[key] for key in FIELD_ORDER if key in merged}
    for key, value in merged.items():
        if key not in record:
            record[key] = value
    return record


def serialize_record(record: dict) -> str:
    """Serialize a record for its immutable decisions/<id>.json file."""
    return json.dumps(record, ensure_ascii=False, indent=2) + "\n"


def resolve_batch_refs(drafts: list, now: dt.datetime) -> list:
    """Resolve batch-local slug references to minted IDs.

    Drafts extracted from one conversation cannot know each other's
    final IDs, so cross-draft links name their target by slug:
    ``supersedes_slug`` and ``drill_down_of_slug`` (single),
    ``related_slugs`` (list, appended to any repo-ID ``related``
    entries). This maps every reference to the ID the batch will mint
    (order-independent). Raises ValueError on unknown slugs or when a
    draft carries both a slug reference and its resolved field.
    """
    minted = {}
    for d in drafts:
        slug = d.get("slug")
        if isinstance(slug, str) and SLUG_RE.match(slug):
            minted[slug] = mint_id(slug, now)

    def resolve(draft_slug, ref):
        if ref not in minted:
            raise ValueError(
                f"draft {draft_slug!r}: batch reference {ref!r} matches "
                "no slug in this batch"
            )
        return minted[ref]

    resolved = []
    for d in drafts:
        d = dict(d)
        for slug_field, target in (
            ("supersedes_slug", "supersedes"),
            ("drill_down_of_slug", "drill_down_of"),
        ):
            ref = d.pop(slug_field, None)
            if ref is not None:
                if d.get(target):
                    raise ValueError(
                        f"draft {d.get('slug')!r}: both {target} and "
                        f"{slug_field} given — use one"
                    )
                d[target] = resolve(d.get("slug"), ref)
        refs = d.pop("related_slugs", None)
        if refs is not None:
            if not isinstance(refs, list):
                raise ValueError(
                    f"draft {d.get('slug')!r}: related_slugs must be a list"
                )
            existing = d.get("related") or []
            d["related"] = existing + [resolve(d.get("slug"), r) for r in refs]
        resolved.append(d)
    return resolved


# ============================ IO shell =============================
# CLI, clone/branch/commit mechanics, PR calls. The PR call is the one
# forge-specific piece: a hosting supersession (or a managed
# environment without gh) swaps/skips this function, never the core.

STATE_FILE = ".recorder-session.json"
VALIDATOR_RELPATH = Path(".github") / "guards" / "decision_validator.py"
GITHUB_URL_RE = re.compile(
    r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"
)


def repo_url_tail(url: str) -> str:
    """Normalize a git URL to its trailing owner/repo pair (lowercase).

    Managed environments rewrite remotes through local proxies, so two
    URLs for the same repo rarely match textually — the owner/repo
    tail is the stable identity across https/ssh/proxy forms.
    """
    path = url.rstrip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    parts = [p for p in path.replace(":", "/").split("/") if p]
    return "/".join(parts[-2:]).lower()


def fail(message: str) -> SystemExit:
    return SystemExit(f"record.py: error: {message}")


def run_git(repo_dir: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_dir), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise fail(f"git {' '.join(args)} failed in {repo_dir}:\n{result.stderr}")
    return result.stdout


def resolve_repo_dir(args: argparse.Namespace) -> Path:
    raw = args.dir or os.environ.get("DECISION_MEMORY_DIR")
    if not raw:
        raise fail(
            "no clone found — run `record.py open` first, then pass --dir "
            "or export DECISION_MEMORY_DIR as it prints"
        )
    repo_dir = Path(raw)
    if not (repo_dir / ".git").exists():
        raise fail(f"{repo_dir} is not a git clone")
    return repo_dir


def load_state(repo_dir: Path) -> dict:
    state_path = repo_dir / STATE_FILE
    if not state_path.exists():
        raise fail(
            f"{state_path} missing — this clone was not created by `record.py open`"
        )
    return json.loads(state_path.read_text(encoding="utf-8"))


def load_validator(repo_dir: Path):
    """Import the copier-vendored validator from the data-repo clone."""
    path = repo_dir / VALIDATOR_RELPATH
    if not path.exists():
        raise fail(
            f"vendored validator missing at {path} — the data repo must "
            "vendor the guard subtemplate (copier update from the "
            "agentic-engineering-template guard subtemplate)"
        )
    spec = importlib.util.spec_from_file_location("decision_validator", path)
    if spec is None or spec.loader is None:
        raise fail(f"cannot import validator from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_corpus(repo_dir: Path) -> dict[str, dict]:
    records: dict[str, dict] = {}
    decisions_dir = repo_dir / "decisions"
    if decisions_dir.is_dir():
        for path in sorted(decisions_dir.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                records[record["id"]] = record
    return records


def read_drafts(args: argparse.Namespace) -> list[dict]:
    if getattr(args, "from_file", None):
        text = Path(args.from_file).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise fail(f"input is not valid JSON: {exc}")
    drafts = data if isinstance(data, list) else [data]
    if not all(isinstance(d, dict) for d in drafts):
        raise fail("input must be a JSON object or an array of objects")
    return drafts


def github_slug(url: str) -> str | None:
    match = GITHUB_URL_RE.search(url)
    return f"{match['owner']}/{match['repo']}" if match else None


def list_closed_unmerged_prs(url: str) -> list[int] | None:
    """Best-effort PR listing via gh. None = unavailable (handoff)."""
    slug = github_slug(url)
    if slug is None or shutil.which("gh") is None:
        return None
    result = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            slug,
            "--state",
            "closed",
            "--json",
            "number,mergedAt",
            "--limit",
            "500",
        ],
        capture_output=True,
        text=True,
    )
    # DECISION: any gh failure falls through to the handoff path —
    # managed environments sabotage gh, so failure is an expected mode,
    # not an error.
    if result.returncode != 0:
        return None
    try:
        prs = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return [
        pr["number"] for pr in prs if isinstance(pr, dict) and not pr.get("mergedAt")
    ]


def covered_closures(records: dict[str, dict]) -> set[int]:
    return {
        record["closure_of"]
        for record in records.values()
        if isinstance(record.get("closure_of"), int)
    }


def _attach_checkout(path_arg: str, url: str) -> Path:
    """Validate an already-available checkout of the store repo."""
    repo_dir = Path(path_arg).resolve()
    if not (repo_dir / ".git").exists():
        raise fail(f"--use {repo_dir}: not a git checkout")
    origin = run_git(repo_dir, "config", "--get", "remote.origin.url").strip()
    if repo_url_tail(origin) != repo_url_tail(url):
        raise fail(
            f"--use {repo_dir}: origin {origin!r} is not the store repo "
            f"(DECISION_MEMORY_URL points at {repo_url_tail(url)!r})"
        )
    if run_git(repo_dir, "status", "--porcelain").strip():
        raise fail(
            f"--use {repo_dir}: worktree is dirty — commit or stash "
            "before opening a recording session in it"
        )
    return repo_dir


def cmd_open(args: argparse.Namespace) -> int:
    url = os.environ.get("DECISION_MEMORY_URL")
    if not url:
        raise fail(
            "DECISION_MEMORY_URL is unset — export the full git URL of "
            "your decision-memory repo (never commit it anywhere public)"
        )
    now = dt.datetime.now(dt.UTC)
    if args.use:
        repo_dir = _attach_checkout(args.use, url)
        print(f"Reusing attached checkout: {repo_dir}")
    else:
        repo_dir = Path(tempfile.mkdtemp(prefix="decision-memory-"))
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, str(repo_dir)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise fail(
                f"clone failed:\n{result.stderr}\n"
                "If the store repo is already available in this session "
                "(e.g. attached in a managed environment where outbound "
                "cloning is blocked), re-run: open --use <path-to-checkout>"
            )

    base_commit = run_git(repo_dir, "rev-parse", "HEAD").strip()
    branch = "session/" + now.strftime("%Y%m%dT%H%M%SZ")
    run_git(repo_dir, "checkout", "-b", branch)

    session = args.session or os.environ.get("CLAUDE_SESSION_ID")
    # DECISION: session state lives inside the ephemeral clone
    # (untracked file, excluded from git status) — nothing persists
    # outside the temp dir, keeping sessions stateless across machines.
    state = {
        "branch": branch,
        "base_commit": base_commit,
        "session": session,
        "opened_at": now.isoformat(),
    }
    (repo_dir / STATE_FILE).write_text(
        json.dumps(state, indent=2) + "\n", encoding="utf-8"
    )
    exclude = repo_dir / ".git" / "info" / "exclude"
    with open(exclude, "a", encoding="utf-8") as handle:
        handle.write(f"{STATE_FILE}\n")

    records = load_corpus(repo_dir)
    covered = covered_closures(records)
    closed_prs = list_closed_unmerged_prs(url)

    print(f"Store checkout: {repo_dir}")
    print(f"Session branch: {branch}")
    print(f"preference_set.commit for this session: {base_commit}")
    print()
    if closed_prs is None:
        print(
            "Unmerged-PR sweep: could not list closed PRs here (no usable "
            "gh). Handoff: list this repo's closed-UNMERGED PRs with your "
            "environment's tooling and record one decision per PR number "
            f"not in the covered set {sorted(covered)} (set closure_of)."
        )
    else:
        pending = sorted(set(closed_prs) - covered)
        if pending:
            print(
                f"Unmerged-PR sweep: PR(s) {pending} were closed without "
                "merge and have no closure record yet. Record one decision "
                "each ('why was PR #N rejected'), with closure_of set and "
                "the correction flag where applicable."
            )
        else:
            print("Unmerged-PR sweep: all closures covered.")
    print()
    print(
        "Reminder: inject preferences.md (and ONLY preferences.md) into "
        "the session context now, if not already injected."
    )
    print(f"export DECISION_MEMORY_DIR={repo_dir}")
    return 0


def commit_record(repo_dir: Path, record: dict) -> None:
    record_id = record["id"]
    path = repo_dir / "decisions" / f"{record_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise fail(f"{path} already exists — records are immutable")
    path.write_text(serialize_record(record), encoding="utf-8")
    slug = record_id.split("Z-", 1)[1]
    chosen = " ".join(str(record.get("chosen", "")).split())
    if len(chosen) > 100:
        chosen = chosen[:99] + "…"
    # Subject grammar authority: the store's docs/conventions.md
    # (§ Commit types); the vendored guard lints what this composes.
    subject = f"decision({record['project']}): {slug} — {chosen}"
    run_git(repo_dir, "add", str(path))
    run_git(repo_dir, "commit", "-m", subject)
    print(f"Recorded {record_id} ({subject})")


def cmd_record(args: argparse.Namespace) -> int:
    repo_dir = resolve_repo_dir(args)
    state = load_state(repo_dir)
    validator = load_validator(repo_dir)
    now = dt.datetime.now(dt.UTC)

    drafts = read_drafts(args)
    try:
        drafts = resolve_batch_refs(drafts, now)
    except ValueError as exc:
        raise fail(str(exc))
    records = []
    errors: list[str] = []
    for index, draft in enumerate(drafts):
        try:
            record = draft_to_record(
                draft,
                now,
                session=state.get("session"),
                preference_commit=state.get("base_commit"),
            )
        except ValueError as exc:
            errors.append(f"draft[{index}]: {exc}")
            continue
        for error in validator.validate_record(record, filename_stem=record["id"]):
            errors.append(f"draft[{index}] ({record['id']}): {error}")
        records.append(record)

    if errors:
        for error in errors:
            print(f"INVALID: {error}", file=sys.stderr)
        print(
            f"{len(errors)} validation error(s) — nothing written.",
            file=sys.stderr,
        )
        return 1

    for record in records:
        commit_record(repo_dir, record)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    repo_dir = resolve_repo_dir(args)
    validator = load_validator(repo_dir)

    errors: list[str] = []
    decisions_dir = repo_dir / "decisions"
    records: dict[str, dict] = {}
    if decisions_dir.is_dir():
        for path in sorted(decisions_dir.iterdir()):
            if path.name.startswith("."):
                continue
            if path.suffix != ".json":
                errors.append(f"{path.name}: non-JSON file in decisions/")
                continue
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{path.name}: invalid JSON: {exc}")
                continue
            errors.extend(
                f"{path.name}: {error}"
                for error in validator.validate_record(record, filename_stem=path.stem)
            )
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                records[record["id"]] = record
    errors.extend(validator.validate_corpus(records))

    preferences = repo_dir / "preferences.md"
    if preferences.exists():
        errors.extend(
            validator.check_preferences_budget(preferences.read_text(encoding="utf-8"))
        )

    for error in errors:
        print(f"CHECK FAIL: {error}", file=sys.stderr)
    if not errors:
        print(f"check: {len(records)} record(s) valid, budget OK.")
    return 1 if errors else 0


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def bump_preference_counter(
    preferences_text: str, rule: str, today: str, counter_re: re.Pattern
) -> tuple[str, int] | None:
    """Bump the confirmation counter of the bullet matching ``rule``.

    ``counter_re`` is the vendored validator's COUNTER_RE — the single
    source of the counter-line grammar, shared with the CI guard.
    Returns (new_text, new_count), or None when no bullet matches.
    Handles wrapped bullets: an entry runs from its `- ` line to the
    next bullet/heading/blank line; the counter sits on its last line.
    """
    lines = preferences_text.splitlines(keepends=True)
    entries: list[tuple[int, int]] = []
    start = None
    for i, line in enumerate(lines):
        if line.startswith("- "):
            if start is not None:
                entries.append((start, i))
            start = i
        elif start is not None and (not line.strip() or line.startswith("#")):
            entries.append((start, i))
            start = None
    if start is not None:
        entries.append((start, len(lines)))

    wanted = _normalize(rule)
    for begin, end in entries:
        entry_text = _normalize("".join(lines[begin:end]))
        if wanted not in entry_text:
            continue
        for i in range(end - 1, begin - 1, -1):
            match = counter_re.search(lines[i])
            if match:
                count = int(match.group(1)) + 1
                lines[i] = counter_re.sub(
                    f"[confirmed: {count}, last: {today}]", lines[i]
                )
                return "".join(lines), count
    return None


def session_hit_rates(records: list[dict]) -> dict[str, dict[str, int]]:
    streams: dict[str, dict[str, int]] = {
        "preference-driven": {"hit": 0, "miss": 0, "near-tie": 0, "refined": 0},
        "cold": {"hit": 0, "miss": 0, "near-tie": 0, "refined": 0},
    }
    for record in records:
        stream = record.get("prediction_stream")
        outcome = record.get("outcome")
        if stream in streams and outcome in streams[stream]:
            streams[stream][outcome] += 1
    return streams


def prediction_rules(record: dict) -> list[str]:
    for option in record.get("options", []):
        if isinstance(option, dict) and option.get("role") in (
            "prediction",
            "prediction+recommendation",
        ):
            rules = option.get("rules_cited")
            return [r for r in rules if isinstance(r, str)] if rules else []
    return []


def build_pr_body(records: list[dict], streams: dict[str, dict[str, int]]) -> str:
    def rate(stream: str) -> str:
        counts = streams[stream]
        scored = counts["hit"] + counts["miss"]
        shown = f"{counts['hit']}/{scored} hits" if scored else "no scored"
        extras = [
            f"{counts[bucket]} {bucket}"
            for bucket in ("refined", "near-tie")
            if counts[bucket]
        ]
        if extras:
            shown += f" ({', '.join(extras)})"
        return shown

    lines = [
        f"Decision session PR: {len(records)} record(s).",
        "",
        "Prediction hit rates (two streams):",
        f"- preference-driven: {rate('preference-driven')}",
        f"- cold (control): {rate('cold')}",
    ]
    supersedes = [
        (record["id"], record["supersedes"])
        for record in records
        if record.get("supersedes")
    ]
    if supersedes:
        lines += ["", "Supersedes claims — review explicitly:"]
        lines += [
            f"- {record_id} supersedes {target}" for record_id, target in supersedes
        ]
    closures = [
        (record["id"], record["closure_of"])
        for record in records
        if record.get("closure_of")
    ]
    if closures:
        lines += ["", "Closure records (closed-unmerged PR sweep):"]
        lines += [
            f"- {record_id} explains the closure of PR #{number}"
            for record_id, number in closures
        ]
    return "\n".join(lines) + "\n"


def cmd_submit(args: argparse.Namespace) -> int:
    repo_dir = resolve_repo_dir(args)
    state = load_state(repo_dir)
    validator = load_validator(repo_dir)
    branch = state["branch"]
    today = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")

    added = run_git(
        repo_dir,
        "diff",
        "--name-only",
        "--diff-filter=A",
        f"{state['base_commit']}..HEAD",
        "--",
        "decisions/",
    ).split()
    records = []
    for name in added:
        path = repo_dir / name
        records.append(json.loads(path.read_text(encoding="utf-8")))
    if not records:
        raise fail("no records on this session branch — nothing to submit")

    streams = session_hit_rates(records)

    preferences_path = repo_dir / "preferences.md"
    for record in records:
        if (
            record.get("prediction_stream") != "preference-driven"
            or record.get("outcome") != "hit"
        ):
            continue
        for rule in prediction_rules(record):
            if not preferences_path.exists():
                print(f"WARN: no preferences.md — cannot bump {rule!r}")
                continue
            bumped = bump_preference_counter(
                preferences_path.read_text(encoding="utf-8"),
                rule,
                today,
                validator.COUNTER_RE,
            )
            if bumped is None:
                print(
                    f"WARN: cited rule {rule!r} not found in "
                    "preferences.md — no counter bumped (proposal?)"
                )
                continue
            new_text, count = bumped
            preferences_path.write_text(new_text, encoding="utf-8")
            run_git(repo_dir, "add", "preferences.md")
            run_git(repo_dir, "commit", "-m", f"pref-confirm: {rule} (n={count})")
            print(f"pref-confirm: {rule} (n={count})")

    run_git(repo_dir, "push", "-u", "origin", branch)
    print(f"Pushed {branch}.")

    title = f"decision session {branch.split('/', 1)[1]} — " + (
        f"{len(records)} record(s)"
    )
    body = build_pr_body(records, streams)

    url = os.environ.get("DECISION_MEMORY_URL", "")
    slug = github_slug(url)
    if slug and shutil.which("gh"):
        result = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                slug,
                "--head",
                branch,
                "--title",
                title,
                "--body",
                body,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(result.stdout.strip())
            return 0
        print(
            f"gh pr create failed ({result.stderr.strip()}) — falling back to handoff.",
            file=sys.stderr,
        )

    print()
    print("── PR handoff (managed environment / no usable gh) ──")
    print("The branch is pushed; open the PR with the tooling your")
    print("environment declares, using exactly this title and body:")
    print()
    print(f"Title: {title}")
    print("Body:")
    print(body)
    return 0


def cmd_propose(args: argparse.Namespace) -> int:
    repo_dir = resolve_repo_dir(args)
    today = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
    rule = " ".join(args.rule.split())
    slug = args.slug or re.sub(
        r"-+", "-", re.sub(r"[^a-z0-9]+", "-", rule.lower())
    ).strip("-")[:MAX_SLUG_LENGTH].rstrip("-")
    if not SLUG_RE.match(slug):
        raise fail(f"cannot derive a kebab-case slug from {rule!r}")

    path = repo_dir / "proposals" / f"{today}-{slug}.md"
    if path.exists():
        raise fail(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# Preference proposal: {slug}\n\n"
        f"- {rule} [confirmed: 0, last: {today}]\n\n"
        "Promotion is human-only: a `pref-promote` commit moves the rule "
        "into preferences.md; merging this file is not promotion.\n",
        encoding="utf-8",
    )
    run_git(repo_dir, "add", str(path))
    run_git(repo_dir, "commit", "-m", f"pref-proposal: {rule}")
    print(f"Proposed: {path.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="record.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dir",
        help="path to the session clone (default: $DECISION_MEMORY_DIR)",
    )
    sub = parser.add_subparsers(dest="verb", required=True)

    p_open = sub.add_parser("open", help="start a recording session")
    p_open.add_argument(
        "--session",
        help="opaque session grouping key (default: $CLAUDE_SESSION_ID)",
    )
    p_open.add_argument(
        "--use",
        help="reuse an already-available checkout of the store repo "
        "instead of cloning (validated against DECISION_MEMORY_URL by "
        "owner/repo; worktree must be clean)",
    )
    p_open.set_defaults(func=cmd_open)

    p_record = sub.add_parser("record", help="record decision drafts")
    p_record.add_argument(
        "--from",
        dest="from_file",
        help="JSON file with a draft record or an array of drafts "
        "(default: read stdin)",
    )
    p_record.set_defaults(func=cmd_record)

    p_check = sub.add_parser("check", help="validate the whole corpus")
    p_check.set_defaults(func=cmd_check)

    p_submit = sub.add_parser("submit", help="push and open the session PR")
    p_submit.set_defaults(func=cmd_submit)

    p_propose = sub.add_parser("propose", help="propose a preference rule")
    p_propose.add_argument("--rule", required=True, help="the rule text")
    p_propose.add_argument("--slug", help="override the derived file slug")
    p_propose.set_defaults(func=cmd_propose)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
