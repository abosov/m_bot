# Story Bundle Pack
Story-ID: US-AUTO-69
Version: 1

=== FILE: 00_story.md ===
## Story ID and Title
US-AUTO-69 — Companion-artifact execution filtering for code-only stories

## Objective
Allow a code-only story run to complete when Codex emits companion registry or documentation edits that are outside the intended implementation scope, but only by filtering those companion artifacts out of the execution review surface rather than widening the story scope.

## Scope
This story is limited to the execution-layer handling of companion artifacts for code-only stories.
It may:
- detect companion-artifact paths produced during Codex execution
- exclude those paths from the effective implementation review surface used by the execution flow
- preserve fail-closed behavior when non-companion out-of-scope changes remain
- add targeted tests for the new execution behavior

This story must not redesign the broader scope-validation model, the registry workflow, or review-stage semantics.

## Non-goals
- Do not make documentation or registry files generally allowed for code-only stories
- Do not change story bundle validation rules
- Do not alter manual-finish continuation logic
- Do not introduce fail-open scope handling
- Do not add telemetry, operator UX redesign, or reuse logic
- Do not mutate the durable registry automatically as part of runtime filtering

## Dependencies
- US-AUTO-41 — story-artifact commit handoff before run
- US-AUTO-44 — materialization preflight and operator handoff
- US-AUTO-46 — committed-HEAD review boundary enforcement
- US-AUTO-49 — runtime scope validation ignores committed active-story bundle artifacts
- US-AUTO-50 — deterministic structured AI review output contract
- US-AUTO-56 — post-run stage-gate guidance
- US-AUTO-57 — blocked predecessor whose execution blocker is being isolated by this follow-up :contentReference[oaicite:0]{index=0}

## Source of Truth
Primary source of truth for prioritization, dependency context, and current status:
- `docs/90_codex/epics/US-AUTO_REGISTRY.md` :contentReference[oaicite:1]{index=1}

Implementation source of truth for this story:
- runtime execution path in `automation/scripts/run_story.sh`
- Codex execution output shaping in `automation/run_codex_task.sh`
- related focused tests in `tests/test_run_story.py` and `tests/test_run_codex_task.py`

## Current Code Reality
The registry records US-AUTO-57 as blocked even though implementation and tests were completed, because Codex execution added a companion edit to `docs/90_codex/epics/US-AUTO_REGISTRY.md`, which fell outside the code-only story scope and caused the run to fail during scope validation. The registry explicitly identifies this as an execution-layer blocker and points to US-AUTO-69 as the narrow follow-up to resolve it. :contentReference[oaicite:2]{index=2}

The current workflow already distinguishes committed story artifacts from implementation delta, enforces committed-HEAD boundaries, and prefers fail-closed behavior. The missing piece is a narrow execution-layer rule that recognizes a small class of companion artifacts for code-only stories and removes them from the effective review surface without silently allowing arbitrary extra edits. :contentReference[oaicite:3]{index=3}

## Target Outcome
After this story:
- a code-only story run no longer fails solely because Codex also emitted a recognized companion registry or documentation edit
- those companion paths are excluded from the effective execution review surface
- the workflow still hard-fails when any remaining out-of-scope non-companion file is present
- the result is deterministic and review-surface fidelity is preserved for the actual code change set
- US-AUTO-57’s execution blocker becomes removable without weakening the pipeline’s fail-closed posture

## Atomic Task Isolation Contract
This story is atomic.
It solves exactly one problem: execution-layer filtering of recognized companion artifacts for code-only stories.

Allowed change categories:
- companion-artifact path classification logic
- effective changed-files filtering for execution review surface
- deterministic error/allow behavior for companion vs non-companion extra edits
- tightly scoped tests

Forbidden expansions:
- no new workflow phases
- no registry redesign
- no generalized multi-category scope policy engine
- no review-stage or analyze-stage redesign
- no documentation automation logic

If implementation pressure suggests broader policy changes, stop and reject rather than expanding scope.

