
# US-AUTO-22: Follow-Ups
## Follow-Up Prompt Queue

Add a separate follow-up story for shell/script-level enforcement of Atomic Task Isolation if documentation alone proves insufficient.
Add separate follow-up prompts if review finds multiple independent wording or bundle-structure gaps; do not batch them into one continuation run.

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

## Findings To Address
- <paste exact finding>

## Follow-Up Intent
- Declare one exact sentence for the single finding being fixed before making changes.

## Out of Scope
- Any second review finding, any unrelated cleanup, and any shell/runtime enforcement work.

## Files Allowed To Change
- <list exact allowed files for the follow-up>

## Files Not Allowed To Change
- `automation/scripts/**`
- `tests/**`
- any files unrelated to the listed finding

## Rules
- keep patch minimal and scoped
- preserve architecture boundaries
- do not introduce new features beyond listed findings
- fix exactly one finding or one narrowly defined blocker in this prompt
- restate the exact one-sentence follow-up intent before edits
- if another issue is discovered, record it as a new follow-up instead of fixing it here
- if the finding cannot be resolved without a second independent change, stop and create a separate follow-up prompt

## Tests
- Record validation performed for the addressed finding.

## Output
Return:
1. addressed findings
2. changed files summary
3. validation results
4. residual risks
5. final diff
