---
name: tdd
description: Test-driven development via red-green-refactor with an auditable commit protocol. Use when implementing any feature, bugfix, refactor, or behavior change before writing implementation code, or when the user mentions TDD, red-green-refactor, or test-first development.
metadata.derived-from: merge of mattpocock/skills' `tdd` (https://github.com/mattpocock/skills/blob/7afa86d3a5dd96edde06ffa014e16c64e733681e/skills/engineering/tdd/SKILL.md) + obra/superpowers' `test-driven-development` (https://github.com/obra/superpowers/blob/030a222af19c1f3a93c6eb876a7422d8e4fc0162/skills/test-driven-development/SKILL.md)
metadata.derivation-note: Commit protocol (red/green commits, markers, lint-red.sh) and the vertical-slice framing are the load-bearing original parts. Diff prose against upstream, not the protocol.
---

# Test-Driven Development

Write test first. Commit it red. Write minimal code to pass. Commit green. Refactor.

**Core principle:** tests verify behavior through public interfaces, not implementation. Code can change entirely; tests shouldn't. A test that breaks when you rename an internal function — with no behavior change — was testing implementation. Delete it.

No watched failure = no proof the test tests the right thing. Commit history is the evidence; hooks check its structure.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for mocking guidelines.

## Iron Law

NO PRODUCTION CODE WITHOUT A FAILING TEST COMMITTED FIRST.

Wrote code before the test? Delete it. Implement fresh from tests. Delete means delete. Exceptions (throwaway prototypes, generated code, config) need human sign-off. Thinking "skip TDD just this once"? That is rationalization.

## 1. Plan (before any code)

Use the project's domain glossary so test names and interface vocabulary match the codebase; respect ADRs in the area you touch.

- List the *behaviors* to test, not implementation steps. Prioritize critical paths and complex logic — you can't test everything.
- Design interfaces for [testability](interface-design.md); identify opportunities for [deep modules](deep-modules.md) (small interface, deep implementation)
- Confirm the public interface and the priority behaviors with the user, then proceed.

## 2. Vertical slices, not horizontal

DO NOT write all tests, then all implementation. That is horizontal slicing and it produces crap tests: written in bulk they test *imagined* behavior and the *shape* of things (signatures, data structures), go insensitive to real changes, and commit you to test structure before you understand the code.

Work in vertical slices — one test → one implementation → repeat. Each test responds to what the last cycle taught you.

```text
WRONG (horizontal):  RED: t1 t2 t3 t4   GREEN: i1 i2 i3 i4
RIGHT (vertical):    t1→i1  t2→i2  t3→i3 ...
```

The first slice is a tracer bullet: it proves the path works end to end.

## 3. Commit protocol

One behavior = one RED commit + one GREEN commit. Multiple cycles per branch is fine; prefer one cycle in flight in Go/Rust repos (see markers).

### RED commit

- Write one failing test. One behavior, clear name, real code — no mocks unless unavoidable.
- Run it *unmarked*; watch it fail for the **right reason** (feature missing — not a typo or import error). Passes immediately? It tests existing behavior — fix the test.
- Add the marker (below), suite green, commit. Tests only, prefix `test(red):`.

| Language | Marker | Strict? |
| --- | --- | --- |
| Python (pytest) | `@pytest.mark.xfail(strict=True)` | yes — XPASS fails suite |
| TS/JS (vitest) | `test.fails(...)` / `it.fails(...)` | yes |
| TS/JS (jest) | `it.failing(...)` | yes |
| Go | `//go:build red` + `TestRed` prefix + `red-tests` job | aggregate only |
| Rust | `#[ignore = "red"]` + `red_` prefix + `red-tests` job | aggregate only |
| Other | find a strict expected-failure mechanism; none exists → commit unmarked, tell the human the repo lacks red enforcement | n/a |

Go/Rust build-tag/ignore markers *exclude* tests from the normal suite, so a `red-tests` CI job must run only the marked tests and expect failure (no-op when none exist). Its exit code is aggregate: two red tests in flight, one wrongly passing → the job still passes. Strict markers catch this per-test; the job doesn't.

### GREEN commit

- Simplest code that passes. YAGNI — no speculative generality.
- Remove this cycle's red markers. No other test changes in this commit.
- Full suite green, output pristine. Fails? Fix the code, not the test. Prefix `feat:`/`fix:`.

### REFACTOR (after green only)

Remove duplication, improve names, extract helpers, deepen modules. Tests stay green, no new behavior, separate commit. **Never refactor while red.** Then start the next cycle.

After all tests pass, look for [refactor candidates](refactoring.md):

## Enforcement — and its limits

`lint-red.sh` (ships with skill; wire into prek + CI): `staged`/`commit` modes check that `test(red):` commits touch only test files and add a marker, others add none; `merge` mode rejects any markers in tree; if Go/Rust markers are present, a `red-tests` job must exist.

Hooks verify commit *structure* and marker hygiene. They do **not** verify you ran the unmarked test and watched it fail for the right reason — that stays on you. Strict markers partially compensate (XPASS catches tests of already-existing behavior). "Lint passed" ≠ "TDD verified."

## Good tests

| Quality | Rule |
| --- | --- |
| Behavioral | Exercises a real path through the public API; survives refactors |
| Minimal | One thing. "and" in the name? Split it. |
| Clear | Name states the behavior, not `test1` |
| Honest | Tests the code, never the mock |

```ts
// Good — tests real behavior (vitest; jest: it.failing)
test.fails('retries failed operations 3 times', async () => {
  let attempts = 0;
  const op = () => { attempts++; if (attempts < 3) throw new Error('fail'); return 'ok'; };
  expect(await retryOperation(op)).toBe('ok');
  expect(attempts).toBe(3);
});
```

## Red flags — STOP, delete, restart

Unmarked test passes before implementation exists · can't explain why the test failed · weakening an assertion in GREEN to make it pass · testing the mock · "just this once" · "I'm being pragmatic, TDD is dogmatic."

Read [testing-anti-patterns.md](testing-anti-patterns.md) to avoid common pitfalls.

## Rationalization table

| Excuse | Reality |
| --- | --- |
| "Too simple to test" | Simple code breaks. The test takes 30s. |
| "I'll test after" | Tests-after are biased by the implementation: "what does this do?" not "what should this?" |
| "Deleting hours of code is wasteful" | Sunk cost. Unverified code is debt. |
| "Test is hard to write" | Hard to test = hard to use. Listen to it; simplify the interface. |
| "Must mock everything" | Too coupled. Inject dependencies. |
| "Lint passed, TDD done" | Hooks check structure, not that you watched the failure. |

## When stuck / debugging

Don't know how to test → write the wished-for API and assertion first. Found a bug → write a failing test reproducing it, then run the full protocol. Never fix a bug without a test.
