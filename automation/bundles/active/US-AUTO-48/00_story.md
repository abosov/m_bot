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

