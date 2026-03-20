# US-AUTO-23 — Story Change Ledger

## Story
Create a durable append-only story change ledger that records story-level lifecycle events across run, review, and finalize/close steps so later anti-cycle stories can detect repeated iteration from committed evidence.

## Why
The epic registry identifies US-AUTO-23 as the first anti-cycle story and the prerequisite for downstream loop-detection and enforcement work. The current gap is that anti-cycle enforcement does not yet exist beyond docs/policy guidance. This story must introduce only the history primitive, not enforcement decisions.

## Problem Statement
The automation workflow has trace artifacts in run directories and review outputs, but there is no single durable story-level ledger that answers:
- how many attempts a story has gone through
- which lifecycle outcomes occurred
- whether the story repeated the same reject/follow-up pattern
- how downstream preflight logic can inspect committed history without re-parsing multiple ad hoc artifacts

Without a durable ledger, future anti-cycle stories must infer repetition indirectly, which increases ambiguity and implementation risk.

## Scope
This story must add only:
- one durable story change ledger artifact in the repository
- one small writer/helper layer for appending normalized ledger entries
- minimal lifecycle integration points that append entries during:
  - story start
  - review outcome
  - finalize/close outcome
- focused tests for ledger append and lifecycle recording
- documentation/checklist updates needed to explain the ledger
- epic registry updates reflecting story progress

## Non-Goals
Do not implement any of the following in this story:
- loop detection preflight
- blocking decisions before run
- expensive run budget limits
- pipeline zone caps
- escalation gates
- merge recommendation redesign
- new review classification semantics
- new operator UX workflows
- broad console output redesign
- database storage
- network calls or external telemetry
- background daemons or polling

## Architectural Intent
US-AUTO-23 introduces only an evidence layer:
- append-only
- repository-visible
- human-reviewable
- deterministic enough for downstream scripts
- non-blocking by itself

This story records history. It does not interpret that history into stop/continue policy.

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- existing lifecycle scripts that already define canonical story run/review/finalize flow
- existing completed US-AUTO stories showing PR-based execution and finalize discipline

## Current Code Reality
- Story execution and review already exist as scripted lifecycle phases.
- Finalization/closure already exists in the workflow.
- Durable story-level history is missing as a normalized committed artifact.
- Anti-cycle work is planned downstream, but there is not yet a shared ledger primitive for it.

## Target Outcome
After this story:
- the repository contains one canonical story change ledger artifact
- lifecycle scripts append normalized entries to that ledger at a small number of stable checkpoints
- reviewers can inspect story attempt history in one place
- downstream US-AUTO-24 can read the ledger instead of reconstructing history from scattered artifacts

## Data Contract
Each ledger entry should be intentionally small and normalized. A reasonable entry shape may include:
- story_id
- timestamp
- run_id or attempt reference
- branch
- pr_number if known
- event_type
- status/classification if known
- reason_code if known
- artifact_ref
- short_note

The exact field names may be adjusted for implementation simplicity, but the contract must stay small, explicit, and deterministic.

## Lifecycle Event Minimum Set
Record only stable checkpoints:
- story_started
- review_outcome
- story_rejected when applicable
- story_finalized when applicable

Do not add speculative intermediate states.

## Atomic Task Isolation Contract
This story has one purpose only:
Create a durable append-only story ledger and wire it into a minimal number of existing lifecycle checkpoints.

Codex must restate this one-sentence purpose before making edits.

If the implementation appears to require any of the following, Codex must stop and document a follow-up instead of expanding scope:
- preflight blocking rules
- rerun throttling/budget logic
- escalation policy
- zone caps
- broad review-gate redesign
- operator UX redesign
- refactoring unrelated automation scripts
- changing classification semantics outside what is necessary to record existing outcomes

## Files Allowed To Change
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `automation/bundle_packs/US-AUTO-23.bundle.md`
- `automation/bundles/active/US-AUTO-23/**`
- one new ledger artifact path under `automation/`
- one new helper/utility module or script for ledger append under `automation/scripts/` or a nearby automation utility path
- only the minimal existing lifecycle scripts required to append ledger entries at:
  - start
  - review outcome
  - finalize/close
- focused tests covering the changed automation paths

## Files Forbidden To Change
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- bundle materialization logic, unless absolutely required for this story and explicitly justified in the review
- validation policy unrelated to ledger presence
- review classification contracts beyond what is necessary to record existing outcomes
- any operator UX story files unrelated to ledger

## Risks
- Overdesigning the ledger into a policy engine
- Recording too many unstable intermediate states
- Touching too many lifecycle scripts and reintroducing scope drift
- Mixing evidence collection with enforcement logic
- Making the ledger schema too heavy for human review

## Acceptance Criteria
- A durable repository-visible story ledger exists.
- Ledger entries are append-only.
- Starting a story records a start entry.
- Review outcome records a review entry and, when applicable, a reject/follow-up entry.
- Finalize/close records a terminal story entry.
- Missing optional metadata such as PR number does not break ledger recording.
- Tests cover ledger append behavior and the chosen lifecycle integration points.
- Documentation explains the ledger as evidence only, not enforcement.
- No preflight blocking, budget guard, zone cap, or escalation logic is implemented.

## Manual Review Focus
Reviewers must verify:
- the story stayed narrow
- the ledger is evidence-only
- no enforcement logic leaked in
- lifecycle integration points are few and stable
- follow-up capture is used for anything beyond the ledger primitive

## Manual Actions
- Inspect the ledger file after one successful run/review/finalize sequence.
- Inspect the ledger file after one rejected review sequence and confirm `review_outcome` + `story_rejected` entries are appended.
- Confirm the resulting history is easy to read and sufficient for later preflight logic.

## Follow-Up Boundary
Potential future stories that must not be absorbed here:
- US-AUTO-24 loop detection preflight
- US-AUTO-25 expensive run budget guard
- US-AUTO-26 pipeline zone cap
- US-AUTO-27 escalation gate
