# US-AUTO-22: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] `03_master_prompt.md` does not under-declare bundle files legitimately in scope for this story
- [ ] Source-of-truth files are complete and resolved
- [ ] No unrelated refactor or formatting-only edits

## Functional Validation
- [ ] Bundle materializes into all seven required files
- [ ] Validation blocks unresolved placeholders and incomplete structure
- [ ] Story remains documentation/prompt-template only

## Architecture / Source of Truth
- [ ] Source-of-truth docs are listed and followed
- [ ] Architecture boundaries remain intact
- [ ] Atomic Task Isolation is expressed consistently across docs and templates

## Verification
- [ ] Validation commands are recorded
- [ ] Manual verification steps are recorded when needed
- [ ] Risks and follow-ups are captured before merge

## Review Prompt Seed


# US-AUTO-22 REVIEW PROMPT — Implementation Review

## Role
You are the Reviewer (Architect + QA + Security) for Zumbot.

## Review Inputs
- Story bundle: `automation/bundles/active/US-AUTO-22/`
- Code diff: `<git diff against branch>`
- Test evidence: `bundle validation and manual doc review`
- Classification rules: `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`

## Review Task
1. Validate scope against allowed/forbidden files.
2. Validate architecture and source-of-truth compliance.
3. Validate the story remains documentation-only.
4. Classify each finding:
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

Include the final recommendation as an exact standalone line:
`MERGE RECOMMENDATION: approve`
or
`MERGE RECOMMENDATION: reject`

