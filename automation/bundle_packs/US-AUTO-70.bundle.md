# Story Bundle Pack
Story-ID: US-AUTO-70
Version: 1

=== FILE: 00_story.md ===
## Story ID and Title
US-AUTO-70 — Rerun-preflight stable-review recomputation for companion-filtered stories

## Objective
Make `run_story.sh` recompute the effective review surface used by rerun-preflight after companion-artifact filtering has already narrowed the committed implementation surface for a code-only story.

The story must close the specific split confirmed after US-AUTO-69: rerun-preflight must not continue evaluating the unadjusted review surface when companion-artifact filtering has already changed which files are meant to count for acceptance.

## Scope
This story is limited to rerun-preflight and its committed test coverage.

Allowed implementation surface:
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`

The implementation may:
- recompute or refresh the effective filtered review surface before rerun-preflight decisions are made
- preserve fail-closed behavior if the filtered surface cannot be derived deterministically
- add or update narrowly-scoped tests that prove rerun-preflight uses the recomputed filtered surface

## Non-goals
- Do not modify companion-artifact filtering logic in `automation/run_codex_task.sh`
- Do not modify execution-surface filtering tests in `tests/test_run_codex_task.py`
- Do not change review-stage scripts, gate scripts, or analyze scripts
- Do not broaden this story into reuse, cache, telemetry, UX, or general verification optimization
- Do not redefine allowed scope rules for unrelated stories
- Do not introduce fail-open fallback behavior

## Dependencies
- US-AUTO-57 — blocked line that exposed the original companion-artifact problem
- US-AUTO-69 — split execution-filtering half already landed and must remain untouched here
- Existing committed-HEAD, rerun-boundary, and manual-finish invariants from US-AUTO-46, US-AUTO-47, US-AUTO-52, US-AUTO-53, US-AUTO-54, US-AUTO-55, and US-AUTO-56

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`
- Committed workflow invariants already established in the stable layer of the registry
- The split-story observation recorded for US-AUTO-69 / US-AUTO-70 in the registry

## Current Code Reality
US-AUTO-69 solved only the execution-filtering half by narrowing the committed implementation surface for code-only stories where companion artifacts appeared.

The remaining defect is in `run_story.sh`: rerun-preflight still reasons about the pre-filter or otherwise unadjusted surface, so acceptance can still fail even when the execution surface has already been companion-filtered.

That means the current workflow can still report a rerun-preflight outcome against evidence that is wider than the intended effective review surface for the story.

## Target Outcome
After this story:
- rerun-preflight in `run_story.sh` derives the same effective filtered review surface needed for the current story before it decides whether a rerun is necessary or whether the story remains blocked
- if that filtered surface cannot be derived deterministically, the script must fail closed with a clear blocking error instead of silently using stale or widened evidence
- `tests/test_run_story.py` contains committed coverage proving the recomputation is used for the rerun-preflight decision path
- US-AUTO-70 remains atomic: only rerun-preflight recomputation is addressed here

## Atomic Task Isolation Contract
This story exists because US-AUTO-69 was confirmed to be non-atomic when it combined:
1. companion-artifact execution filtering
2. rerun-preflight stable-review recomputation

This story isolates only item 2.

Hard isolation rules:
- edit only the two allowed files
- do not re-open execution filtering logic
- do not add generic review-surface reuse architecture
- do not fix unrelated rerun or review UX issues opportunistically
- if the recomputation path cannot be implemented within the narrow boundary above, fail closed and stop rather than widening scope

## Risks
- Regressing existing rerun-preflight behavior for stories that do not use companion filtering
- Accidentally coupling `run_story.sh` to execution-stage details that belong exclusively in `run_codex_task.sh`
- Introducing hidden scope drift by changing other pipeline stages indirectly
- Overfitting tests to one scenario without preserving general fail-closed invariants

## Manual Actions
- Update the registry entry for US-AUTO-70 to reflect active bundle work before execution
- Materialize and validate this bundle before running the story
- Commit bundle artifacts before `run_story.sh`
- After implementation commit, rerun from committed HEAD and analyze the fresh run before any review-stage continuation

