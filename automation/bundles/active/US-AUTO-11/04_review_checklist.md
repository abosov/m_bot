# US-AUTO-11: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No allowed-files guard logic was added
- [ ] No AI review gate logic was added
- [ ] No unrelated runner refactor was introduced

## Functional Validation
- [ ] `repository_map_runtime.md` is generated for a run
- [ ] `story_context.md` references the repository map artifact
- [ ] `manifest.md` records repository map injection status

## Architecture Validation
- [ ] Repository map generation is lightweight and deterministic
- [ ] Existing curated docs are reused instead of replaced
- [ ] Runner remains the owner of this injection logic

## Verification
- [ ] Focused tests updated
- [ ] Manual run command documented
- [ ] Follow-ups captured separately
