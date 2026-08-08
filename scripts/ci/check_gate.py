#!/usr/bin/env python3
"""The uniform CI gate (agentic-engineering-template#137, #143).

Three subcommands, one per job in ci-ok.yml:

  ticket     the PR names its tickets in the canonical ALL-CAPS form
  reviews    every human review thread is answered with a verified
             commit URL or a line starting with the central file's
             `no_commit_marker`
  aggregate  every job of every pull_request-triggered workflow on
             this head SHA succeeded — the one required context

Decision logic lives in pure functions over plain data so the tests
exercise it without a network; `fetch` is the only door to the API.
Exit 0 on green, 1 with each violation named on red.
"""

import json
import os
import re
import sys
import time
import urllib.request

import yaml

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
SERVER = os.environ.get("GITHUB_SERVER_URL", "https://github.com")


def api_url(path):
    """The absolute URL for an API path, refusing any non-HTTP scheme.

    `API` comes from the environment, so a hostile or fat-fingered
    `GITHUB_API_URL` could otherwise steer the gate's own reads at
    `file:` and have it judge a PR on whatever it found on disk. The
    scheme is checked here, once, because this is the only place a URL
    is built.
    """
    url = API + path
    if not url.startswith(("https://", "http://")):
        scheme = url.split(":", 1)[0] if ":" in url else url
        raise ValueError(f"GITHUB_API_URL must be http(s) — refusing scheme {scheme!r}")
    return url


def fetch(path, token):
    """GET one API path, parsed. The only network call in this file."""
    req = urllib.request.Request(  # noqa: S310 — api_url rejects every other scheme
        api_url(path),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req) as response:  # noqa: S310 — checked above
        return json.load(response)


def paginate(path, token, key=None):
    """Every page of a list endpoint, 100 at a time."""
    sep = "&" if "?" in path else "?"
    items = []
    page = 1
    while True:
        batch = fetch(f"{path}{sep}per_page=100&page={page}", token)
        if key is not None:
            batch = batch.get(key, [])
        items.extend(batch)
        if len(batch) < 100:
            return items
        page += 1


# ------------------------------------------------------------- ticket

# `#123` or `owner/repo#123`.
REF = r"(?:[\w.-]+/[\w.-]+)?#\d+"


def ticket_violations(body, branch, labels, author, config):
    """Violations of the reference rules, and whether the escape held.

    The allow-list is exact ALL CAPS: the gate recognizes only the
    canonical forms, and separately REJECTS any of the forge's native
    closing keywords in any other casing — a `resolves #5` in prose
    would close the ticket on merge without the gate ever auditing it,
    which is the false-accept this deny scan exists for. The only
    escape is the `automated` label on a bot-authored PR: an agent
    doing manual work cannot honestly hold either half.
    """
    allowed = config["allowed"]
    native = {word.lower() for word in config["github_native"]}
    if "automated" in labels and str(author).endswith("[bot]"):
        return [], True

    problems = []
    text = body or ""
    found = re.findall(
        r"\b(" + "|".join(map(re.escape, allowed)) + r") (" + REF + r")", text
    )
    for match in re.finditer(r"\b([A-Za-z]+) (" + REF + r")", text):
        word, ref = match.group(1), match.group(2)
        if word in allowed:
            continue
        if word.lower() in native or word.upper() in allowed:
            problems.append(
                f"'{word} {ref}' is not canonical — write "
                f"{'/'.join(sorted(allowed))} in ALL CAPS, or drop the keyword"
            )
    if not found:
        problems.append(
            "the body carries no canonical ticket reference — "
            f"{'/'.join(sorted(allowed))} #n (or owner/repo#n) is required"
        )

    named = re.match(config["branch_pattern"], branch or "")
    if named:
        in_body = {re.search(r"#(\d+)$", ref).group(1) for _, ref in found}
        for number in sorted(set(named.group(1).split("-")) - in_body, key=int):
            problems.append(
                f"the branch names ticket {number} but the body never "
                f"references #{number} with a canonical keyword"
            )
    return problems, False


