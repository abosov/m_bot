# US-AUTO-28 — Escalation gate for repeated reject stagnation

## Story ID and Title
- **Story ID:** US-AUTO-28
- **Title:** Escalation gate for repeated reject stagnation

## Objective
Introduce a deterministic escalation layer that stops the pipeline when review/gate outcomes repeat without meaningful progress and requires an explicit human decision before any further automated execution continues.

## Scope
In scope:
- define a formal stagnation / escalation contract for repeated reject outcomes
- add a deterministic escalation decision point after review/gate rejection analysis
- require explicit human action before continuing after escalation is triggered
- add a dedicated operator-facing escalation script / workflow entrypoint
- persist escalation evidence in run artifacts and ledger-compatible workflow evidence
- document operator actions for three outcomes:
  - accept-as-is
  - force-followup
  - abort
- add automated tests for escalation trigger conditions and required manual intervention

Out of scope:
- automatic merge on escalation
- AI-authorized override without human action
- broad redesign of review classification taxonomy
- full run deduplication logic across identical HEAD/diff states
- loop detection heuristics beyond the minimum deterministic contract needed for escalation
- UI/dashboard work
- changes to unrelated stories outside the escalation decision flow

## Non-goals
- do not weaken fail-closed review/gate behavior
- do not allow silent continuation after repeated reject stagnation
- do not auto-resolve governance disputes
- do not introduce probabilistic or opaque AI scoring for escalation
- do not merge code automatically after escalation is detected

## Dependencies
- US-AUTO-39 — re-review / re-gate finalized post-commit HEAD
- US-AUTO-40 — review artifact fidelity to actual HEAD diff
- US-AUTO-41 — commit handoff before run
- existing run/review/gate scripts and the current clean-tree contract
- current epic registry process in `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- current behavior in:
  - `automation/scripts/run_story.sh`
  - `automation/scripts/review_story_run.sh`
  - `automation/scripts/classify_review_story_run.sh`
  - `automation/scripts/review_gate_story_run.sh`
  - `automation/scripts/analyze_story_run.sh`
  - `automation/scripts/finalize_story.sh`

## Current Code Reality
Today the pipeline can repeatedly produce reject outcomes even when the reviewed HEAD has not meaningfully progressed. The current system can fail closed, but it does not yet provide a deterministic governance handoff path when repeated reject outcomes represent stagnation rather than a simple implementation bug. This creates operator friction, repeated review cycles, and risk of governance loops.

## Target Outcome
After this story:
- repeated reject stagnation is detected deterministically
- the pipeline stops and marks the story as requiring escalation
- further automated continuation is blocked until the operator explicitly chooses one of the approved escalation actions
- the chosen human decision is recorded in durable workflow evidence
- operator guidance is documented and test-covered

## Acceptance Criteria
1. A deterministic escalation contract is documented and implemented.
2. Repeated reject outcomes with no meaningful progress trigger an escalation-required state.
3. Once escalation is required, the pipeline refuses to continue automatically.
4. A dedicated operator entrypoint supports explicit actions:
   - accept-as-is
   - force-followup
   - abort
5. Escalation evidence is visible in artifacts produced for analysis / audit.
6. Tests cover positive and negative cases for escalation detection and manual resolution.
7. Documentation is updated to reflect the new governance handoff step.

## Risks / Constraints
- false-positive escalation if stagnation criteria are too broad
- accidental weakening of review gate if escalation is treated like approval
- operator ambiguity if escalation actions are not explicit and mutually exclusive
- evidence drift if escalation state is not tied to concrete reviewed run / HEAD metadata

## Implementation Notes
Start with the smallest deterministic contract:
- repeated reject count threshold
- same or equivalent rejection category
- no meaningful change in the reviewed state
Avoid broader heuristics in this story. Prefer explicit evidence and simple comparison rules.

