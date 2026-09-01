#!/usr/bin/env python3
"""The uniform CI gate (agentic-engineering-template#137, #143).

One subcommand per job in ci-ok.yml:

  ticket     the PR names its tickets in the canonical ALL-CAPS form
  reviews    every human review thread is answered with a verified
             commit URL or a line starting with the central file's
             `no_commit_marker`, or resolved by the reviewer
  approval   an allowlisted human's latest review APPROVES the current
             head commit — or the PR is authored by one (#187)
  aggregate  every job of every pull_request-triggered workflow on
             this head SHA succeeded — the one required context
  rerun      stale non-green gate runs on this head SHA are re-run in
             place, so a superseded red stops blocking merge (#190) —
             gate-rerun.yml's job, not ci-ok.yml's
  leaks      no PUSH_BLOCKLIST value appears on any surface this PR
             publishes: title, body, commit messages, commit author
             and committer names/emails, the branch name, the diff,
             the PR's own comment and review threads, and the bodies
             and comments of every ticket the body references (#189)

Decision logic lives in pure functions over plain data so the tests
exercise it without a network; `fetch` is the only door to the API.
Exit 0 on green, 1 with each violation named on red.
"""

import json
import os
import re
import sys
import time
import urllib.error
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


def graphql(query, variables, token):
    """POST one GraphQL query — the read for what REST does not expose.

    Review-thread resolution exists only in the GraphQL schema, so this
    is the file's second network door: a POST to the fixed /graphql
    path, under the same scheme guard as `fetch`.
    """
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(  # noqa: S310 — api_url rejects every other scheme
        api_url("/graphql"),
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as response:  # noqa: S310 — checked above
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(f"GraphQL errors: {payload['errors']}")
    return payload["data"]


def post(path, token):
    """POST one empty-bodied API path — the file's one write door.

    Exists solely for `rerun-failed-jobs` (#190): superseding a stale
    red check run takes a write, where everything the gate JUDGES stays
    behind the two read doors above. Same scheme guard; returns the
    HTTP status, since the endpoint answers 201 with no body.
    """
    req = urllib.request.Request(  # noqa: S310 — api_url rejects every other scheme
        api_url(path),
        data=b"",
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req) as response:  # noqa: S310 — checked above
        return response.status


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


def live_pr(payload, token):
    """The PR as it is NOW, falling back to the event's snapshot.

    The payload is frozen when the run is created, and a re-run replays
    that same payload — so a body corrected after a red run stays
    invisible to every re-run of it, and the gate fails forever for a
    reason that no longer exists (#159). Only the number is taken from
    the event; everything judged is read live.

    A read that fails leaves the payload in place: the gate judges a
    possibly-stale body rather than erroring, which is the same verdict
    it gave before this existed, and never a pass it did not earn.
    """
    if not token:
        return payload
    try:
        fresh = fetch(
            f"/repos/{os.environ['GITHUB_REPOSITORY']}/pulls/{payload['number']}", token
        )
    except OSError as err:
        print(
            f"::notice::could not read the live pull request ({err}) — judging the event payload"
        )
        return payload
    return fresh


def run_ticket():
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as handle:
        event = json.load(handle)
    pr = live_pr(event["pull_request"], os.environ.get("GH_TOKEN"))
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


def review_violations(
    threads, pr_author, pr_shas, base_url, marker, resolved=frozenset()
):
    """The agent's worklist: human threads still needing a response.

    Each violation names its exact thread — opener, path, a quote of
    the comment and its URL — because the reader is the agent deciding
    what to do next, not a human who already knows which comment they
    left.

    Answered: a full commit URL under `base_url` whose sha is one of
    this PR's own commits — a pasted-but-wrong link fails, and a bare
    hash fails by design — or a line starting exactly with the central
    file's `no_commit_marker`. A thread the reviewer RESOLVED is off
    the worklist regardless: resolution is the reviewer's own sign-off
    that nothing more is needed, and demanding a reply on top of it
    gated pandoscope/skills#30 on wording nobody was waiting for
    (agentic-engineering-template#166).
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
        if first.get("id") in resolved:
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
            quote = " ".join((first.get("body") or "").split())
            if len(quote) > 90:
                quote = quote[:87] + "..."
            link = first.get("html_url") or ""
            problems.append(
                f'unanswered review thread by {opener} at {where}: "{quote}"'
                + (f" ({link})" if link else "")
                + f" — reply with a commit URL on this PR or a '{marker} <why>'"
                " line, or the reviewer resolves the thread"
            )
    return problems


RESOLVED_QUERY = """
query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { isResolved comments(first: 1) { nodes { databaseId } } }
      }
    }
  }
}
"""


def resolved_roots(nodes):
    """Root-comment ids of resolved threads, from reviewThreads nodes.

    The databaseId is the same id the REST comments endpoint returns,
    which is what lets resolution — GraphQL-only — exempt threads built
    from REST data.
    """
    roots = set()
    for node in nodes:
        if not node.get("isResolved"):
            continue
        for comment in (node.get("comments") or {}).get("nodes") or []:
            if comment.get("databaseId") is not None:
                roots.add(comment["databaseId"])
    return roots


def resolved_thread_roots(repo, number, token):
    """Every resolved thread's root id, paged."""
    owner, name = repo.split("/", 1)
    nodes = []
    cursor = None
    while True:
        data = graphql(
            RESOLVED_QUERY,
            {"owner": owner, "name": name, "number": number, "cursor": cursor},
            token,
        )
        threads = data["repository"]["pullRequest"]["reviewThreads"]
        nodes.extend(threads["nodes"])
        if not threads["pageInfo"]["hasNextPage"]:
            return resolved_roots(nodes)
        cursor = threads["pageInfo"]["endCursor"]


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
        thread_of(comments),
        pr["user"]["login"],
        shas,
        SERVER,
        marker,
        resolved=resolved_thread_roots(repo, number, token),
    )
    for problem in problems:
        print(f"::error::{problem}")
    if not problems:
        print("Every human review thread is answered.")
    return 1 if problems else 0


