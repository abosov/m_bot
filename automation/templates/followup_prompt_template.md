# <STORY-ID> FOLLOW-UP PROMPT <N> — <Fix/Adjustment>

## ROLE
You are the System Architect + Developer + QA + Security Reviewer for Zumbot.

## CONTEXT
- Base story bundle: `automation/bundles/active/<STORY-ID>/`
- Previous run output: `automation/output/<story-run-id>/`
- Review checklist: `automation/bundles/active/<STORY-ID>/04_review_checklist.md`

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