## Acceptance Notes
Acceptance requires all of the following:
- only `automation/scripts/run_story.sh` and `tests/test_run_story.py` change
- rerun-preflight uses a recomputed effective filtered review surface for the companion-filtered path
- non-companion-filtered paths remain stable
- failures remain fail-closed
- no edits are made to `automation/run_codex_task.sh` or `tests/test_run_codex_task.py`
- the story remains atomic and does not absorb broader safe-reuse or UX work

=== FILE: 01_context_bundle.md ===
## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`

## Current Code Reality
The registry now records that US-AUTO-69 was split because companion-artifact execution filtering and rerun-preflight stable-review recomputation are not one atomic change.

US-AUTO-69 already landed the execution-filtering half. The remaining work is explicitly tracked as US-AUTO-70 and is limited to `run_story.sh` plus its tests.

The defect is not stale evidence in the abstract. The defect is that rerun-preflight can still reason over the wrong effective surface after companion filtering has already narrowed what should count for the story.

## Architectural Intent
Preserve the existing fail-closed pipeline and committed-HEAD invariants while making rerun-preflight compute against the correct effective surface for the current story.

The desired architecture is narrow:
- execution filtering remains where it already lives
- rerun-preflight recomputation happens where rerun-preflight decisions are made
- review/gate/analyze contracts remain unchanged
- no new general-purpose reuse subsystem is introduced

This is a correction to decision input fidelity, not a redesign of the pipeline.

## Risks
- Scope drift into execution filtering or later review-stage scripts
- Regressions in normal rerun-preflight behavior for stories that are not companion-filtered
- Fail-open fallback if recomputation errors are swallowed
- Implicit contract drift if tests verify a broader behavior than the story intends

## Acceptance Notes
Review should reject if:
- any file outside the allowed pair changes
- the implementation depends on editing `run_codex_task.sh`
- the recomputation path is inferred loosely rather than deterministically
- errors fall back to the old widened surface
- tests do not prove the companion-filtered rerun-preflight case

=== FILE: 02_file_scope.md ===
## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-69.bundle.md`
- `automation/bundles/active/US-AUTO-69/**`
- any other file not explicitly listed under Files Allowed To Change

## Scope Notes
Allowed change types:
- narrow logic changes in `run_story.sh` that recompute the effective filtered review surface for rerun-preflight
- small helper extraction or local refactor inside `run_story.sh` only if required to keep the behavior deterministic and testable
- targeted tests in `tests/test_run_story.py` that prove:
  - companion-filtered rerun-preflight uses the recomputed filtered surface
  - unchanged paths remain stable
  - failures remain fail-closed

Hard scope rules:
- no companion-filtering rule changes
- no registry editing in this implementation story
- no broad pipeline orchestration changes
- no telemetry, UX, cache, retry, or optimization work
- no fallback to stale or unfiltered surfaces

If implementation pressure suggests another file is needed, stop and treat that as evidence of a new follow-up rather than widening this story.

=== FILE: 03_master_prompt.md ===
## Role
You are Codex acting as a narrowly-scoped implementation engineer for the US-AUTO automation pipeline.

## Goal
Implement US-AUTO-70 by making rerun-preflight in `automation/scripts/run_story.sh` recompute the effective filtered review surface for companion-filtered stories before it makes rerun-preflight decisions, and add committed regression coverage in `tests/test_run_story.py`.

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- any file not explicitly listed in Files Allowed To Change

## Atomic Task Isolation Contract
This story is the rerun-preflight half of a previously confirmed split. Do not re-open the execution-filtering half.

You must not:
- edit `automation/run_codex_task.sh`
- edit `tests/test_run_codex_task.py`
- generalize the work into a multi-stage reuse framework
- absorb broader review/gate/analyze changes
- add unrelated fixes because they appear nearby

If the required fix cannot be completed inside the allowed files, stop and fail closed rather than widening scope.

## Execution Gate
Before making changes, confirm all planned edits fit inside the allowed files and directly support rerun-preflight stable-review recomputation for companion-filtered stories.

If the repository state or current code suggests the fix requires a non-allowed file, do not proceed with a wider implementation. Keep the story atomic.

