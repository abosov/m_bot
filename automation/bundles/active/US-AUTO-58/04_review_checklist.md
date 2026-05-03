## Scope Validation

Confirm the implementation stays within US-AUTO-58.

Confirm it does not implement the full US-AUTO-79 orchestrator.

Confirm it does not implement the full US-AUTO-80 decision packet UX beyond minimal required forced-decision output.

Confirm it does not weaken dirty-tree, stale-run, committed-HEAD, refresh evidence, classification, or gate safety contracts.

Confirm it does not modify unrelated business feature code.

Confirm registry status is not prematurely changed to Implemented unless this is explicitly part of the accepted repository workflow.

## Functional Validation

Verify loop cap behavior for repeated stage loops.

Verify that repeated run/rerun loops are stopped.

Verify that repeated refresh/review/classification/gate loops are stopped.

Verify that non-safety polish loops route to escalation or follow-up instead of more blind implementation changes.

Verify that explicit safety/source-of-truth blockers can still permit a narrow fix.

Verify the US-AUTO-60 no-Codex refresh path remains valid.

Verify analyze remains the safest decision authority.

Verify outputs contain stable markers that future automation can parse or rely on.

## Verification

Run targeted tests relevant to changed scripts.

Expected targeted tests may include:

    python3 -m pytest tests/test_analyze_story_run.py tests/test_run_story.py tests/test_refresh_review_evidence.py tests/test_review_story_run.py tests/test_classify_review_story_run.py tests/test_review_gate_story_run.py tests/test_review_pipeline_validation_contract.py

If AI review script behavior changes, also run:

    python3 -m pytest tests/test_ai_review_story_run.py tests/test_review_classification_script.py

If full pytest is run, report the full result exactly.

Review git status before review-stage commands.

Do not proceed to review/classify/gate with dirty tree.

## Regression Checks

Check that old accepted workflows still pass.

Check that a first rerun or first refresh is not blocked merely because a prior stage exists.

Check that after commit/amend, old AUTOMATION_RUN_DIR is still considered stale unless explicitly refreshed through the allowed no-Codex path.

Check that ledger-only dirtiness guidance remains intact.

Check that analyze output does not recommend a forbidden next step.

