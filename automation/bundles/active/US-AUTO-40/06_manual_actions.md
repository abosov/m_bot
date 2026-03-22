# Manual Actions — US-AUTO-40

## Before run

1. Ensure brch is correct:
   - `feat/us-auto-40-review-artifact-fidelity`

2. Ensure working tree is clean:
   - run `git status --short`

3. Confirm active bundle exists and required files are populated:
   - `00_story.md`
   - `01_context_bundle.md`
   - `02_file_scope.md`
   - `03_master_prompt.md`
   - `04_review_checklist.md`
   - `05_followups.md`
   - `06_manual_actions.md`

4. Validate bundle before execution.

## Run

Execute the story through the normal story runner for US-AUTO-40.

## Immediately after run

1. Check working tree:
   - `git status --short`

2. If the only dirty file is:
   - `automation/story_change_ledger.jsonl`

   restore it immediately before reviewing anything else.

3. Inspect the implementation diff and confirm it remains within intended scope.

4. Run targeted tests for touched review / gate workflow files.

## Before PR

1. Re-read the implemented contract.
2. Confirm docs were updated.
3. Confirm tests cover both:
   - faithful artifact approve path;
   - stale or mismatching artifact reject path.

## Review / gate expectation

The operator should expect stale or incomplete review artifacts to be rejected once the story is implemented.

If rejection happens because artifacts drifted from HEAD, the correct remediation is to refresh the review inputs so they faithfully reflect the actual branch diff.
