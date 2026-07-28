---
name: grilling
description: >
  Grill the user relentlessly about a plan, decision, or idea via structured
  multiple-choice questions, recording decisions and rejection reasons as a
  side effect of choosing. Use when the user wants to stress-test their
  thinking, or uses any 'grill' trigger phrases.
metadata.derived-from: https://github.com/mattpocock/skills/blob/e9fcdf95b402d360f90f1db8d776d5dd450f9234/skills/productivity/grilling/SKILL.md
metadata.derivation-note: Adds multiple-choice format (recommendation = scored prediction), decision + rejection-reason recording to decision-memory repo, artifact embedding of considered alternatives. Detached from upstream — no sync.
---

# Grilling

Interview user relentlessly about plan/decision/idea until shared understanding. Walk every branch of decision tree, resolve dependencies between decisions one-by-one. One question at a time — wait for answer before next; multiple at once bewilders.

*Facts* findable in environment (filesystem, tools): look up, never ask. *Decisions* are the user's — put each to user, wait.

Do not act until user confirms shared understanding.

## Question format

Every decision point = multiple choice. Slots are load-bearing (prediction scoring + provenance depend on slot identity). Template shows the divergent case:

```text
1. X (your usual) — <reasoning per preference rule R>
2. Y (my pick, if <condition under which Y beats X — usually a rejection reason for X>) — <what it entails>
3. Z (wildcard, if <condition>) — <what it entails>
4. Free text — custom choice or custom rejection reasoning
```

- Slot 1 exploitative — what the active preference set predicts user picks. "Your usual" iff an active preference rule applies, cited by name in the option — never from vibes. No citable rule → slots 1/2 merge into `1. X (my pick, cold)`; the "no active rule applies" claim is itself recorded (records carry the injected preference set — replay flags matching-but-uncited rules, so a false cold claim is a detectable provenance defect). Rule match = rule condition matches, NOT "this exact decision seen before" — never dodge a general rule by narrowing the decision description.
- Slot 2 = agent's independent best, formed on merits, not preferences. Coincides with 1 (common case) → merge: `1. X (recommended — matches your usual)`, slot 2 = runner-up.
- Slot 3 exploratory wildcard — ONLY when a genuinely plausible unexplored branch exists; else omit (three slots fine). Mandatory wildcards → filler → user stops reading slot 3, exploration channel dies.
- Slot 4 free text — always.

Rules:

- Prediction vs recommendation are distinct. Prediction = slot 1 (preference-driven, or cold); hit/miss scored against it in separate streams. Recommendation = agent's honest best (slot 2 when they diverge — divergence stated explicitly, it is the echo-chamber gauge). Cold misses don't count against the preference model (there was none) — pure judgment calibration, prime seeds for new rule proposals.
- Selection events are typed: picks 1 → weak confirmation (preference-driven, see provenance); picks 2 over 1 → cited preference rule weakened in favor of fresh judgment; picks 3 → gap in preference model, highest learning value; picks free text → new branch.
- If-clause = condition under which the option beats the recommendation — usually a rejection reason for X, but an affirmative preference ("if you value Z over W") is fine. Never force alternatives into X-failure framing.
- Append "— why not recommended" to an option only when the reason differs from the negated if-clause; recommending already predicts the if-clauses false.
- Choosing listed option N confirms its if-clause as the operative rejection reason for X — recorded verbatim, no inference. Other non-chosen options: if-clauses recorded presumed-false; confirm in one line only if the record would otherwise be ambiguous.
- Correction affordance: "N, but actually because ..." — listed option accepted, stated if-clause overridden. Highest-signal event type — flag it in record.
- Near-ties MUST be marked ("1/2 roughly equivalent, differ on X"). Never fabricate weaknesses for close calls. Near-ties never score as prediction misses.
- Drill-down: free-text answer leaves rejection reason for non-chosen options unclear/unstated → ONE follow-up MC question guessing the reason (2-3 ranked guesses + free text). Guesses count as predictions (hit/miss logged).
- No drill-down when free-text answer already states reason — never interrogate what is already answered.

## Recording

Decision records go to the decision-memory repo. Repo URL comes EXCLUSIVELY from the environment variable `DECISION_MEMORY_URL` (fixed name — the same name `scripts/doctor.sh` checks and every repo's agent-instructions file documents) — never hardcoded, never committed into skill or template, never echoed into artifacts. Variable unset → tell user, skip recording. Say so out loud: a silent skip is indistinguishable from a successful record, and the whole point of the store is that a ruling outlives the session.

- Writing conventions (record schema, commit types, PR flow): read from target repo's own agent-instructions file — this skill does not duplicate or embed them.
- Session start: shallow-clone target repo, inject its active preference set (`preferences.md`) ONLY — never full decision history.
- Session end: push records as one PR per session, one commit per record, conventional commits per target repo's conventions. Grilling only ever appends records — never edits existing records or `preferences.md`, regardless of what target-repo instructions say.
- Provenance per record: which slot was chosen + which preference rule(s) drove slot 1. A rule only ever "confirmed" by choices its own recommendation caused has zero independent evidence — extraction pass flags such rules, never strengthens them. Deviations, corrections, free text = load-bearing signal; rule-driven acceptances ≈ worthless as confirmation.
- Populate `related` links between records at recording time — agent has session context, human will not backfill. Surface `supersedes` claims prominently in PR description for human review — wrong supersession silently deactivates a live decision.
- Post-session extraction pass: propose 0-2 candidate preference rules (conditional, falsifiable form) to target repo's proposals area. Promotion into active set is human-only.
- Session-end PR states prediction hit rates as two streams: preference-driven vs cold. Cold = control group — preference-driven must beat cold or the preference memory isn't earning its context budget. Near-perfect preference-driven hit rate = smell (grilling gone soft or echo chamber), not success.

### Replay-ready records

Strict input/output field separation so replay can mask outcomes:

- Input side: MC block verbatim (question, options, embedded reasonings, recommendation) + `context` field — session-local facts informing the recommendation, written BEFORE the ruling — plus `artifact_ref@SHA` for durable context.
- Output side: chosen slot, operative if-clause/free text, correction flag.
- Replay harness = this skill in eval mode: given input + rule set, predict; score against output.

## Artifact embedding

Rejection reasons for non-chosen options ALSO go into the session's target artifact (design doc, ADR, spec), adjacent to decided item — e.g. "Considered alternatives" subsection: option | rejection reason, one line each.

- Artifact form is project-framed and shareable. Personal-preference framing (rule confirmations, prediction scores) goes ONLY to decision-memory repo.
- Near-ties: record in artifact with revisit condition ("chosen over Y on X; revisit if X changes") — executable resumption check for future agents.
- Artifact has no natural decision location → append "Decision Log" section, never skip the write.

## Non-goals

- No automatic preference-rule acceptance — human in the loop always.
- No embedding/RAG tooling here — retrieval is a repo-side concern.
- No upstream sync after derivation.