def closing_refs(body, config, repo):
    """The tickets this PR would close on merge, as owner/repo#n.

    Only keywords the central file tags `closing` count — ADVANCES is
    non-closing by design, and hardcoding the split here would be the
    second copy of a fact reference-keywords.json already owns. Bare
    `#n` is the merging repo's own ticket, so it normalizes against
    `repo` rather than staying ambiguous.
    """
    closers = sorted(w for w, kind in config["allowed"].items() if kind == "closing")
    refs = set()
    pattern = r"\b(?:" + "|".join(map(re.escape, closers)) + r") (" + REF + r")"
    for match in re.finditer(pattern, body or ""):
        ref = match.group(1)
        refs.add(ref if "/" in ref else f"{repo}{ref}")
    return sorted(refs)


def open_prs_of(events, exclude):
    """Open PRs among a ticket's cross-references, as owner/repo#n.

    The timeline is the forge's own reference index: no text search to
    miss a phrasing, cross-repo for free, and sources the token cannot
    read are simply absent rather than errors. `exclude` drops the PR
    under judgement — it always references its own tickets.
    """
    prs = set()
    for event in events:
        if event.get("event") != "cross-referenced":
            continue
        source = event.get("source", {}).get("issue") or {}
        if "pull_request" not in source or source.get("state") != "open":
            continue
        name = f"{source['repository']['full_name']}#{source['number']}"
        if name != exclude:
            prs.add(name)
    return sorted(prs)


def warn_premature_close(body, config, repo, number, token):
    """#150: closing a ticket other open PRs still reference is loud.

    A warning, never a failure — a shared mention is often legitimate
    (a see-also, a quoted changelog), and forcing ADVANCES onto a
    genuinely final PR would teach people to stop declaring closes.
    Anything unreadable is a notice for the same reason a consumer
    whose workflow lags the script by one release must not go red.
    """
    tickets = closing_refs(body, config, repo)
    if not tickets:
        return
    if not token:
        print("::notice::no GH_TOKEN — cannot check closing targets for other open PRs")
        return
    for ticket in tickets:
        ticket_repo, _, ticket_number = ticket.rpartition("#")
        try:
            events = paginate(
                f"/repos/{ticket_repo}/issues/{ticket_number}/timeline", token
            )
        except (OSError, ValueError) as error:
            print(f"::notice::could not check {ticket} for other open PRs: {error}")
            continue
        others = open_prs_of(events, exclude=f"{repo}#{number}")
        if others:
            print(
                f"::warning::merging closes {ticket}, but other open PRs still "
                f"reference it: {', '.join(others)}. If they share its work, "
                f"this PR should ADVANCES the ticket and the last one close it."
            )


def run_ticket():
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as handle:
        event = json.load(handle)
    pr = event["pull_request"]
    config = reference_config()
    problems, escaped = ticket_violations(
        pr.get("body"),
        pr["head"]["ref"],
        [label["name"] for label in pr.get("labels", [])],
        pr["user"]["login"],
        config,
    )
    if escaped:
        print("automated escape: bot-authored PR carries the automated label.")
        return 0
    for problem in problems:
        print(f"::error::{problem}")
    if not problems:
        print("Ticket references are canonical.")
    warn_premature_close(
        pr.get("body"),
        config,
        os.environ["GITHUB_REPOSITORY"],
        pr["number"],
        os.environ.get("GH_TOKEN"),
    )
    return 1 if problems else 0


# ------------------------------------------------------------ reviews


def thread_of(comments):
    """REST review comments grouped into threads by their root."""
    threads = {}
    for comment in comments:
        root = comment.get("in_reply_to_id") or comment["id"]
        threads.setdefault(root, []).append(comment)
    return list(threads.values())