## Risks
- Risk of accidental fail-open handling if companion filtering is too broad
- Risk of drift between filtered changed-files surface and diff.patch surface
- Risk of masking real out-of-scope edits if path classification is ambiguous
- Risk of regression in existing strict scope-validation behavior for non-companion files

## Manual Actions
- Update the registry entry for US-AUTO-69 from `Planned` to `Bundle Drafted` when the bundle is materialized and committed
- Keep US-AUTO-57 as `Blocked` until US-AUTO-69 is implemented, rerun, reviewed, and merged
- After implementation, reassess whether US-AUTO-57 should move from blocked to resumed or implemented based on committed evidence
- Use the standard bundle-first workflow described in `06_manual_actions.md`

## Acceptance Notes
Acceptance requires all of the following:
- code-only execution treats recognized companion artifact paths as filtered, not as allowed implementation scope
- at least one focused test proves that a recognized companion registry/doc path does not fail the run by itself
- at least one focused test proves that a non-companion out-of-scope path still hard-fails
- if both a recognized companion path and a real out-of-scope path appear together, the run still hard-fails
- effective changed-files and any related execution diff surface remain consistent with the filtering rule
- no unrelated files or stages are changed

=== FILE: 01_context_bundle.md ===
## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md` is the durable portfolio source of truth for story priority, status, and dependencies. It lists US-AUTO-69 as the next recommended story and explains that US-AUTO-57 is blocked by a companion-artifact execution defect. :contentReference[oaicite:4]{index=4}
- Runtime behavior must remain aligned with the established fail-closed execution pipeline already documented in the registry’s current epic state and workflow observations. :contentReference[oaicite:5]{index=5}

## Current Code Reality
The registry states that the remaining work after US-AUTO-56 is about cycle-cost reduction and stronger workflow decisions rather than missing fail-closed contracts. US-AUTO-57 attempted rerun-skip detection but became blocked because Codex introduced a companion registry diff that was outside scope, making the success boundary unreachable through `run_story.sh`. US-AUTO-69 exists specifically to fix that execution-layer defect without broadening the story’s allowed scope. :contentReference[oaicite:6]{index=6}

Existing pipeline guarantees already include:
- explicit handoff before run
- preflight dirty-state classification
- committed-HEAD review boundary enforcement
- exclusion of committed active-story bundle artifacts from runtime scope validation
- deterministic review evidence contracts
These guarantees should remain intact. :contentReference[oaicite:7]{index=7}

## Architectural Intent
The correct fix is a narrow execution-layer filter for a recognized class of companion artifacts on code-only stories.
Architectural intent:
- preserve fail-closed behavior
- preserve deterministic review-surface fidelity
- do not silently widen allowed story scope
- keep the distinction between actual implementation delta and companion artifacts
- make the execution flow cheaper and less fragile only where the extra diff is known to be non-implementation noise

The system should treat companion artifacts as excluded from the effective implementation review surface, not as ordinary allowed edits.

## Risks
Primary risks:
- over-classifying companion paths and hiding true scope violations
- under-classifying and leaving US-AUTO-57 blocked
- creating inconsistency between filtered changed-files output and execution diff output
- accidental spread into broader validation, retry, UX, or orchestration work

Mitigation:
- keep path classification explicit and minimal
- add binary tests for companion-only, mixed, and non-companion cases
- keep filtering confined to the execution path and its immediate evidence outputs

## Acceptance Notes
The story is acceptable only if:
- recognized companion paths are filtered deterministically
- non-companion out-of-scope edits still reject
- mixed cases still reject
- the fix is limited to the execution layer for code-only stories
- the bundle scope and implementation scope remain perfectly aligned

=== FILE: 02_file_scope.md ===
## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `tests/test_run_story.py`
- `tests/test_run_codex_task.py`

