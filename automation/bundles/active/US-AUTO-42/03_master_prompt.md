# US-AUTO-42 PROMPT 1 — Fail-Closed Escalation Resolution

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Story
US-AUTO-42 — Enforce fail-closed escalation resolution.

## Goal
Implement a narrow governance hardening fix so `automation/scripts/run_story.sh` fails closed whenever escalation resolution input is malformed, missing, empty, or unknown, instead of allowing execution to continue.

## Source of Truth
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-28.bundle.md`

## Intent
Intent: enforce fail-closed escalation resolution parsing in `automation/scripts/run_story.sh` and add focused regression coverage for invalid `resolution_action` inputs.

## Out of Scope
Out of scope: escalation UX redesign; escalation schema redesign; changes to escalation producers; `AUTOMATION_RUNS_ROOT`; review/gate reuse; AI review failure handling; zone budgets; targeted test strategy work; any non-escalation governance cleanup.

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-42.bundle.md`
- `automation/bundles/active/US-AUTO-42/**`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/escalate_story.sh`
- `automation/scripts/story_change_ledger.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `scripts/migrations/**`

## Atomic Task Isolation Contract
Atomic Task Isolation is a mandatory contract for this run.

You must declare the one-sentence task intent before making changes.

You must implement exactly one narrow defect fix:
- invalid escalation resolution input in `run_story.sh` must fail closed.

You must not treat this prompt as permission to redesign escalation flow or fix adjacent governance issues.

If you discover any additional issue that is not strictly required to make invalid `resolution_action` fail closed, you must stop, leave the issue untouched, and capture it as a follow-up.

Follow-up prompts are not an exception path around Atomic Task Isolation.

## Execution Gate
Before editing files, verify that this prompt is atomic, sufficiently specified, and limited to one defect. If it is not, stop instead of proceeding.

Hard stop immediately if any required code change would:
- touch a forbidden file,
- solve more than the invalid-resolution defect,
- require producer-side escalation artifact changes,
- require redesigning operator UX or downstream review/gate behavior.

## Implementation Requirements
1. Inspect the current escalation resolution branch in `automation/scripts/run_story.sh`.
2. Remove any fail-open continuation path for invalid resolution input.
3. Treat each of the following as a deterministic failure condition:
   - missing required escalation artifact when resolution is being consumed,
   - malformed JSON,
   - missing `resolution_action`,
   - empty `resolution_action`,
   - whitespace-only `resolution_action`,
   - unknown `resolution_action`.
4. Ensure the operator-facing message identifies the invalid resolution state and tells the operator to fix the escalation artifact rather than rerun blindly.
5. Add focused regression tests in `tests/test_run_story.py` that prove execution does not continue for invalid cases.
6. Update docs only where needed to describe the fail-closed escalation resolution contract.
7. Keep the patch minimal and localized.

## Verification Requirements
- Run the focused `tests/test_run_story.py` coverage relevant to escalation resolution.
- Confirm at least one invalid-input case is blocked with deterministic stderr guidance.
- Confirm no unrelated scripts were changed.

## Follow-Up Capture Rule
If you encounter any of the following, do not fix them here; capture them as follow-ups instead:
- broader escalation policy changes,
- artifact schema redesign,
- run-dir provenance redesign,
- review/gate coupling changes,
- unrelated test-suite restructuring.

## Output
Make the required code, test, and documentation changes directly in the repository.

The result must:
- make invalid escalation resolution input fail closed;
- add focused regression coverage for malformed, missing, empty, whitespace-only, and unknown `resolution_action` values;
- keep the implementation tightly scoped to US-AUTO-42;
- avoid changes to forbidden files;
- update only the narrowest necessary documentation.