def review_violations(threads, pr_author, pr_shas, base_url, marker):
    """Human threads left without a qualifying author reply.

    Qualifying: a full commit URL under `base_url` whose sha is one of
    this PR's own commits — a pasted-but-wrong link fails, and a bare
    hash fails by design — or a line starting exactly with the central
    file's `no_commit_marker`. Resolving a thread is not answering it;
    this never reads resolution.
    """
    url_re = re.compile(
        re.escape(base_url) + r"/[\w.-]+/[\w.-]+/commit/([0-9a-f]{7,40})\b"
    )
    problems = []
    for comments in threads:
        first = comments[0]
        opener = first["user"]["login"]
        if opener == pr_author or opener.endswith("[bot]"):
            continue
        answered = False
        for reply in comments[1:]:
            if reply["user"]["login"] != pr_author:
                continue
            body = reply.get("body") or ""
            linked = any(
                any(sha.startswith(match.group(1)) for sha in pr_shas)
                for match in url_re.finditer(body)
            )
            marked = any(line.strip().startswith(marker) for line in body.splitlines())
            if linked or marked:
                answered = True
                break
        if not answered:
            where = first.get("path") or "(general)"
            problems.append(
                f"review thread by {opener} at {where} has no reply from "
                f"{pr_author} carrying a commit URL on this PR or a '{marker} <why>' line"
            )
    return problems


def reference_config():
    """The central keyword file — required, never defaulted (#144).

    Every rule value is passed explicitly from the one central
    location; a missing file or key fails loudly rather than silently
    reverting to a built-in the file no longer controls. The store
    variants carry the same file for the same reason, byte-pinned.
    """
    with open(os.environ["REFERENCE_KEYWORDS"], encoding="utf-8") as handle:
        return json.load(handle)


