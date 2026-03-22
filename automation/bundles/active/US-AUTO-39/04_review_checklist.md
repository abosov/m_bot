# US-AUTO-39: Review Checklist

## Scope Validation

- [ ] Changes stay inside `02_file_scope.md`
- [ ] No unrelated workflow redesign was absorbed
- [ ] No fail-open path was introduced
- [ ] Changes remain focused on HEAD-bound post-finalize approval

## Functional Validation

- [ ] Finalize can still create a pre-merge finalized commit
- [ ] Pre-finalize approval becomes stale if finalize changes HEAD
- [ ] Review/gate evidence is explicitly bound to a HEAD identity
- [ ] Merge readiness fails when current HEAD differs from reviewed/gated HEAD
- [ ] Re-review / re-gate on the finalized HEAD restores readiness

## Verification

- [ ] Targeted tests cover stale approval after HEAD mutation
- [ ] Docs and active bundle files were updated consistently
- [ ] Risks and follow-ups were captured without absorbing neighboring stories

