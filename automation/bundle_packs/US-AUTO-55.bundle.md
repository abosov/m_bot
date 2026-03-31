# Story Bundle Pack
Story-ID: US-AUTO-55
Version: 1

=== FILE: 00_story.md ===
# US-AUTO-55

## Story ID and Title
US-AUTO-55 — Manual-finish final-HEAD review compliance after allowed non-converging rerun continuation

## Objective
Restore strict but usable downstream review compliance for the one allowed exception path introduced by the workflow: manual-finish continuation after `blocked_non_converging_rerun`.

The story must ensure that `ai_review_story_run.sh`, `classify_review_story_run.sh`, `review_gate_story_run.sh`, and `analyze_story_run.sh` treat that allowed continuation path consistently with final reviewed `HEAD` semantics, without reopening rerun loops and without weakening committed-HEAD review boundaries.

## Scope
In scope:
- downstream review-stage compliance for the exact allowed manual-finish continuation path
- final-HEAD evidence handling for pinned run artifacts after branch tip advances through allowed manual finish
- deterministic fail-closed rejection when final-HEAD compliance cannot be proven
- focused regression coverage for the exact allowed path and nearby reject cases
- registry and story artifact updates required by this story

Out of scope:
- diff fidelity changes already completed in US-AUTO-54
- rerun orchestration changes
- retry logic changes
- operator UX messaging improvements beyond minimal evidence/reason surfacing needed for correctness
- broad manual-finish redesign
- escalation logic and unrelated pipeline stages

## Non-goals
- Do not change the normal rule that ordinary review must consume a fresh committed-head rerun.
- Do not make `run -> commit -> review` valid as a general workflow.
- Do not weaken workspace-only, stale-run, or ancestor/descendant boundary checks outside the exact allowed manual-finish continuation contract.
- Do not introduce fallback behavior that silently accepts unproven final-HEAD lineage.
- Do not broaden this story into stage-gate guidance; that remains US-AUTO-56.

## Dependencies
- US-AUTO-46 — committed-HEAD review boundary
- US-AUTO-47 — rerun convergence boundary
- US-AUTO-52 — strict manual-finish continuation contract
- US-AUTO-53 — committed-HEAD diff.patch review fidelity
- US-AUTO-54 — rerun diff fidelity fix for the reproduced US-AUTO-28-F1 path

## Source of Truth
- docs/90_codex/epics/US-AUTO_REGISTRY.md
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh
- tests/test_ai_review_story_run.py
- tests/test_classify_review_story_run.py
- tests/test_review_gate_story_run.py
- tests/test_analyze_story_run.py
- tests/test_review_pipeline_validation_contract.py

## Current Code Reality
US-AUTO-54 fixed the rerun-artifact diff fidelity defect for the reproduced US-AUTO-28-F1 path, so `review_diff_patch_mismatch` is no longer the blocker on a clean committed-head rerun.

The remaining defect is narrower:
- the pipeline explicitly allows manual-finish continuation after `blocked_non_converging_rerun`
- during that allowed continuation, branch `HEAD` advances
- pinned run artifacts remain tied to the pre-manual-finish committed `HEAD`
- downstream review stages still interpret that state as workflow/branch compliance failure, even though the continuation itself is allowed by contract

This creates an internal pipeline contradiction:
- one part of the workflow allows continuation
- downstream review still demands strict final-HEAD alignment with no compliant continuation evidence path

## Target Outcome
After implementation:
- the exact allowed manual-finish continuation path can reach downstream review stages with compliant final-HEAD semantics
- downstream stages either:
  1. accept the exact allowed final-HEAD lineage for the pinned continuation path, or
  2. fail closed with explicit deterministic evidence that final-HEAD compliance was not proven
- ordinary stale-head or generic descendant/ancestor cases remain rejected
- no rerun loop is reopened
- no orchestration scope is widened

## Atomic Task Isolation Contract
This story is intentionally narrow.

Allowed problem to solve:
- final-HEAD review compliance for the exact allowed manual-finish continuation case after `blocked_non_converging_rerun`

Not allowed:
- changing normal review eligibility rules
- changing run orchestration
- changing retry policy
- changing diff generation fidelity
- changing general operator guidance policy
- adding broad artifact refresh workflows
- changing escalation behavior

If implementation pressure suggests broader workflow redesign, stop and fail closed rather than expanding scope.

## Risks
- Scope drift into orchestration or rerun policy
- Accidental fail-open acceptance of stale or unrelated descendant `HEAD`
- Inconsistent interpretation across AI review, classification, gate, and analyze
- Regression in ordinary committed-head review path
- Hidden dependence on ad hoc workspace state instead of deterministic committed evidence

## Manual Actions
- Materialize this bundle pack
- Validate the materialized bundle
- Update registry status conservatively for US-AUTO-55
- Create a feature branch before implementation
- Commit story artifacts before run
- Run the story on the feature branch
- Analyze the resulting pinned run before any review-stage continuation

## Acceptance Notes
Acceptance requires all of the following:
1. Ordinary workflow still rejects `run -> commit -> review` without a fresh committed-head rerun.
2. Exact allowed manual-finish continuation after `blocked_non_converging_rerun` can produce compliant downstream review behavior for final branch `HEAD`.
3. If final-HEAD compliance cannot be proven, downstream stages fail closed with deterministic evidence/reasoning.
4. Ancestor-run, unrelated descendant, or generic stale-head variants remain rejected.
5. No diff fidelity regression is introduced.
6. No orchestration or retry behavior changes are introduced.
7. Tests cover both exact-allow and nearby-reject cases.

