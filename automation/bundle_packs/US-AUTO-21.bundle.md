=== FILE: 00_story.md ===
# US-AUTO-21: Enforce Clean Commit Boundary Before Review Gate

## Story ID and Title
- Story ID: `US-AUTO-21`
- Title: `Enforce Clean Commit Boundary Before Review Gate`

## Objective
Prevent review and gate from running against a branch state that contains uncommitted materialized changes, so AI review always evaluates commit-consistent evidence.

## Scope
- Add an explicit clean-commit-boundary rule before review/gate execution.
- Detect when the current branch working tree is dirty before review/gate starts.
- Block review/gate before AI review and classification begin if the reviewed branch state is not commit-consistent.
- Return a clear operator-facing error explaining what to do next.
- Update docs and tests for the new workflow rule.

## Non-goals
- No automatic git commit creation by automation.
- No redesign of review/gate to operate on arbitrary working-tree snapshots instead of commit-based evidence.
- No changes to business logic of Codex implementation or story execution semantics outside review-boundary enforcement.
- No redesign of review artifact generation in `automation/run_codex_task.sh`.

## Dependencies
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- existing run artifacts under `automation/runs/<STORY_ID>/...`

## Source of Truth
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `tests/test_review_story_run.py`
- `tests/test_review_gate_story_run.py`

## Current Code Reality
- `automation/run_codex_task.sh` already enforces a clean tree before execution, runs Codex in an isolated worktree, materializes resulting changes into the primary checkout, and builds review artifacts from a commit-range base.
- After materialization, the current branch can legitimately contain uncommitted changes in the primary checkout.
- `review_story_run.sh` currently summarizes the latest run but does not enforce a clean commit boundary before review.
- `review_gate_story_run.sh` currently proceeds into review/classification flow without a fail-fast dirty-tree precheck.
- This can produce false review-gate rejections because review evidence is interpreted as if it reflected a committed branch state while the operator is still holding uncommitted materialized changes.

## Target Outcome
- Review and gate fail fast when the current branch working tree is dirty.
- The operator gets explicit guidance on how to restore a review-safe state.
- AI review and classification never start from a non-committed branch state.
- Commit-based review remains the source of truth.

## Acceptance Notes
- Fail closed if branch state is not review-safe.
- The console message must clearly explain that uncommitted materialized changes must be inspected and committed before review/gate proceeds.
- The guidance may suggest rerunning `automation/scripts/run_story.sh <STORY_ID>` only if a fresh run is desired for the newly committed state.
- The normal clean-tree path must remain unchanged.

=== FILE: 01_context_bundle.md ===
# US-AUTO-21: Context Bundle

## Source of Truth
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Current Code Reality
- Story execution already uses isolated worktree execution and materialization into the primary checkout.
- Review artifacts are already derived from commit-based evidence, not just from transient working-tree state.
- The remaining workflow gap is at review/gate time: the operator can hold valid materialized changes locally without committing them, and the review layer currently does not fail fast on that inconsistency.
- This creates a false-reject class: artifact integrity / workflow compliance can fail even though the implementation itself is acceptable.

## Architectural Intent
- Keep commit-based review as the source of truth.
- Enforce a clean commit boundary before review/gate.
- Prefer explicit operator control over hidden automation.
- Fail fast before AI review/classification starts when branch state is not review-safe.

## Risks
- Overblocking review if the check is broader than intended.
- Underblocking review if dirty-tree detection is incomplete or inconsistent between scripts.
- Confusing operator guidance if the script implies rerunning Codex is always required when only a commit is needed.

## Acceptance Notes
- The failure message must be explicit and actionable.
- The blocked state must be visible in both `review_story_run.sh` and `review_gate_story_run.sh`.
- The implementation should stay minimal and avoid redesigning runner behavior.

=== FILE: 02_file_scope.md ===
# US-AUTO-21: File Scope

