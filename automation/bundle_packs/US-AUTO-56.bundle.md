# Story Bundle Pack
Story-ID: US-AUTO-56
Version: 1

=== FILE: 00_story.md ===
# Story ID and Title
US-AUTO-56 — Post-run stage-gate guidance for review eligibility and manual-finish continuation

## Objective
Add explicit, deterministic operator guidance immediately after post-run decision points so the workflow states whether review-stage commands are allowed, whether commit/discard is required first, and whether manual-finish continuation forbids another rerun.

## Scope
This story is limited to stage-gate guidance and operator messaging around the existing fail-closed workflow contract after `run_story.sh` and `analyze_story_run.sh`.

In scope:
- surface explicit review-eligibility guidance after run/analyze outcomes
- surface explicit commit/discard requirement when the working tree is dirty
- surface explicit rerun prohibition when manual-finish continuation is active
- keep guidance deterministic and aligned with existing workflow invariants
- add targeted tests for the new guidance text and decision framing

## Non-goals
- no new rerun-skip logic
- no new escalation threshold logic
- no new review-artifact reuse logic
- no new telemetry registry or analytics
- no changes to review, classify, or gate decision semantics
- no fail-open fallback behavior
- no broad UX rewrite of all scripts

## Dependencies
- US-AUTO-41 — canonical story-artifact handoff before run
- US-AUTO-44 — dirty-state preflight classification
- US-AUTO-46 — committed-HEAD review boundary enforcement
- US-AUTO-47 — rerun convergence boundary
- US-AUTO-52 — strict manual-finish continuation contract
- US-AUTO-55 — final-HEAD manual-finish review compliance for exact allowed continuation path

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_run_story.py`
- `tests/test_analyze_story_run.py`

## Current Code Reality
The fail-closed workflow contracts already exist, but operator guidance is still too implicit. The registry identifies the next active gap as operator-facing stage guidance after US-AUTO-55. Current behavior can block or redirect correctly, yet operators may still infer the wrong next command from partial output, especially around:
- when review-stage commands are actually allowed
- when dirty-tree state means commit/discard must happen before review
- when manual-finish continuation is active and rerun is forbidden

The pipeline correctness boundary is already implemented; the missing layer is explicit stage-aware guidance.

## Target Outcome
After `run_story.sh` and `analyze_story_run.sh`, the operator should receive deterministic stage-gate guidance that clearly answers:
- Is review-stage allowed now?
- Must the operator commit/discard first?
- Is rerun forbidden because manual-finish continuation is active?
- What is the cheapest safe next step?

This must remain fail-closed and must not relax any existing execution or review boundary.

## Atomic Task Isolation Contract
This story solves exactly one problem: stage-gate guidance after post-run decision points.

Hard isolation rules:
- do not introduce new workflow stages
- do not change review/gate eligibility semantics beyond messaging/explicit surfacing of existing rules
- do not add telemetry, caching, reuse, retry, or loop-control logic
- do not expand into bundle-pack workflow simplification
- do not modify unrelated scripts or tests outside the listed scope

If a change requires new enforcement behavior rather than explicit guidance of existing behavior, stop and leave it for a follow-up story.

## Risks
- wording drift could accidentally change operator interpretation of existing contracts
- tests may overfit exact strings instead of stable stage-gate meaning
- scope drift into rerun-control or review-boundary logic is a real risk and must be rejected

## Manual Actions
- update the registry row for US-AUTO-56 from `Planned` to `Bundle Ready` when the bundle is committed
- keep US-AUTO-57 as the next recommended implementation follow-up after US-AUTO-56
- after implementation, verify guidance output on both normal rerun path and manual-finish continuation path

## Acceptance Notes
Acceptance requires all of the following:
- `run_story.sh` or `analyze_story_run.sh` emits explicit stage-gate guidance for normal post-run outcomes
- dirty-tree states explicitly tell the operator that review-stage is not allowed until commit/discard resolves the tree
- manual-finish continuation explicitly tells the operator not to rerun again until manual finish is completed
- guidance is deterministic, fail-closed, and consistent with existing committed-HEAD / manual-finish contracts
- tests prove the guidance exists for the intended paths without broadening scope

=== FILE: 01_context_bundle.md ===
# Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_run_story.py`
- `tests/test_analyze_story_run.py`

