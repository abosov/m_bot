# US-AUTO-12: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No finalize-story automation was added
- [ ] No allowed-files guard logic was added
- [ ] No AI review gate logic was added
- [ ] No unrelated runner refactor was introduced

## Functional Validation
- [ ] One bundle pack can materialize the seven required bundle files
- [ ] Materialization is atomic
- [ ] Validation fails on unresolved placeholders
- [ ] Validation fails on incomplete required sections
- [ ] `run_story.sh` refuses invalid bundles

## Architecture Validation
- [ ] Bundle pack format is simple and deterministic
- [ ] Bootstrap and production flows are clearly separated
- [ ] Canonical unresolved placeholder token is consistent with existing CI policy

## Verification
- [ ] Focused tests updated
- [ ] Docs/specs updated
- [ ] Follow-ups captured separately