def run_reviews():
    token = os.environ["GH_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as handle:
        event = json.load(handle)
    pr = event["pull_request"]
    number = pr["number"]
    comments = paginate(f"/repos/{repo}/pulls/{number}/comments", token)
    shas = [c["sha"] for c in paginate(f"/repos/{repo}/pulls/{number}/commits", token)]
    marker = reference_config()["no_commit_marker"]
    problems = review_violations(
        thread_of(comments), pr["user"]["login"], shas, SERVER, marker
    )
    for problem in problems:
        print(f"::error::{problem}")
    if not problems:
        print("Every human review thread is answered.")
    return 1 if problems else 0


# ---------------------------------------------------------- aggregate


def triggers_of(doc):
    """The `on:` mapping of a parsed workflow. YAML 1.1 reads bare
    `on` as boolean True, so both spellings are looked up."""
    if not isinstance(doc, dict):
        return {}
    on = doc.get("on", doc.get(True, {}))
    if isinstance(on, str):
        return {on: None}
    if isinstance(on, list):
        return {name: None for name in on}
    return on if isinstance(on, dict) else {}


def expects_pr_run(text):
    """Does this workflow produce a run for every PR head SHA?

    True when it triggers on pull_request with default types or an
    explicit list containing `synchronize` — anything narrower (say
    `[opened]`) has no run for later pushes, so no run can be awaited.
    """
    triggers = triggers_of(yaml.safe_load(text))
    if "pull_request" not in triggers:
        return False
    spec = triggers["pull_request"] or {}
    types = spec.get("types") if isinstance(spec, dict) else None
    return types is None or "synchronize" in types


def aggregate_verdict(expected, runs, jobs_of):
    """(pending, failures) over the expected workflows' newest runs.

    A workflow with no run yet is pending, not failed — the poll loop
    waits it out. A completed job with any conclusion but success is a
    failure: a job that was cancelled or skipped did not pass, and a
    gate that shrugged there would read absence as health.
    """
    pending, failures = [], []
    for path in expected:
        run = runs.get(path)
        if run is None:
            pending.append(f"{path}: no run for this head SHA yet")
            continue
        if run["status"] != "completed":
            pending.append(f"{path}: run {run['id']} is {run['status']}")
            continue
        for job in jobs_of(run["id"]):
            if job["conclusion"] != "success":
                failures.append(
                    f"{path}: job '{job['name']}' concluded {job['conclusion']}"
                )
    return pending, failures


def own_verdict(jobs):
    """(pending, failures) over the gate's own run — judged job by job,
    because this run cannot complete while the gate is still inside it.
    The `ci-ok` job itself is the one exclusion, or it would wait for
    itself forever; its incomplete siblings are pending, not failed,
    since they are in flight exactly while this loop runs.
    """
    pending, failures = [], []
    for job in jobs:
        if job["name"] == "ci-ok":
            continue
        if job["status"] != "completed":
            pending.append(f"own run: job '{job['name']}' is {job['status']}")
        elif job["conclusion"] != "success":
            failures.append(
                f"own run: job '{job['name']}' concluded {job['conclusion']}"
            )
    return pending, failures


def own_workflow_path(workflow_ref, repo):
    """The gate's own workflow file, from GITHUB_WORKFLOW_REF.

    Static, never inferred from the run listing: the gate re-runs on
    review events, and those runs are invisible to a listing filtered
    to `event=pull_request` — the lookup then misses itself and judges
    its own workflow by a sibling run the concurrency group already
    cancelled, failing the head that is in fact green.
    """
    path = workflow_ref.split("@", 1)[0]
    prefix = f"{repo}/"
    return path[len(prefix) :] if path.startswith(prefix) else path


def run_aggregate():
    token = os.environ["GH_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    sha = os.environ["HEAD_SHA"]
    own_run = int(os.environ["GITHUB_RUN_ID"])
    own_path = own_workflow_path(os.environ["GITHUB_WORKFLOW_REF"], repo)
    deadline = time.monotonic() + int(os.environ.get("CI_OK_TIMEOUT", "1500"))

    workflows = {}
    root = ".github/workflows"
    for name in sorted(os.listdir(root)):
        if name.endswith((".yml", ".yaml")):
            with open(os.path.join(root, name), encoding="utf-8") as handle:
                workflows[f"{root}/{name}"] = handle.read()
    expected = [path for path, text in workflows.items() if expects_pr_run(text)]
    print("Aggregating:", ", ".join(expected))

    while True:
        listed = paginate(
            f"/repos/{repo}/actions/runs?head_sha={sha}&event=pull_request",
            token,
            "workflow_runs",
        )
        # Newest run per workflow path. The gate's own workflow is
        # judged separately, job by job, since its run cannot complete
        # while this loop is inside it.
        runs = {}
        for run in sorted(listed, key=lambda r: r["id"]):
            runs[run["path"]] = run

        def jobs_of(run_id):
            return paginate(f"/repos/{repo}/actions/runs/{run_id}/jobs", token, "jobs")

        pending, failures = aggregate_verdict(
            [p for p in expected if p != own_path], runs, jobs_of
        )
        own_pending, own_failures = own_verdict(jobs_of(own_run))
        pending.extend(own_pending)
        failures.extend(own_failures)
        if failures:
            for failure in failures:
                print(f"::error::{failure}")
            return 1
        if not pending:
            print("Every job of every PR workflow succeeded.")
            return 0
        if time.monotonic() > deadline:
            for item in pending:
                print(f"::error::still pending at the gate's timeout — {item}")
            return 1
        print("waiting:", "; ".join(pending))
        time.sleep(15)


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    runners = {"ticket": run_ticket, "reviews": run_reviews, "aggregate": run_aggregate}
    if verb not in runners:
        print(f"usage: check_gate.py {{{'|'.join(runners)}}}", file=sys.stderr)
        return 2
    return runners[verb]()


if __name__ == "__main__":
    sys.exit(main())
