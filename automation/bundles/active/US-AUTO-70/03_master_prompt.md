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