## Files Not Allowed To Change
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/story_change_ledger.jsonl`
- any file under `automation/bundles/active/` except through normal materialization before implementation
- any file under `automation/bundle_packs/` except this bundle before materialization
- any unrelated test file not listed above

## Scope Notes
Allowed change types:
- add a narrow companion-artifact classifier or predicate
- filter companion artifact paths from the effective execution review surface for code-only stories
- align any execution diff/evidence generation needed so filtered surfaces stay deterministic
- add focused tests covering companion-only allow, non-companion reject, and mixed-case reject

Hard boundaries:
- do not generalize into a universal path-policy framework
- do not modify review-stage contracts
- do not change registry content as part of runtime logic
- do not introduce telemetry, new CLI phases, or operator UX redesign
- do not relax fail-closed behavior for ambiguous or unknown paths

If implementation requires files outside this list, reject and spin a follow-up instead of expanding scope.

=== FILE: 03_master_prompt.md ===
## Role
You are the implementation engineer for a fail-closed automation pipeline. Work narrowly, preserve invariants, and do not broaden policy beyond the exact defect described here.

## Goal
Implement a narrow execution-layer fix so that code-only stories do not fail solely because Codex emitted a recognized companion registry or documentation edit outside the intended implementation scope. Those companion artifacts must be filtered out of the effective execution review surface, while all real out-of-scope edits continue to hard-fail.

## Source of Truth
Use these sources of truth:
- `docs/90_codex/epics/US-AUTO_REGISTRY.md` for story intent, status context, and dependency framing :contentReference[oaicite:8]{index=8}
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `tests/test_run_story.py`
- `tests/test_run_codex_task.py`

Registry facts relevant to this story:
- US-AUTO-57 is blocked by a companion-artifact diff added to `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- US-AUTO-69 is the designated follow-up to resolve that blocker narrowly at the execution layer
- the epic’s remaining gaps are optimization and workflow clarity problems, not justification for fail-open behavior :contentReference[oaicite:9]{index=9}

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `tests/test_run_story.py`
- `tests/test_run_codex_task.py`

