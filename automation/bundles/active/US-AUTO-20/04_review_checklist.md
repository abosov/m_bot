# US-AUTO-20: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No backend/product files were changed
- [ ] No unrelated refactor or formatting-only edits were introduced
- [ ] Atomic Task Isolation remained explicit and enforced

## Functional Validation
- [ ] Latest valid stage is detected from existing run artifacts
- [ ] Exactly one next recommended action is printed
- [ ] Resume guidance fails closed on stale or inconsistent evidence
- [ ] Existing workflow stages remain reusable and explicit

## Verification
- [ ] Focused tests/validation commands are recorded
- [ ] Manual verification steps are recorded when needed
- [ ] Risks and follow-ups are captured before merge

