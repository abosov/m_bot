# US-AUTO-28 PROMPT 2 — Fix fail-open escalation resolution handling

## Goal
Fix exactly one merge blocker from the latest review: `automation/scripts/run_story.sh` must fail closed when a resolved escalation artifact contains a missing, empty, or unexpected `resolution_action`.

## Role
You are the Bash Automation Developer, QA Engineer, and Workflow Contract Enforcer for the Zumbot US-AUTO pipeline.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- latest review artifacts for `US-AUTO-28`
- current scripts and tests for run/review/gate/analyze flow

## Files Allowed To Change
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_review_gate_story_run.py`

## Files Not Allowed To Change
- `automation/scripts/escalate_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_escalate_story.py`
- docs files
- bundle files other than this prompt as required for execution
- any unrelated automation or product code

## Output
Produce only:
1. the code change in `automation/scripts/run_story.sh`
2. the minimal targeted test updates in `tests/test_run_story.py`
3. no unrelated edits

Additional requirements:
- if escalation is unresolved and pending, ordinary continuation remains blocked as before
- if escalation is resolved with a valid action, behavior remains deterministic
- if `resolution_action` is missing, empty, or not one of the explicitly supported values, the script must fail closed
- there must be no silent success path for malformed resolved escalation artifacts

Keep the patch narrow. Do not fix:
- `AUTOMATION_RUNS_ROOT`
- `escalate_story.sh`
- broader escalation artifact validation
- docs updates unless strictly required by tests for this exact defect