# ----------------------------------------------------------- approval


def latest_reviews(reviews):
    """Each reviewer's latest state-bearing review, in submission order.

    COMMENTED reviews carry no verdict and are skipped; everything else
    (APPROVED, CHANGES_REQUESTED, DISMISSED) overwrites the reviewer's
    earlier entry — GitHub returns reviews chronologically, so the last
    one standing is the reviewer's current word.
    """
    current = {}
    for review in reviews:
        if review.get("state") == "COMMENTED":
            continue
        user = (review.get("user") or {}).get("login")
        if user:
            current[user] = review
    return current


def approval_violations(reviews, approvers, author, labels, head_sha):
    """Why the PR lacks a current human approval, and whether the
    escape held.

    The pass conditions, in order:
    - `automated` label on a bot-authored PR — the same escape as the
      ticket gate, so release and template-update PRs do not wait on a
      human click (#187 records this as a deliberate hole).
    - the PR's AUTHOR is an allowlisted approver — an author cannot
      approve their own PR, and authorship is approval by the same
      party.
    - some approver's latest review is APPROVED on the current head
      commit. An approval on an older commit is stale and named as
      such: whatever was approved is not what would merge.

    A CHANGES_REQUESTED from an approver is named explicitly — it is
    not merely "no approval", it is a standing objection.
    """
    if "automated" in labels and str(author).endswith("[bot]"):
        return [], True
    if author in approvers:
        return [], False

    problems = []
    stale = []
    for user, review in latest_reviews(reviews).items():
        if user not in approvers:
            continue
        state = review.get("state")
        if state == "APPROVED":
            if review.get("commit_id") == head_sha:
                return [], False
            stale.append(
                f"approval by {user} is stale — it approved "
                f"{str(review.get('commit_id'))[:7]}, the head is now "
                f"{str(head_sha)[:7]}; re-approve the current state"
            )
        elif state == "CHANGES_REQUESTED":
            problems.append(
                f"{user} requested changes — address them or have the review dismissed"
            )
    problems.extend(stale)
    if not problems:
        problems.append(
            "no approving review from an allowlisted human "
            f"({'/'.join(sorted(approvers)) or 'none configured'}) — "
            "an approver clicks Approve, or authors the PR"
        )
    return problems, False


def approvers_config():
    """The central approvers file — required, never defaulted (#144).

    An empty list is as loud as a missing file: a gate that waved
    through every PR because nobody was listed would read absence as
    approval.
    """
    with open(os.environ["MERGE_APPROVERS"], encoding="utf-8") as handle:
        approvers = json.load(handle)["approvers"]
    if not approvers or not all(isinstance(a, str) and a for a in approvers):
        raise ValueError(
            f"{os.environ['MERGE_APPROVERS']} lists no approvers — "
            "name at least one human login"
        )
    return approvers