=== FILE: 01_context_bundle.md ===
# Context Bundle

## Source of Truth
- docs/90_codex/epics/US-AUTO_REGISTRY.md
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh
- existing committed manual-finish continuation logic from US-AUTO-52
- existing committed diff fidelity behavior from US-AUTO-53 and US-AUTO-54
- focused regression suites covering review boundary and pipeline validation contracts

## Current Code Reality
The pipeline currently has two simultaneously true facts:
1. manual-finish continuation is explicitly allowed after `blocked_non_converging_rerun`
2. downstream review stages still expect pinned artifacts to align directly with the final reviewed `HEAD`

That mismatch causes the allowed continuation path to behave like a compliance violation once the branch tip advances through manual finish.

The defect is not in:
- diff.patch fidelity
- basic committed-head enforcement
- rerun boundary detection

The defect is in downstream interpretation of allowed continuation lineage versus final reviewed `HEAD`.

## Architectural Intent
The workflow must remain fail-closed.

The intended architecture is:
- normal review operates on a fresh committed-head rerun
- manual-finish continuation is a tightly constrained exception
- exceptions must still be evidence-based and deterministic
- downstream stages must never guess that a newer `HEAD` is compliant; they must prove the exact allowed lineage or reject

The correct repair is therefore:
- add or interpret deterministic continuation evidence for final-HEAD compliance in the exact allowed manual-finish path
- preserve strict rejection for all other stale or ambiguous variants

## Risks
- Broadening the exception beyond the exact allowed path
- Accepting descendant `HEAD` without proving it belongs to the approved continuation
- Divergent logic between AI review, classification, gate, and analyze
- Confusing evidence model that forces future stories to patch around hidden semantics
- Turning an allowed exception into an implicit general rule

## Acceptance Notes
A good implementation:
- keeps the exception narrow
- uses deterministic committed evidence, not heuristics
- preserves ordinary review invariants
- gives analyze/gate enough information to explain why the exact path is allowed or rejected
- does not reopen the rerun loop

=== FILE: 02_file_scope.md ===
# File Scope

## Files Allowed To Change
- automation/bundle_packs/US-AUTO-55.bundle.md
- automation/bundles/active/US-AUTO-55/00_story.md
- automation/bundles/active/US-AUTO-55/01_context_bundle.md
- automation/bundles/active/US-AUTO-55/02_file_scope.md
- automation/bundles/active/US-AUTO-55/03_master_prompt.md
- automation/bundles/active/US-AUTO-55/04_review_checklist.md
- automation/bundles/active/US-AUTO-55/05_followups.md
- automation/bundles/active/US-AUTO-55/06_manual_actions.md
- docs/90_codex/epics/US-AUTO_REGISTRY.md
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh
- tests/test_ai_review_story_run.py
- tests/test_classify_review_story_run.py
- tests/test_review_gate_story_run.py
- tests/test_analyze_story_run.py
- tests/test_review_pipeline_validation_contract.py

## Files Not Allowed To Change
- automation/scripts/run_story.sh
- automation/scripts/review_story_run.sh
- automation/run_codex_task.sh
- automation/scripts/commit_story_artifacts.sh
- automation/scripts/materialize_story_bundle.sh
- automation/scripts/validate_story_bundle.sh
- tests/test_run_story.py
- tests/test_run_codex_task.py
- any files outside the defined scope

## Scope Notes
Allowed change types:
- narrow downstream evidence/compliance logic
- deterministic reject reasoning
- focused test updates

Hard limits:
- no orchestration changes
- no diff fidelity changes
- no UX expansion (US-AUTO-56)

=== FILE: 03_master_prompt.md ===
# Master Prompt

## Role
You are the implementation engineer for US-AUTO-55 working inside the fail-closed Codex automation pipeline.

## Goal
Implement a narrow fix so downstream review stages handle the exact allowed manual-finish continuation path with compliant final-HEAD semantics after `blocked_non_converging_rerun`, while preserving all ordinary committed-head review rules and rejecting any unproven stale or ambiguous lineage.

## Source of Truth
- docs/90_codex/epics/US-AUTO_REGISTRY.md
- automation/scripts/*
- tests/*

## Files Allowed To Change
(same as 02_file_scope.md)

## Files Not Allowed To Change
(same as 02_file_scope.md)

## Atomic Task Isolation Contract
Only fix manual-finish compliance

## Execution Gate
Stop if orchestration changes required

## Implementation Requirements
- deterministic evidence
- fail-closed
- no fallback

## Verification Requirements
- pytest
- allow + reject cases

## Output
- minimal changes
- focused tests

=== FILE: 04_review_checklist.md ===
# Review Checklist

## Scope Validation
- only allowed files changed
- no orchestration changes

## Functional Validation
- manual-finish path works
- others rejected

## Verification
- tests pass

HARD BLOCK:
- reject on scope drift
- reject on fail-open

=== FILE: 05_followups.md ===
# Follow-Ups

## Follow-Up Prompt Queue
- US-AUTO-56
- US-AUTO-26
- US-AUTO-27

## Iteration Notes
- atomic story
- medium complexity
- narrow blast radius

=== FILE: 06_manual_actions.md ===
# Manual Actions

## Required Human Actions
1. save bundle
2. materialize
3. validate
4. commit
5. run
6. analyze

## Completion Status
- [ ] bundle saved
- [ ] materialized
- [ ] validated
- [ ] committed
- [ ] run completed
- [ ] analyzed