## Current Code Reality
The epic registry marks US-AUTO-56 as the next recommended story after US-AUTO-55. The fail-closed workflow boundary is already stable:
- ordinary review after an implementation commit requires a fresh committed-head rerun
- `run -> commit -> review` is not a valid normal path
- manual-finish continuation is the only explicit exception after `blocked_non_converging_rerun`
- when manual-finish continuation is active, rerun must not happen again until manual finish is complete

The remaining gap is not policy correctness; it is explicit operator-facing stage guidance. Current outputs can still leave room for confusion about whether review-stage is allowed now, whether commit/discard must happen first, and whether rerun is forbidden under manual-finish continuation.

## Architectural Intent
Keep the pipeline fail-closed and deterministic while reducing operator ambiguity.

The story must:
- surface existing workflow invariants at the exact post-run decision points
- make the next safe step obvious
- make forbidden actions explicit
- avoid adding new orchestration or broad UX behavior

The guidance should act as a thin interpretation layer over existing rules, not as a new workflow engine.

## Risks
- accidental semantic changes disguised as messaging improvements
- expanding from stage guidance into loop prevention, retry budget, or telemetry
- inconsistent phrasing between `run_story.sh` and `analyze_story_run.sh`
- tests validating prose too loosely or too rigidly

## Acceptance Notes
A correct implementation keeps all existing boundaries intact and only makes them explicit:
- normal rerun/review path guidance remains committed-head first
- manual-finish continuation remains a narrow exception with rerun prohibition
- dirty tree remains a hard stop for review-stage eligibility until resolved
- no other scripts become part of scope

=== FILE: 02_file_scope.md ===
# Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_run_story.py`
- `tests/test_analyze_story_run.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/run_codex_task.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/story_change_ledger.jsonl`
- any bundle pack or active bundle for stories other than US-AUTO-56
- any test files other than `tests/test_run_story.py` and `tests/test_analyze_story_run.py`

## Scope Notes
Allowed change types:
- add deterministic stage-gate summary text
- add explicit “allowed next step” / “forbidden next step” guidance
- add targeted tests that verify stage-gate guidance for normal and manual-finish paths
- update the registry conservatively for US-AUTO-56 lifecycle status and next-action notes

Disallowed change types:
- changing review/gate decision logic
- introducing new files or registries
- adding rerun-skip, escalation, telemetry, reuse, or verification-selection behavior
- refactoring unrelated code paths for style only
- changing external contracts outside stage-gate guidance

=== FILE: 03_master_prompt.md ===
# Role
You are the implementation engineer for US-AUTO-56 working inside the fail-closed US-AUTO automation pipeline.

## Goal
Implement explicit post-run stage-gate guidance so operators can immediately see whether review-stage is allowed, whether commit/discard is required first, and whether manual-finish continuation forbids rerun.

## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_run_story.py`
- `tests/test_analyze_story_run.py`

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_run_story.py`
- `tests/test_analyze_story_run.py`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/run_codex_task.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/story_change_ledger.jsonl`
- any bundle pack or active bundle for stories other than US-AUTO-56
- any test files other than `tests/test_run_story.py` and `tests/test_analyze_story_run.py`

## Atomic Task Isolation Contract
This is a narrow guidance story, not a workflow redesign.

Hard rules:
- preserve all existing fail-closed boundaries
- do not add new stages or orchestration
- do not change committed-HEAD review semantics
- do not change manual-finish continuation semantics except to make them more explicit to the operator
- do not implement rerun-skip detection, loop caps, telemetry, reuse, or verification optimization
- if a desired change would alter policy rather than clarify existing policy, stop and leave it for a follow-up story

## Execution Gate
Before editing:
1. confirm the changed files remain within the allowed scope
2. confirm the story is still atomic: guidance only, no new workflow behavior
3. confirm the implementation remains fail-closed
4. reject any temptation to “also improve” adjacent pipeline stages

## Implementation Requirements
- add deterministic post-run guidance text at the right operator-facing decision points
- explicitly state when review-stage is allowed
- explicitly state when review-stage is blocked until commit/discard resolves dirty state
- explicitly state when manual-finish continuation forbids another rerun
- keep output aligned with existing workflow invariants already established by US-AUTO-41, US-AUTO-44, US-AUTO-46, US-AUTO-47, US-AUTO-52, and US-AUTO-55
- prefer compact, stage-aware wording over verbose prose
- keep behavior deterministic across repeated runs for the same state

