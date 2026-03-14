# US-AUTO-13: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No allowed-files guard logic was added
- [ ] No AI review gate logic was added
- [ ] No unrelated runner refactor was introduced

## Functional Validation
- [ ] Dirty tree is blocked
- [ ] `main` branch is blocked
- [ ] Non-green PR checks block merge
- [ ] Successful finalize lands on updated clean `main`
- [ ] Successful finalize removes story branches locally and remotely

## Architecture Validation
- [ ] Finalization is a separate workflow layer from story execution
- [ ] `gh` is used as the canonical GitHub integration path
- [ ] Finalization logic is deterministic and explicit

## Verification
- [ ] Focused tests updated
- [ ] Docs/checklist updated
- [ ] Follow-ups captured separately

