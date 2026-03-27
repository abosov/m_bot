# File Scope

## Files Allowed To Change
- automation/scripts/run_story.sh
- tests/test_run_story.py

## Files Not Allowed To Change
- automation/scripts/analyze_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/commit_story_artifacts.sh
- automation/scripts/run_codex_task.sh
- any files under automation/runs/

## Scope Notes
- modify ONLY escalation validation block
- no refactoring outside validation
- no changes to unrelated logic
- no structural changes to pipeline

---

