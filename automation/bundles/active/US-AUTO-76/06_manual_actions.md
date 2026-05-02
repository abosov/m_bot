## Required Human Actions

Before implementation:

1. Confirm branch:

   `git branch --show-current`

   Expected:

   `feat/us-auto-76-governance-artifact-scope-semantics`

2. Confirm clean workspace except the new bundle pack if not yet committed:

   `git status --short`

3. Save this bundle pack to:

   `automation/bundle_packs/US-AUTO-76.bundle.md`

4. Materialize:

   `automation/scripts/materialize_story_bundle.sh US-AUTO-76`

5. Validate:

   `automation/scripts/validate_story_bundle.sh US-AUTO-76`

6. Open generated files in Cursor:

   `open -a "Cursor" automation/bundle_packs/US-AUTO-76.bundle.md automation/bundles/active/US-AUTO-76`

7. Review bundle diff:

   `git diff -- automation/bundle_packs/US-AUTO-76.bundle.md automation/bundles/active/US-AUTO-76`

8. Commit story artifacts before running the story:

   `automation/scripts/commit_story_artifacts.sh US-AUTO-76`

After implementation:

1. Run targeted tests:

   `python3 -m pytest tests/test_classify_review_story_run.py tests/test_review_gate_story_run.py`

2. Run broader review-stage tests if touched behavior requires it:

   `python3 -m pytest tests/test_ai_review_story_run.py tests/test_analyze_story_run.py tests/test_classify_review_story_run.py tests/test_review_gate_story_run.py tests/test_review_story_run.py`

3. Run story:

   `automation/scripts/run_story.sh US-AUTO-76`

4. Analyze latest run before review-stage commands.

5. Do not run review/gate commands against stale run artifacts after any commit.

6. If `automation/story_change_ledger.jsonl` is the only unintended dirty file before push or PR, discard it:

   `git restore automation/story_change_ledger.jsonl`

7. Before PR, confirm:

   `git status --short`

8. Create PR only after story workflow is resolved.

## Completion Status

US-AUTO-76 is complete only when:

- bundle materializes successfully;
- bundle validates successfully;
- story artifacts are committed;
- implementation and tests are committed;
- targeted tests pass;
- story workflow completes;
- analyze/review/classify/gate are resolved according to current pipeline rules;
- PR is opened, checked, merged, and branch cleanup is completed.

Do not proceed to US-AUTO-77 until US-AUTO-76 is merged or explicitly parked.
