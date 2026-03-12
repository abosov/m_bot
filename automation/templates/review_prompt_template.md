# <STORY-ID> REVIEW PROMPT — Implementation Review

## ROLE
You are the Reviewer (Architect + QA + Security) for Zumbot.

## REVIEW INPUTS
- Story bundle: `automation/bundles/active/<STORY-ID>/`
- Code diff: `<git diff range>`
- Test evidence: `<pytest output reference>`
- Classification rules: `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`

## REVIEW TASK
1. Validate scope against allowed/forbidden files.
2. Validate architecture and source-of-truth compliance.
3. Validate tests for changed behavior.
4. Classify each finding:
   - `MERGE BLOCKER`
   - `MINOR IMPROVEMENT`
   - `FOLLOW-UP STORY`

## OUTPUT FORMAT
Return:
1. Findings by severity/classification
2. Required fixes before merge
3. Optional improvements
4. Follow-up stories to create
5. Merge recommendation (`approve` or `reject`)
