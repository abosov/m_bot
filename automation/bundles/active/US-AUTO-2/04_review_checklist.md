# US-AUTO-2: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] Non-goals remain untouched
- [ ] No unrelated refactor or formatting-only edits

## Architecture / Source of Truth
- [ ] Source-of-truth docs are listed and followed
- [ ] Architecture boundaries remain intact
- [ ] Docs/process updates are included when required

## Verification
- [ ] Targeted tests/validation commands are recorded
- [ ] Manual verification steps are recorded when needed
- [ ] Risks and follow-ups are captured before merge

## Review Prompt Seed

```md
# US-AUTO-2 REVIEW PROMPT — Implementation Review

## ROLE
You are the Reviewer (Architect + QA + Security) for Zumbot.

## REVIEW INPUTS
- Story bundle: `automation/bundles/active/US-AUTO-2/`
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
```