## Implementation Requirements
- Update `automation/scripts/run_story.sh` so rerun-preflight uses a recomputed effective filtered review surface for the companion-filtered path.
- Preserve existing behavior for non-companion-filtered stories.
- Preserve committed-HEAD and fail-closed workflow invariants.
- If the effective filtered surface cannot be derived deterministically, emit a fail-closed blocking error rather than silently continuing with the wrong surface.
- Keep the implementation narrow and deterministic.
- Add or update targeted tests in `tests/test_run_story.py` to cover:
  - positive companion-filtered rerun-preflight recomputation
  - preservation of existing behavior on unaffected paths
  - fail-closed behavior when recomputation input is invalid or missing

## Verification Requirements
Run only the minimum verification needed for this story, centered on:
- `pytest -q tests/test_run_story.py`

If there are directly relevant targeted test selectors for the new behavior, they may be used during iteration, but final verification must still include the file-level test run above.

## Output
Provide:
1. the implementation changes in the allowed files only
2. concise verification results for the required test command
3. a clear note if anything blocked completion under the atomic scope rules

Do not output plans for unrelated follow-ups unless the story cannot be completed within scope.

=== FILE: 04_review_checklist.md ===
## Scope Validation
HARD BLOCK / REJECT if any changed file is outside:
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`

HARD BLOCK / REJECT if any implementation change touches:
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`
- review/gate/analyze scripts
- registry files
- bundle files for other stories

APPROVE only if the diff stays fully inside the allowed pair and clearly targets rerun-preflight stable-review recomputation for the companion-filtered path.

## Functional Validation
HARD BLOCK / REJECT if rerun-preflight still evaluates an unadjusted or stale surface after companion filtering should have narrowed the effective review surface.

HARD BLOCK / REJECT if the implementation introduces fail-open fallback when recomputation inputs are missing, invalid, or ambiguous.

HARD BLOCK / REJECT if the change alters unrelated rerun behavior for non-companion-filtered stories without explicit narrow justification.

APPROVE only if:
- rerun-preflight uses a recomputed effective filtered review surface for the intended path
- unaffected paths remain stable
- failure behavior is deterministic and fail-closed

## Verification
HARD BLOCK / REJECT if `pytest -q tests/test_run_story.py` is not run and reported.

HARD BLOCK / REJECT if new or updated tests do not specifically prove the companion-filtered rerun-preflight path.

Final review outcome must be binary:
- APPROVE
- REJECT

No partial approval.

=== FILE: 05_followups.md ===
## Follow-Up Prompt Queue
- Revisit US-AUTO-69 only if US-AUTO-70 uncovers a still-residual coupling beyond rerun-preflight recomputation.
- Consider a later optimization story only after US-AUTO-70 lands and proves that the effective filtered review surface can be recomputed deterministically within `run_story.sh`.
- Do not open safe-reuse, telemetry, or UX follow-ups from this story unless a separate committed observation requires them.

## Iteration Notes
US-AUTO-70 is intentionally atomic and should remain so. If implementation pressure suggests changing `run_codex_task.sh` or any review-stage script, that is evidence of a new story, not permission to widen this one.

Completion of US-AUTO-70 is the explicit return condition recorded for the parked split line of US-AUTO-69.

=== FILE: 06_manual_actions.md ===
## Required Human Actions
1. Save this bundle pack as `automation/bundle_packs/US-AUTO-70.bundle.md`.
2. Run `automation/scripts/materialize_story_bundle.sh US-AUTO-70`.
3. Run `automation/scripts/validate_story_bundle.sh US-AUTO-70`.
4. Update the registry entry for US-AUTO-70 to reflect active bundle work if it is not already recorded.
5. Create a feature branch for US-AUTO-70 before implementation.
6. Commit the bundle artifacts before running the story.
7. Run `automation/scripts/run_story.sh US-AUTO-70`.
8. After implementation commit, use a fresh committed-head rerun if required by the workflow and then run `automation/scripts/analyze_story_run.sh US-AUTO-70` before any review-stage continuation.

## Completion Status
- Story selection: complete
- Atomicity check: complete; US-AUTO-70 is treated as the atomic rerun-preflight half of the prior split
- Bundle pack assembly: complete
- Sanity check against section contract and scope synchronization: complete
- Ready for materialize and validate: yes