def run_approval():
    token = os.environ["GH_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as handle:
        event = json.load(handle)
    pr = live_pr(event["pull_request"], token)
    reviews = paginate(f"/repos/{repo}/pulls/{pr['number']}/reviews", token)
    problems, escaped = approval_violations(
        reviews,
        approvers_config(),
        pr["user"]["login"],
        [label["name"] for label in pr.get("labels", [])],
        pr["head"]["sha"],
    )
    if escaped:
        print("automated escape: bot-authored PR carries the automated label.")
        return 0
    for problem in problems:
        print(f"::error::{problem}")
    if not problems:
        print("A current human approval covers this head.")
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


# -------------------------------------------------------------- rerun


def stale_gate_runs(runs, gate_path):
    """Completed non-green runs of the gate workflow, oldest first.

    A re-judge event spawns a FRESH gate run; the prior red run's check
    runs stay `failure` on the same head SHA, and required-check
    evaluation counts that stale red over the newer green (#190 —
    observed blocking #188's merge). Only re-running the old run in
    place supersedes its verdict. `skipped` already passes evaluation,
    so it is not stale; anything else non-success is.
    """
    return [
        run
        for run in sorted(runs, key=lambda run: run["id"])
        if run["path"] == gate_path
        and run["status"] == "completed"
        and run["conclusion"] not in ("success", "skipped")
    ]


def gate_busy(runs, gate_path):
    """Is any run of the gate workflow still queued or in flight?

    Re-running an old run while a fresh one is in progress queues into
    the same `ci-ok-<pr>` concurrency group and cancel-in-progress
    kills the fresh run — trading one stale red for another. The rerun
    therefore waits for quiet first, which is also why it lives in its
    own workflow with its own group.
    """
    return any(
        run["path"] == gate_path and run["status"] != "completed" for run in runs
    )


def run_rerun():
    """Re-run each stale red gate run once, serially, then stop.

    This job SYNCS old runs with the gate's current verdict; it never
    judges. A rerun re-executes the gate's own jobs, which read live
    data (#159), so a red flips green only when the condition genuinely
    holds now — a still-unmet condition reruns red and keeps blocking,
    which is correct and not this job's failure. Hence exit 0 on every
    orderly path; each run is attempted at most once so a legitimately
    red gate cannot loop.
    """
    token = os.environ["GH_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    sha = os.environ["HEAD_SHA"]
    gate_path = os.environ["GATE_WORKFLOW"]
    deadline = time.monotonic() + int(os.environ.get("GATE_RERUN_TIMEOUT", "1500"))

    attempted = set()
    while True:
        runs = paginate(
            f"/repos/{repo}/actions/runs?head_sha={sha}", token, "workflow_runs"
        )
        if not gate_busy(runs, gate_path):
            stale = [
                run
                for run in stale_gate_runs(runs, gate_path)
                if run["id"] not in attempted
            ]
            if not stale:
                done = f"re-ran {sorted(attempted)}" if attempted else "none found"
                print(f"No stale non-green gate runs left on {sha} ({done}).")
                return 0
            run = stale[0]
            attempted.add(run["id"])
            print(f"re-running failed jobs of run {run['id']} ({run['conclusion']})")
            try:
                post(f"/repos/{repo}/actions/runs/{run['id']}/rerun-failed-jobs", token)
            except urllib.error.HTTPError as err:
                # E.g. a cancelled run with nothing rerunnable (409) —
                # note it and move on; syncing must not go red itself.
                print(f"::warning::rerun of {run['id']} refused: {err}")
        if time.monotonic() > deadline:
            print("::warning::gate runs still in flight at the rerun timeout.")
            return 0
        time.sleep(15)


# -------------------------------------------------------------- leaks


def parse_blocklist(value):
    """PUSH_BLOCKLIST env → (value, name) pairs, blanks dropped.

    `|`-separated values (pandoscope/skills#46); the variable carries
    WHAT to block and nothing else, so the committed side of the
    contract is just this parser and the variable's name. An entry may
    name its own placeholder (`value=pb:name`, `=` and `|` reserved):
    the name is what violations and scrub placeholders say, and it
    survives list edits where a positional index would drift. An
    unlabeled entry falls back to its raw field position.
    """
    if not value:
        return []
    pairs = []
    for position, entry in enumerate(value.split("|"), start=1):
        term, _, name = entry.partition("=")
        term = term.strip()
        if term:
            pairs.append((term, name.strip() or f"entry {position}"))
    return pairs


def leak_violations(surfaces, values):
    """Denylist hits over (label, text) surfaces — value-silent.

    Case-insensitive substring match, one violation per (surface,
    entry) pair; `values` is parse_blocklist output. The violation
    names WHERE and WHICH entry — by the entry's own placeholder name
    when it carries one — never WHAT: the values are the identifying
    material this gate keeps off public surfaces, and this gate's own
    log on a public repo is such a surface (#189).
    """
    problems = []
    for label, text in surfaces:
        lowered = (text or "").lower()
        for term, name in values:
            if term.lower() in lowered:
                problems.append(
                    f"{label} carries PUSH_BLOCKLIST {name} — "
                    "scrub it and rewrite the offending commit or text"
                )
    return problems


def referenced_tickets(body, repo):
    """Every ticket the body mentions, keyword or not, as owner/repo#n.

    Broader than closing_refs on purpose: a see-also reference leaks
    exactly like a CLOSES, so any `#n` / `owner/repo#n` occurrence
    puts that ticket's surfaces under the scan.
    """
    refs = set()
    for match in re.finditer(REF, body or ""):
        ref = match.group(0)
        refs.add(ref if "/" in ref else f"{repo}{ref}")
    return sorted(refs)


def pr_surfaces(
    pr, commits, files, comments=(), reviews=(), review_comments=(), tickets=()
):
    """Every text surface this PR publishes, labeled for the verdict.

    Commit metadata is listed explicitly because no established
    scanner covers author/committer name and email (#189) — an agent's
    misconfigured git identity auto-publishes on merge with no
    approval step in between. The PR's own comment threads and the
    tickets it references (`tickets` is (ref, body, comments) tuples)
    are scanned too: those publish the instant they are posted, so
    this cannot prevent — but the gate re-runs on PR events, and a hit
    blocks merge and goes loud instead of lingering quietly.
    """
    surfaces = [("PR title", pr.get("title")), ("PR body", pr.get("body"))]
    if pr.get("head"):
        surfaces.append(("branch name", pr["head"].get("ref")))
    for ref, body, ticket_comments in tickets:
        surfaces.append((f"ticket {ref} body", body))
        for comment in ticket_comments:
            surfaces.append(
                (f"ticket {ref} comment {comment['id']}", comment.get("body"))
            )
    for entry in commits:
        sha = entry["sha"][:7]
        commit = entry["commit"]
        surfaces.append((f"commit {sha} message", commit.get("message")))
        for role in ("author", "committer"):
            who = commit.get(role) or {}
            surfaces.append((f"commit {sha} {role} name", who.get("name")))
            surfaces.append((f"commit {sha} {role} email", who.get("email")))
    for changed in files:
        surfaces.append((f"diff of {changed['filename']}", changed.get("patch")))
    for comment in comments:
        surfaces.append((f"comment {comment['id']}", comment.get("body")))
    for review in reviews:
        surfaces.append((f"review {review['id']}", review.get("body")))
    for comment in review_comments:
        where = comment.get("path") or "(general)"
        surfaces.append(
            (f"review comment {comment['id']} on {where}", comment.get("body"))
        )
    return surfaces


def run_leaks():
    token = os.environ["GH_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    values = parse_blocklist(os.environ.get("PUSH_BLOCKLIST"))
    if not values:
        # An unset org secret must not fail every fork and fresh
        # consumer, but silence would hide that the layer is off.
        print("::warning::PUSH_BLOCKLIST is empty — the denylist layer is inactive")
        return 0
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as handle:
        event = json.load(handle)
    pr = live_pr(event["pull_request"], token)
    number = pr["number"]
    commits = paginate(f"/repos/{repo}/pulls/{number}/commits", token)
    files = paginate(f"/repos/{repo}/pulls/{number}/files", token)
    tickets = []
    for ref in referenced_tickets(pr.get("body"), repo):
        ticket_repo, _, ticket_number = ref.rpartition("#")
        try:
            issue = fetch(f"/repos/{ticket_repo}/issues/{ticket_number}", token)
            ticket_comments = paginate(
                f"/repos/{ticket_repo}/issues/{ticket_number}/comments", token
            )
        except (OSError, ValueError) as error:
            # A ref the token cannot read (foreign or private repo) is
            # not this gate's to judge — say so and move on.
            print(f"::notice::could not scan referenced ticket {ref}: {error}")
            continue
        tickets.append((ref, issue.get("body"), ticket_comments))
    problems = leak_violations(
        pr_surfaces(
            pr,
            commits,
            files,
            comments=paginate(f"/repos/{repo}/issues/{number}/comments", token),
            reviews=paginate(f"/repos/{repo}/pulls/{number}/reviews", token),
            review_comments=paginate(f"/repos/{repo}/pulls/{number}/comments", token),
            tickets=tickets,
        ),
        values,
    )
    for problem in problems:
        print(f"::error::{problem}")
    if not problems:
        print("No blocklisted string on any surface this PR publishes.")
    return 1 if problems else 0


def main():
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    runners = {
        "ticket": run_ticket,
        "reviews": run_reviews,
        "approval": run_approval,
        "aggregate": run_aggregate,
        "rerun": run_rerun,
        "leaks": run_leaks,
    }
    if verb not in runners:
        print(f"usage: check_gate.py {{{'|'.join(runners)}}}", file=sys.stderr)
        return 2
    return runners[verb]()


if __name__ == "__main__":
    sys.exit(main())
