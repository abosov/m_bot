# US-AUTO-38: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No backend, frontend, database, or migration changes were introduced
- [ ] No unrelated finalize or registry redesign was introduced
- [ ] No unrelated deployment/runtime work was added

## Functional Validation
- [ ] Success path preserves intended working tree changes
- [ ] Failed execution restores tracked files to the exact pre-run state
- [ ] Failed execution cleans run-owned untracked artifacts
- [ ] Interruption/simulated trap path restores clean state where supported
- [ ] Rollback failure is surfaced explicitly
- [ ] US-AUTO-37 ephemeral path behavior is preserved

## Verification
- [ ] Focused tests cover success path
- [ ] Focused tests cover failure path
- [ ] Focused tests cover pre-mutation failure or safe no-op path
- [ ] Focused tests cover interruption/simulated trap behavior
- [ ] Documentation reflects failed-run rollback semantics

