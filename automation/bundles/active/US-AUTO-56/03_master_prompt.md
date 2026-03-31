## Role
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

