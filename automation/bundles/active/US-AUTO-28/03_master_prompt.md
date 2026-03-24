US-AUTO-28 PROMPT 2 — Fix fail-open escalation resolution handling

## Role

You are the Bash Automation Developer, QA Engineer, and Workflow Contract Enforcer for the Zumbot US-AUTO pipeline.

## Story

- Story ID: US-AUTO-28
- Title: Escalation gate for repeated reject stagnation

## Goal

Fix exactly one merge blocker from the latest review: `automation/scripts/run_story.sh` must fail closed when a resolved escalation artifact contains a missing, empty, or unexpected `resolution_action`.

## Source Context

Latest review rejected merge because `enforce_escalation_resolution()` currently allows ordinary automation to continue when `escalation_result.json` has:
- `escalation_required: true`
- `status: resolved`
- invalid or missing `resolution_action`

This violates the documented fail-closed governance contract.

## Scope

In scope:
- fix fail-open behavior in `automation/scripts/run_story.sh`
- add the minimum targeted test coverage in `tests/test_run_story.py` needed to prove fail-closed handling for malformed `resolution_action`

Out of scope:
- `AUTOMATION_RUNS_ROOT` handling
- validation changes in `automation/scripts/escalate_story.sh`
- broader escalation artifact schema redesign
- docs changes unless strictly necessary for consistency with implemented behavior
- any new follow-up stories
- any unrelated refactors

## Files Allowed To Change

- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`

## Files Not Allowed To Change

- `automation/scripts/escalate_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `tests/test_escalate_story.py`
- docs files
- bundle files
- any unrelated automation or product code

## Required Behavior

Update `enforce_escalation_resolution()` so that:

- if escalation is unresolved and pending, ordinary continuation is blocked as before
- if escalation is resolved with a valid action, behavior remains deterministic
- if `resolution_action` is missing, empty, or not one of the explicitly supported values, the script must fail closed
- there must be no silent success path for malformed resolved escalation artifacts

Supported actions must be handled explicitly and deterministically.
Any unknown value must produce an error and block continuation.

## Testing Requirement

Add only the minimum targeted tests needed in `tests/test_run_story.py` to cover:
- malformed `resolution_action` is rejected
- missing `resolution_action` is rejected
- a valid resolved action still behaves as expected for the currently implemented contract

Keep tests narrow and local to this defect.

## Atomic Task Isolation Contract

Intent:
- fix the single fail-open defect identified by review in `run_story.sh`

Do not:
- fix the other review findings in this iteration
- widen the patch to neighboring scripts
- add speculative improvements

If you notice adjacent issues, do not implement them. Leave them untouched.

## Output

Produce:
1. the code change in `automation/scripts/run_story.sh`
2. the minimal targeted test updates in `tests/test_run_story.py`
3. no unrelated edits

## Validation

Run only the smallest relevant targeted test command first for `tests/test_run_story.py`, then stop.