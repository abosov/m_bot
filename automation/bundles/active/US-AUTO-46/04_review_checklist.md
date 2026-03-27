# US-AUTO-46: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No runner redesign was introduced
- [ ] No auto-commit behavior was introduced
- [ ] No escalation-policy changes were bundled into this story
- [ ] No unrelated operator UX cleanup was included

## Functional Validation
- [ ] Review is blocked when the primary checkout has relevant uncommitted changes
- [ ] Review proceeds normally when the checkout is clean
- [ ] Downstream review/classify/gate semantics remain pinned to committed state
- [ ] Operator-facing error text is deterministic and actionable

## Architecture Validation
- [ ] The patch hardens the review boundary instead of redesigning the pipeline
- [ ] The contract remains aligned to `origin/main...HEAD`
- [ ] Existing deterministic gate reuse behavior is not weakened
- [ ] Existing run-time clean-tree contract is not relaxed or contradicted

## Verification
- [ ] Focused tests updated for blocked and clean review paths
- [ ] Docs/checklist/registry updated as needed
- [ ] Manual verification steps recorded
- [ ] Follow-ups captured separately for anything beyond committed-HEAD review fidelity

