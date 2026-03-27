# Story Bundle Pack
Story-ID: US-AUTO-48
Version: 1

=== FILE: 00_story.md ===
# US-AUTO-48 — AI review artifact contract hardening

## Story ID and Title
- **Story ID:** US-AUTO-48
- **Title:** AI review artifact contract hardening

## Objective
Harden the AI review artifact contract so the review pipeline deterministically produces a valid normalized `ai_review_result.md` or fails closed with explicit evidence when normalization is impossible.

## Scope
In scope:
- define and enforce the required normalized AI review artifact contract
- ensure malformed or incomplete AI review output cannot advance downstream implicitly
- require deterministic fail-closed behavior for missing or invalid `ai_review_result.md`
- preserve raw AI review output for debugging
- add focused regression coverage for normalization, classification handoff, gate behavior, and analysis visibility

Out of scope:
- rerun convergence logic from US-AUTO-47
- broad redesign of review pipeline architecture
- unrelated operator UX improvements
- changes to bundle materialization, bundle validation, or finalize flow
- unrelated governance or registry cleanup beyond minimal story bookkeeping

## Non-goals
This story does not:
- modify committed-head rerun behavior
- redesign the full review/classification/gate sequence
- add new recovery workflows unrelated to the AI review artifact contract
- widen into unrelated analysis or reporting improvements

## Dependencies
- `US-AUTO-47` is already implemented and merged to `main`
- existing review-stage scripts:
  - `automation/scripts/ai_review_story_run.sh`
  - `automation/scripts/classify_review_story_run.sh`
  - `automation/scripts/review_gate_story_run.sh`
  - `automation/scripts/analyze_story_run.sh`
- existing focused tests for AI review, classification, gate, and analysis
- epic registry entry for `US-AUTO-48` in `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Source of Truth
Primary sources of truth for this story:
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- the active `US-AUTO-48` bundle files after materialization
- current repository implementations of the review-stage scripts and their focused tests
- the observed failure mode captured in the registry notes for `US-AUTO-48`

## Current Code Reality
The current review pipeline can reach a state where:
- `ai_review_raw_output.txt` exists
- `ai_review_result.md` is missing or malformed
- classification cannot proceed from a validated normalized review artifact
- gate rejects with `ai_review_missing_artifact`

That means the boundary between raw AI output and the normalized review artifact is not enforced strongly enough for downstream consumers.

## Target Outcome
After this story:
- downstream stages no longer assume that `ai_review_result.md` exists and is valid
- the pipeline either produces a valid normalized review artifact or emits deterministic fail-closed evidence
- malformed or incomplete AI review output cannot silently propagate into classification or gate
- focused tests prove the contract
- `US-AUTO-48` remains strictly separate from rerun convergence logic in `US-AUTO-47`

=== FILE: 01_context_bundle.md ===
# Context Bundle — US-AUTO-48

## Source of Truth
Primary sources of truth for this story:
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- current implementations of:
  - `automation/scripts/ai_review_story_run.sh`
  - `automation/scripts/classify_review_story_run.sh`
  - `automation/scripts/review_gate_story_run.sh`
  - `automation/scripts/analyze_story_run.sh`
- current focused tests for AI review, classification, gate, and analysis
- the observed review-pipeline failure recorded as follow-up `US-AUTO-48` in the registry

## Current Code Reality
The current review pipeline can reach a state where:
- `ai_review_raw_output.txt` exists
- `ai_review_result.md` is missing or malformed
- classification cannot proceed deterministically from a validated normalized artifact
- gate rejects with `ai_review_missing_artifact`

This means the boundary between raw model output and the normalized review artifact is not enforced strongly enough for downstream consumers.

## Architectural Intent
The review pipeline must treat the normalized AI review artifact as an explicit contract boundary:
- raw output is diagnostic only
- downstream stages must consume validated normalized artifacts, not assumptions
- if normalization cannot produce a valid `ai_review_result.md`, the system must fail closed with deterministic evidence
- classification, gate, and analysis must present a clear contract failure state instead of an ambiguous partially-reviewed state

## Acceptance Notes
Accept the story only if all of the following are true:
- `ai_review_result.md` is explicitly required and validated before classification proceeds
- malformed or missing normalized AI review artifacts fail closed deterministically
- raw AI review output remains preserved for diagnosis
- downstream stages no longer rely on implicit artifact presence
- focused regression tests cover valid, missing, and malformed artifact paths
- no unrelated rerun convergence or broad pipeline redesign changes are introduced

## Risks
Main risks for this story:
- accidentally widening into general review-pipeline redesign
- changing downstream behavior without focused regression coverage
- introducing hidden fallback behavior that still relies on implicit artifact presence
- coupling this fix to rerun convergence work that belongs to `US-AUTO-47`

=== FILE: 02_file_scope.md ===
# File Scope — US-AUTO-48

## Files Allowed To Change
Only these files may be changed:

- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_ai_review_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-48.bundle.md`
- `automation/bundles/active/US-AUTO-48/00_story.md`
- `automation/bundles/active/US-AUTO-48/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-48/02_file_scope.md`
- `automation/bundles/active/US-AUTO-48/03_master_prompt.md`
- `automation/bundles/active/US-AUTO-48/04_review_checklist.md`
- `automation/bundles/active/US-AUTO-48/05_followups.md`
- `automation/bundles/active/US-AUTO-48/06_manual_actions.md`