## Verification Requirements
- update or add focused tests in:
  - `tests/test_run_story.py`
  - `tests/test_analyze_story_run.py`
- prove that guidance appears for:
  - a normal path where review-stage is allowed only after the correct committed-head rerun sequence
  - a dirty-tree path where commit/discard is required before review-stage
  - a manual-finish continuation path where rerun is explicitly forbidden until manual finish completes
- run only the minimal relevant test targets for this story unless existing tests clearly require a slightly wider local verification set

## Output
Deliver:
1. implementation changes only within allowed files
2. targeted tests proving the stage-gate guidance contract
3. conservative registry update for US-AUTO-56
4. no unrelated refactors
5. no additional follow-up implementation in the same story

=== FILE: 04_review_checklist.md ===
# Scope Validation
- APPROVE only if changed files are limited to the allowed scope
- REJECT if any review/gate/classify/AI-review script changed
- REJECT if any new file or telemetry artifact was introduced
- REJECT if the implementation adds rerun-skip, loop-cap, reuse, telemetry, or verification-selection behavior
- REJECT if the registry update claims more than bundle/implementation lifecycle progress for US-AUTO-56

## Functional Validation
- APPROVE only if stage-gate guidance is explicit and deterministic
- APPROVE only if output clearly distinguishes:
  - review-stage allowed
  - commit/discard required before review-stage
  - manual-finish continuation active and rerun forbidden
- REJECT if guidance weakens or contradicts existing fail-closed workflow contracts
- REJECT if the implementation changes policy instead of clarifying existing policy
- REJECT if manual-finish wording allows another rerun before manual finish is complete

## Verification
- APPROVE only if targeted automated tests cover the intended guidance states
- REJECT if tests are missing for dirty-tree review blocking
- REJECT if tests are missing for manual-finish rerun prohibition guidance
- REJECT if tests rely only on vague substring matches that do not prove the stage-gate meaning
- Final result must be binary: APPROVE or REJECT with no soft-pass language

=== FILE: 05_followups.md ===
# Follow-Up Prompt Queue
1. US-AUTO-57 — preflight rerun-skip detection
2. US-AUTO-31 — mandatory analyze gate before rerun or next phase
3. US-AUTO-58 — stage-loop cap and forced escalation threshold
4. US-AUTO-61 — workflow telemetry registry for run stages, blockers, manual interventions, and timings
5. US-AUTO-59 — failure-summary and operator decision UX

## Iteration Notes
- US-AUTO-56 must remain guidance-only.
- Any desire to stop unnecessary reruns belongs to US-AUTO-57, not this story.
- Any desire to make analyze a mandatory enforced checkpoint belongs to US-AUTO-31, not this story.
- Any desire to summarize the whole operator experience more broadly belongs to US-AUTO-59.
- Any durable workflow measurement belongs to US-AUTO-61 and follow-ups, not this story.

=== FILE: 06_manual_actions.md ===
# Required Human Actions
1. Save this bundle pack to `automation/bundle_packs/US-AUTO-56.bundle.md`.
2. Run `automation/scripts/materialize_story_bundle.sh US-AUTO-56`.
3. Run `automation/scripts/validate_story_bundle.sh US-AUTO-56`.
4. Update `docs/90_codex/epics/US-AUTO_REGISTRY.md` conservatively so US-AUTO-56 reflects bundle readiness / active work state and remains the current priority story until merged.
5. Create a feature branch for US-AUTO-56. Do not run automation on `main`.
6. Commit the bundle artifacts using the normal story-artifact handoff workflow.
7. Run `automation/scripts/run_story.sh US-AUTO-56`.
8. Run `automation/scripts/analyze_story_run.sh US-AUTO-56`.
9. Only proceed to review-stage commands if the resulting stage-gate guidance explicitly permits it.

## Completion Status
- Story selection completed: US-AUTO-56 chosen as the highest-priority next story with completed dependencies.
- Atomicity check completed: narrow guidance-only scope confirmed.
- Bundle sanity check completed: seven required files present with required headings and synchronized scope.
- Implementation status: not started.