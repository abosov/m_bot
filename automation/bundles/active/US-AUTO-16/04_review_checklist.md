# US-AUTO-16: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] Source-of-truth files are complete and resolved
- [ ] No unrelated refactor or formatting-only edits

## Functional Validation
- [ ] A single review gate entrypoint script exists
- [ ] The gate runs AI review and review classification for the latest story run
- [ ] The gate writes a machine-readable result artifact with explicit final decision
- [ ] The gate exits non-zero on reject or invalid/missing decision
- [ ] Existing review artifacts remain available for manual inspection

## Architecture / Source of Truth
- [ ] Source-of-truth docs are listed and followed
- [ ] Architecture boundaries remain intact
- [ ] Finalize/merge integration is not introduced in this story

## Verification
- [ ] Targeted commands/validation steps are recorded
- [ ] Manual verification steps are recorded when needed
- [ ] Risks and follow-ups are captured before merge

## Review Prompt Seed

```md
# US-AUTO-16 REVIEW PROMPT — Implementation Review

## Role
You are the Reviewer (Architect + QA + Security) for Zumbot.

## Review Inputs
- Story bundle: `automation/bundles/active/US-AUTO-16/`
- Code diff: `<RUN ARTIFACT>`
- Test evidence: `<RUN ARTIFACT>`
- Classification rules: `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`

## Review Task
1. Validate scope against allowed/forbidden files.
2. Validate architecture and source-of-truth compliance.
3. Validate tests for changed behavi.
4. Validate that gate output is stable and fail-closed.
5. Classify each finding:
   - `MERGE BLOCKER`
   - `MINOR IMPROVEMENT`
   - `FOLLOW-UP STORY`

## Output
Return:
1. Findings by severity/classification
2. Required fixes before merge
3. Optional improvements
4. Follow-up stories to create
5. Merge recommendation (`approve` or `reject`)


