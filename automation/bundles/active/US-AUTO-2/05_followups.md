# US-AUTO-2: Follow-Ups

## Follow-Up Prompt Queue
- <No follow-ups yet>

## Iteration Notes
- <Review findings, accepted improvements, or deferred work>

## Follow-Up Prompt Template

```md
# US-AUTO-2 FOLLOW-UP PROMPT 1 — <Fix/Adjustment>

## ROLE
You are the System Architect + Developer + QA + Security Reviewer for Zumbot.

## CONTEXT
- Base story bundle: `automation/bundles/active/US-AUTO-2/`
- Previous run output: `automation/output/<story-run-id>/`
- Review checklist: `automation/bundles/active/US-AUTO-2/04_review_checklist.md`

## TARGET
<Single follow-up objective>

## FINDINGS TO ADDRESS
- <MERGE BLOCKER or approved MINOR IMPROVEMENT item>

## FILES ALLOWED TO CHANGE
- <path>

## FILES NOT ALLOWED TO CHANGE
- <path>

## RULES
- keep patch minimal and scoped
- preserve architecture boundaries
- do not introduce new features beyond listed findings

## TESTS
- `pytest <targeted test path>`

## OUTPUT FORMAT
Return:
1. addressed findings
2. changed files summary
3. test results
4. residual risks
5. final diff
```

## PR Description Template

```md
# US-AUTO-2 — Run story launcher by STORY_ID

## Summary
<What this PR changes in 2-4 lines>

## Story Context
- Story bundle: `automation/bundles/active/US-AUTO-2/`
- Objective: <objective>
- Non-goals: <key exclusions>

## Scope
- <Implemented item 1>
- <Implemented item 2>

## Files Changed
- <path>
- <path>

## Tests
- `pytest <targeted path>`: <pass/fail>

## Review Classification
- Merge blockers: <count/status>
- Minor improvements: <count/status>
- Follow-up stories created: <list or none>

## Risks / Notes
- <Known risk and mitigation>

## Manual Actions
- <Manual actions, if any>
```
