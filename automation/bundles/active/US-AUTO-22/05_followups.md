
# US-AUTO-22: Follow-Ups
## Follow-Up Prompt Queue

Add a separate follow-up story for shell/script-level enforcement of Atomic Task Isolation if documentation alone proves insufficient.

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
- if another issue is discovered, record it as a new follow-up instead of fixing it here

## Tests
- Record validation performed for the addressed finding.

## Output
Return:
1. addressed findings
2. changed files summary
3. validation results
4. residual risks
5. final diff