## Files Allowed To Change
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `tests/test_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `automation/bundle_packs/US-AUTO-21.bundle.md`
- `automation/bundles/active/US-AUTO-21/**`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `backend/**`
- `migrations/**`
- `.github/workflows/**`

## Scope Notes
- This story enforces review/gate safety boundary only.
- Do not redesign run artifact generation.
- Do not add auto-commit or hidden git mutation behavior.
- Prefer fail-fast prechecks in review-stage scripts over deeper runner changes.

=== FILE: 03_master_prompt.md ===
# US-AUTO-21 PROMPT 1 — Enforce Clean Commit Boundary Before Review Gate

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Story
US-AUTO-21 — Enforce Clean Commit Boundary Before Review Gate

## Goal
Prevent review/gate from evaluating artifact bundles when the current branch contains uncommitted materialized changes and therefore does not represent a commit-consistent review state.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_review_story_run.py`
- `tests/test_review_gate_story_run.py`

## Files Allowed To Change
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `tests/test_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `automation/bundle_packs/US-AUTO-21.bundle.md`
- `automation/bundles/active/US-AUTO-21/**`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `backend/**`
- `migrations/**`
- `.github/workflows/**`

## Current Problem
The runner can validly materialize isolated-worktree changes into the primary checkout.
That leaves the branch dirty until the operator reviews and commits those changes.
The review/gate layer currently does not stop on that dirty state before AI review starts.
As a result, AI review may classify a run against evidence that is not aligned with committed branch state, causing false rejects.

## Implementation Requirements
1. Add a review-stage precheck that detects whether the current branch working tree is dirty before review/gate proceeds.
2. Fail fast before AI review/classification starts when review evidence is not commit-consistent.
3. Make `review_story_run.sh` surface whether the latest run is review-safe or blocked by dirty working tree.
4. Make `review_gate_story_run.sh` refuse to proceed when the current branch is dirty.
5. Keep behavior fail-closed.
6. Do not modify `automation/run_codex_task.sh`.
7. Do not add auto-commit behavior.

## Operator UX Requirements
When blocked, print a clear operator-facing message that explains:
- uncommitted materialized changes exist in the current branch
- review/gate is blocked because branch state is not commit-consistent
- inspect and commit the changes first
- if a fresh run is needed for the newly committed state, rerun `automation/scripts/run_story.sh <STORY_ID>`
- then rerun `automation/scripts/review_gate_story_run.sh <STORY_ID>`

## Suggested UX Shape
Example review summary block:
Review safety: BLOCKED
Reason: working tree contains uncommitted materialized changes
Next step:
1. inspect changes
2. commit changes
3. if needed, rerun automation/scripts/run_story.sh US-AUTO-21
4. rerun automation/scripts/review_gate_story_run.sh US-AUTO-21


Example gate failure block:
ERROR: review gate blocked for 'US-AUTO-21'
Reason: current branch has uncommitted changes; review artifacts would not match committed state
Required action:
- inspect and commit the materialized changes
- if needed, rerun automation/scripts/run_story.sh US-AUTO-21
- rerun automation/scripts/review_gate_story_run.sh US-AUTO-21

Testing

Add or update focused tests that verify:

clean working tree allows normal review/gate flow

dirty working tree blocks review_story_run.sh with explicit status/output

dirty working tree blocks review_gate_story_run.sh before AI review starts

operator-facing message is actionable and stable

Documentation

Update workflow docs/checklists to describe the clean commit boundary rule before review/gate.

Output

Return:

changed files summary

design rationale

validation performed

risks / follow-ups

final diff

=== FILE: 04_review_checklist.md ===

US-AUTO-21: Review Checklist
Scope Validation

 Changes stay inside 02_file_scope.md

 No redesign of runner snapshot semantics

 No changes to automation/run_codex_task.sh

 No hidden auto-commit behavior introduced

Functional Validation

 Review is blocked when working tree is dirty

 Gate is blocked before AI review/classification starts

 review_story_run.sh clearly reports blocked review safety state

 Error message is actionable and explicit

 Clean working tree still allows normal review/gate flow

Architecture / Source of Truth

 Commit-based review remains the source of truth

 Fail-fast boundary is enforced at review stage

 Review/gate layer does not rely on hidden git mutation

 Docs reflect the new workflow rule

Verification

 Tests cover clean-tree pass case

 Tests cover dirty-tree block case

 Gate output is verified

 No unrelated automation behavior changed

=== FILE: 05_followups.md ===

US-AUTO-21: Follow-Ups
Follow-Up Prompt Queue

Consider a later story for richer review-stage observability and failure surfacing.

Consider a later story for refreshing or regenerating review artifacts without rerunning Codex when branch state changes after review.

Consider snapshot-aware review only if clean-commit-boundary enforcement proves too restrictive in practice.

Iteration Notes

This story intentionally solves the current false-reject class without redesigning the whole review model.

The preferred tradeoff is predictable operator control and fail-fast safety over convenience.

=== FILE: 06_manual_actions.md ===

US-AUTO-21: Manual Actions
Required Human Actions

Review the fail-fast message in a synthetic dirty-working-tree scenario.

Confirm the operator guidance matches the intended local workflow.

Execution Notes

Test once with a clean tree and confirm review/gate still works.

Test once with a dirty tree after a successful materialized run and confirm gate blocks before AI review starts.

Completion Status

 No manual actions required

 Manual actions completed and documented