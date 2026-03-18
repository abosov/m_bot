
# US-AUTO-22: Follow-Ups
## Follow-Up Prompt Queue

Add a separate follow-up story for shell/script-level enforcement of Atomic Task Isolation if documentation alone proves insufficient.
Add separate follow-up prompts if review finds multiple independent wording or bundle-structure gaps; do not batch them into one continuation run.
Each follow-up prompt must name exactly one target finding or blocker and must be rejected if it tries to carry more than one independently reviewable fix.
Follow-up mode is not an exception path around Atomic Task Isolation; do not use a follow-up prompt to absorb a second independently reviewable change.
If the follow-up prompt is missing intent, out-of-scope, file-boundary, follow-up-capture, or hard-stop details, stop and correct it before execution.

## Iteration Notes

This story intentionally stops at documentation and prompt-template updates.

Any runtime enforcement, gate changes, or allowed-files guard changes require a separate story.

## Follow-Up Prompt Template

# US-AUTO-22 FOLLOW-UP PROMPT 1 — <Fix/Adjustment>

## Role
You are the System Architect + Developer + QA + Security Reviewer for Zumbot.

## Context
- Base story bundle: `automation/bundles/active/US-AUTO-22/`
- Previous run output: `automation/output/<story-run-id>/`
- Review checklist: `automation/bundles/active/US-AUTO-22/04_review_checklist.md`

## Target
Address only the specific documented finding from the previous run without expanding scope.

## Follow-Up Target Finding
- <paste exact finding identifier or blocker label only once>

## Findings To Address
- <paste exact finding text for the single target only>

## Follow-Up Intent
- Declare one exact sentence for the single finding being fixed before making changes.

## Atomic Task Isolation Contract
- Atomic Task Isolation is a mandatory execution contract for this follow-up run.
- This prompt may address exactly one review finding or one narrowly defined blocker only.
- If required intent, out-of-scope, file-boundary, target-finding, follow-up-capture, or hard-stop details are missing, stop and refuse implementation until the follow-up prompt is corrected.
- If another independent issue appears, record it as a separate follow-up instead of fixing it here.
- Follow-up mode is not an exception path around this contract; do not batch a second independently reviewable fix into this run.

## Out of Scope
- Any second review finding, any unrelated cleanup, and any shell/runtime enforcement work.

## Files Allowed To Change
- <list exact allowed files for the follow-up>

## Files Not Allowed To Change
- `automation/scripts/**`
- `tests/**`
- any files unrelated to the listed finding

## Follow-Up Capture Rule
- If this fix reveals another independently reviewable issue, record it as a separate follow-up task and do not implement it in this run.
- Do not treat follow-up mode as permission to widen scope beyond the single target finding or blocker.

## Execution Gate
- Refuse implementation if this follow-up targets more than one finding or blocker.
- Refuse implementation if the target-finding label, intent, out-of-scope statement, allowed-file boundaries, forbidden-file boundaries, follow-up-capture rule, or hard-stop condition is missing or ambiguous.
- Refuse implementation if resolving the target would require a second independently reviewable change; stop and create another follow-up prompt instead.
- Refuse implementation if the prompt tries to use follow-up mode as an exception path around Atomic Task Isolation.

## Rules
- keep patch minimal and scoped
- preserve architecture boundaries
- do not introduce new features beyond listed findings
- fix exactly one finding or one narrowly defined blocker in this prompt
- restate the exact one-sentence follow-up intent before edits
- if another issue is discovered, record it as a new follow-up instead of fixing it here
- if the finding cannot be resolved without a second independent change, stop and create a separate follow-up prompt
- if this prompt targets more than one finding or blocker, stop and split it before implementation
- declare the exact one-sentence follow-up intent before edits and confirm no second finding is included in this run

## Tests
- Record validation performed for the addressed finding.

## Output
Return:
1. addressed findings
2. changed files summary
3. validation results
4. residual risks
5. final diff
