# Claude Code Specific Project Instructions

**First:** Read `AGENTS.md`. Follow all instructions and skills there.

### Pull Requests

Share PR URL in response to user. Run CI poll after push, confirm green before reporting done.

### CI Polling (`scripts/ci_poll.py`)

Uses exponential backoff (15s → 60s cap).

```bash
python scripts/ci_poll.py                         # latest run, current branch
python scripts/ci_poll.py --workflow ci.yml       # specific workflow
python scripts/ci_poll.py --sha HEAD              # match exact commit (use after push)
python scripts/ci_poll.py --tail 100              # more failure log lines (default 50)
```

**Token-saving pattern:** Always `--sha HEAD` after push. Run in background. Poll both workflows parallel. Grep output for `FAILED`/`Error`/`assert`/`Traceback` — don't read whole log.
