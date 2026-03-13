# US-AUTO-3: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `automation/run_codex_task.sh`
- `automation/scripts/run_story.sh`

## Current Code Reality
- `automation/run_codex_task.sh` already creates per-run artifact directories under `automation/runs/<STORY_ID>/<RUN_ID>/`
- Existing run artifacts already include review-oriented files such as `review_bundle.md`, `chatgpt_review_prompt.md`, `diff.patch`, `changed_files.txt`, and `pytest.txt`
- Review is still performed manually after the run
- There is no script that resolves the latest run for a story and standardizes how review should be started

## Target Architecture
- Add a thin review launcher that accepts `STORY_ID`
- The launcher resolves the latest run directory for that story
- The launcher checks that required review artifacts exist
- The launcher prints a clear review-oriented summary and paths for the operator
- Existing artifact generation remains owned by `automation/run_codex_task.sh`

## Risks
- Re-implementing artifact generation logic instead of reusing existing outputs
- Picking the wrong run if latest-run resolution is fragile
- Overcomplicating the review launcher instead of keeping it as a thin wrapper
- Weak error messages could make missing-artifact cases confusing

## Acceptance Notes
- The review launcher succeeds for a story that already has at least one run
- The review launcher fails clearly when no run exists for the story
- The review launcher fails clearly when required review artifacts are missing
- Manual validation should include at least one success case and one failure case