## Files Not Allowed To Change
These files are out of scope:

- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/merge_recommendation_contract.sh`
- `automation/story_change_ledger.jsonl`
- any active bundle or bundle pack outside `US-AUTO-48`
- any docs outside the epic registry unless strictly required for this exact contract

=== FILE: 03_master_prompt.md ===
# Master Prompt — US-AUTO-48

## Role
You are implementing a narrow governance follow-up in the Zumbot automation pipeline. Work as a careful maintainer operating under strict atomic-task isolation.

## Goal
Harden the AI review artifact contract so the pipeline deterministically creates a valid normalized `ai_review_result.md` or fails closed with explicit evidence when normalization is impossible.

## Source of Truth
Use only the following as source of truth:
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- the active `US-AUTO-48` bundle files
- current implementations of:
  - `automation/scripts/ai_review_story_run.sh`
  - `automation/scripts/classify_review_story_run.sh`
  - `automation/scripts/review_gate_story_run.sh`
  - `automation/scripts/analyze_story_run.sh`
- corresponding focused tests

## Files Allowed To Change
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_ai_review_story_run.py`
- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/story_change_ledger.jsonl`

## Output
Produce the smallest safe patch that:
- makes the normalized AI review artifact contract explicit and validated
- prevents malformed or incomplete AI review output from silently advancing
- makes classification and gate fail closed deterministically when normalized artifact validation fails
- preserves raw AI review output for debugging
- adds focused regression tests
- avoids unrelated scope expansion

Before editing, restate the one-sentence task intent.
If a required fix falls outside allowed scope, stop and record it in follow-ups instead of widening the patch.

=== FILE: 04_review_checklist.md ===
# Review Checklist — US-AUTO-48

## Scope Validation
- Confirm the patch changes only the AI review artifact contract and direct downstream handling
- Confirm rerun convergence logic from `US-AUTO-47` is untouched
- Confirm no unrelated workflow scripts are modified
- Confirm no unrelated docs or bundle packs are modified

## Functional Validation
- Confirm `ai_review_result.md` is explicitly validated before classification uses it
- Confirm malformed or missing normalized artifacts fail closed deterministically
- Confirm raw AI review output remains available for debugging
- Confirm classification and gate no longer rely on implicit normalized artifact presence
- Confirm analysis clearly reports the contract failure state

## Verification
- Run focused tests for AI review artifact handling
- Run focused tests for classification behavior
- Run focused tests for gate behavior
- Run focused tests for analysis/reporting if changed
- Confirm the relevant test subset passes without unrelated changes

=== FILE: 05_followups.md ===
# Follow-ups — US-AUTO-48

## Follow-Up Prompt Queue
Add entries here only if implementation reveals new work that is out of scope for this story, such as:
- shared helper extraction for artifact schema validation
- broader operator UX improvements for blocked review states
- broader schema unification across review, classification, and gate artifacts
- unrelated cleanup in review-stage messaging

## Iteration Notes
This story must stay narrow.
Do not absorb:
- rerun convergence work
- committed-head rerun fidelity work
- broad review-pipeline redesign
- unrelated operator UX improvements
- unrelated registry cleanup

If a necessary fix exceeds scope, stop and capture it as a precise follow-up rather than widening `US-AUTO-48`.

=== FILE: 06_manual_actions.md ===
# Manual Actions — US-AUTO-48

## Required Human Actions
- Save this bundle pack at `automation/bundle_packs/US-AUTO-48.bundle.md`
- Materialize the bundle with the story ID
- Validate the materialized bundle with the story ID
- Create a fresh implementation branch only after validation succeeds
- After implementation, use a fresh `analyze_story_run.sh US-AUTO-48` output to identify the latest run directory

## Completion Status
Initial manual steps for this story are complete only when:
- the bundle pack is saved
- materialization succeeds
- validation succeeds
- the working tree reflects only expected `US-AUTO-48` bundle artifacts before the implementation branch is created