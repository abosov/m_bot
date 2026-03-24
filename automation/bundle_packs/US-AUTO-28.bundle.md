# Story Bundle Pack
Story-ID: US-AUTO-28
Version: 1

=== FILE: 00_story.md ===
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

=== FILE: 01_context_bundle.md ===
# Context Bundle

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
The pipeline now has stronger run/review/gate fidelity and an explicit commit handoff before run, but repeated reject cycles can still happen when the system keeps rejecting the same story without meaningful progress. The current system can fail closed, but it does not yet provide a deterministic governance handoff path when repeated reject outcomes represent stagnation rather than an ordinary implementation defect.

## Architectural Intent
Introduce a small deterministic escalation layer above ordinary reject handling. The system must distinguish between:
- ordinary reject, where constrained follow-up work may continue
- repeated reject stagnation, where automated continuation must stop and a human must choose the next governance action

The first version should remain simple, auditable, and fail-closed.

## Risks
- false-positive escalation if stagnation criteria are too broad
- accidental weakening of review gate if escalation is treated like approval
- operator ambiguity if escalation actions are not explicit
- evidence drift if escalation is not tied to concrete reviewed run / HEAD metadata

## Acceptance Notes
A valid outcome for this story should include:
- deterministic escalation criteria
- explicit escalation-required state
- blocked automatic continuation after escalation
- explicit human resolution path:
  - accept-as-is
  - force-followup
  - abort
- updated analysis/remediation messaging
- focused tests and documentation updates

=== FILE: 02_file_scope.md ===
# File Scope

## Files Allowed To Change
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/escalate_story.sh`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`
- `tests/test_run_story.py`
- `tests/test_escalate_story.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-28.bundle.md`
- `automation/bundles/active/US-AUTO-28/00_story.md`
- `automation/bundles/active/US-AUTO-28/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-28/02_file_scope.md`
- `automation/bundles/active/US-AUTO-28/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-28/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-28/05_followups.md`
- `automation/bundles/active/US-AUTO-28/06_manual_actions.md`

## Files Not Allowed To Change
- database migrations
- application product code outside automation governance flow
- GitHub Actions workflows unless a direct blocker is proven
- unrelated bundle packs or active bundles for other stories
- unrelated review classification taxonomy files unless directly required by this story
- any file not needed for the escalation gate contract

=== FILE: 03_master_prompt.md ===
# US-AUTO-28 PROMPT 1 — Escalation gate for repeated reject stagnation

## Goal
Implement a deterministic escalation layer that stops automated continuation when repeated reject outcomes show no meaningful progress and requires an explicit human decision before the story may proceed further.

## Role
You are the Workflow Architect, Bash/Python Automation Developer, QA Engineer, and Tech Writer for the Zumbot US-AUTO pipeline.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- current scripts and tests for run/review/gate/analyze flow

## Files Allowed To Change
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/escalate_story.sh`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`
- `tests/test_run_story.py`
- `tests/test_escalate_story.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change
- unrelated automation scripts
- product application code
- unrelated stories / bundles
- GitHub Actions workflows unless directly required by this story
- broad classification taxonomy redesign

## Output
Produce a minimal, deterministic implementation that:
1. detects repeated reject stagnation
2. marks escalation as required
3. blocks ordinary automated continuation once escalation is required
4. provides an explicit operator command to resolve escalation through:
   - accept-as-is
   - force-followup
   - abort
5. surfaces escalation state clearly in artifacts / analysis output
6. adds focused tests and documentation updates

Keep the patch narrow. Do not absorb US-AUTO-25 or US-AUTO-26 into this story.

=== FILE: 04_review_checklist.md ===
# Review Checklist

## Scope Validation
- Verify the patch stays within escalation detection and explicit operator resolution.
- Verify the patch does not absorb US-AUTO-25 or US-AUTO-26.
- Verify no unrelated automation refactors are included.
- Verify file changes stay within the allowed scope.

## Functional Validation
- Verify escalation is triggered only by documented deterministic conditions.
- Verify ordinary one-off rejects still behave as ordinary rejects.
- Verify escalation does not silently approve or merge anything.
- Verify the implementation remains fail-closed.
- Verify the operator has a clear explicit command to resolve escalation.
- Verify supported actions are documented:
  - accept-as-is
  - force-followup
  - abort

## Verification
- Verify escalation state is visible in inspectable artifacts.
- Verify analysis output makes escalation-required state obvious.
- Verify positive trigger tests exist.
- Verify negative / non-trigger tests exist.
- Verify continuation-block tests exist.
- Verify explicit resolution action tests exist.
- Verify docs and epic registry are updated consistently.

=== FILE: 05_followups.md ===
# Follow-ups

## Follow-Up Prompt Queue
1. **US-AUTO-25 — loop detection**
   - richer repeated-reject detection across categories / history
   - generalized loop telemetry and stronger classification of loop patterns

2. **US-AUTO-26 — protection from repeated identical runs**
   - block run when HEAD/diff is unchanged before expensive repeated execution
   - broader deduplication before run

3. **US-AUTO-27 — tighter pipeline zone boundaries**
   - refine where each stage may write and how scope is enforced across stages

## Iteration Notes
- Keep US-AUTO-28 intentionally small and deterministic.
- If implementation requires broader history indexing, heavy diff comparison, or cross-story analytics, stop and capture a follow-up instead of widening this story.
- Prefer explicit escalation metadata over hidden log-only behavior.

=== FILE: 06_manual_actions.md ===
# Manual Actions

## Required Human Actions
1. Save this bundle pack to:
   - `automation/bundle_packs/US-AUTO-28.bundle.md`
2. Materialize the bundle:
   - `automation/scripts/materialize_story_bundle.sh US-AUTO-28`
3. Validate the active bundle:
   - `automation/scripts/validate_story_bundle.sh automation/bundles/active/US-AUTO-28`
4. Update:
   - `docs/90_codex/epics/US-AUTO_REGISTRY.md`
5. Commit story artifacts before run:
   - `automation/scripts/commit_story_artifacts.sh US-AUTO-28`
6. Execute the story:
   - `automation/scripts/run_story.sh US-AUTO-28`

## Completion Status
- Bundle draft prepared
- Waiting for successful materialize
- Waiting for bundle validation
- Waiting for registry update
- Waiting for artifact commit handoff
- Waiting for story execution