## Files Not Allowed To Change
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/story_change_ledger.jsonl`
- any unrelated production or test file not explicitly listed as allowed

## Atomic Task Isolation Contract
You must solve one problem only:
execution filtering of recognized companion artifacts for code-only stories.

You must not:
- redesign scope validation broadly
- change review-stage semantics
- alter registry workflow
- add telemetry or UX layers
- create fallback behavior that silently allows unknown extra edits

Treat ambiguity as reject, not as permission to expand logic.

## Execution Gate
Hard-stop rules:
- if the change seems to require widening allowed scope, stop
- if unknown extra paths cannot be deterministically classified as companion artifacts, keep reject behavior
- if filtering changed-files would diverge from the execution diff surface, fix the inconsistency inside allowed files or stop
- do not touch any file outside the allowed list
- do not auto-edit the registry

The desired behavior is fail-closed:
- recognized companion-only extra paths: filtered
- any remaining non-companion out-of-scope path: reject
- mixed companion + non-companion: reject
- ambiguous classification: reject

## Implementation Requirements
Implement only the minimal logic needed to satisfy the story:
1. Add or refine explicit companion-artifact path recognition for code-only story execution.
2. Ensure those recognized companion paths are removed from the effective implementation review surface used by execution-stage scope decisions.
3. Keep all unknown or non-companion extra paths as hard failures.
4. Ensure any relevant execution evidence or diff surface exposed by the allowed files remains consistent with the filtered changed-files surface.
5. Add focused regression tests for:
   - companion-only registry/doc edit does not fail
   - non-companion out-of-scope path still fails
   - mixed companion + non-companion still fails
   - deterministic behavior when no companion artifact is present

Do not add generic abstractions unless they are the smallest clean way to express the exact classifier/filter.

## Verification Requirements
Run only the minimum targeted verification needed for this story:
- `pytest -q tests/test_run_story.py`
- `pytest -q tests/test_run_codex_task.py`

If a smaller targeted subset is clearly sufficient during development, that is acceptable, but final verification must cover both listed test files.

## Output
Produce:
- the minimal code changes within allowed files
- focused tests proving the binary behavior above
- no unrelated refactors
- no registry edits
- no explanatory prose in code comments beyond what is necessary for maintainability

=== FILE: 04_review_checklist.md ===
## Scope Validation
APPROVE only if:
- changed files are limited to the four allowed files
- the implementation remains strictly about companion-artifact execution filtering for code-only stories
- no review-stage, analyze-stage, registry, telemetry, or UX logic was changed
- no scope widening was introduced

REJECT if:
- any unlisted file changed
- the implementation broadens into general scope-policy redesign
- registry mutation or registry auto-handling was added
- the story solves more than the execution-filtering defect

## Functional Validation
APPROVE only if:
- recognized companion registry/doc edits are filtered from the effective execution review surface
- a code-only run no longer fails solely because of those recognized companion edits
- non-companion out-of-scope edits still fail hard
- mixed companion and non-companion extra edits still fail hard
- behavior is deterministic and fail-closed for ambiguous cases

REJECT if:
- companion artifacts are treated as generally allowed scope
- unknown paths are silently ignored
- mixed cases pass
- filtering affects unrelated workflow phases
- changed-files and execution diff surface become inconsistent

## Verification
Required evidence:
- passing targeted tests in `tests/test_run_story.py`
- passing targeted tests in `tests/test_run_codex_task.py`

HARD BLOCK:
- REJECT if tests were not run
- REJECT if assertions do not cover companion-only allow, non-companion reject, and mixed-case reject
- REJECT if the implementation relies on manual operator steps instead of deterministic code behavior

Binary review result:
- APPROVE
- REJECT

=== FILE: 05_followups.md ===
## Follow-Up Prompt Queue
1. Reassess US-AUTO-57 after US-AUTO-69 merges and determine whether the parked implementation can now pass the normal execution boundary without manual workaround.
2. US-AUTO-31 — mandatory analyze gate before rerun or next phase.
3. US-AUTO-58 — stage-loop cap and forced escalation threshold.
4. Consider a future narrow story only if needed for a configurable companion-artifact allowlist source; do not add that work here.

## Iteration Notes
- This story was intentionally selected because the registry marks it as the next recommended story and because US-AUTO-57 is blocked by a single execution-layer defect rather than a broad architectural gap. :contentReference[oaicite:10]{index=10}
- Keep this follow-up narrow. Do not combine it with analyze gating, telemetry, failure-summary UX, or broader verification optimization.
- If implementation reveals that companion artifacts need separate policy for docs-only or mixed-scope stories, create a new follow-up instead of expanding US-AUTO-69.
- After merge, the registry should be updated conservatively based on committed evidence: US-AUTO-69 can move to Implemented only after run/test/review proof exists; US-AUTO-57 should remain blocked until its downstream status is actually revalidated.

=== FILE: 06_manual_actions.md ===
## Required Human Actions
1. Save this bundle pack to `automation/bundle_packs/US-AUTO-69.bundle.md`.
2. Materialize the story bundle:
   - `automation/scripts/materialize_story_bundle.sh US-AUTO-69`
3. Validate the materialized bundle:
   - `automation/scripts/validate_story_bundle.sh US-AUTO-69`
4. Update the registry conservatively to reflect bundle readiness for US-AUTO-69 and keep US-AUTO-57 blocked until evidence changes. Source registry: `docs/90_codex/epics/US-AUTO_REGISTRY.md` :contentReference[oaicite:11]{index=11}
5. Create a feature branch for the story. Do not run automation on `main`.
6. Commit the bundle artifacts using the normal story-artifact handoff flow.
7. Run the story:
   - `automation/scripts/run_story.sh US-AUTO-69`
8. After the run completes, analyze the latest run before any further phase:
   - `automation/scripts/analyze_story_run.sh US-AUTO-69`
9. Only after committed implementation and a fresh rerun boundary are satisfied, continue into the ordinary review path according to current pipeline rules.

## Completion Status
- Bundle selected: complete
- Bundle drafted: complete
- Materialize: pending human action
- Validate: pending human action
- Registry update: pending human action
- Branch creation: pending human action
- Story-artifact commit handoff: pending human action
- Implementation run: pending human action
- Run analysis: pending human action
- Review and merge: pending human action