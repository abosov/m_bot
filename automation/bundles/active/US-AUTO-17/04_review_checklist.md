# US-AUTO-17: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No console UX / chaining / resume logic was added
- [ ] No allowed-files enforcement logic was changed
- [ ] No AI review gate behavior was changed
- [ ] No unrelated runner refactor was introduced

## Functional Validation
- [ ] `repository_map_runtime.md` includes architecture layer boundaries
- [ ] `repository_map_runtime.md` includes story-local context for the active story
- [ ] `repository_map_runtime.md` includes anti-hallucination rules
- [ ] `repository_map_runtime.md` includes pipeline dependency hints
- [ ] `story_context.md` still references the repository map artifact
- [ ] `manifest.md` still records repository map injection metadata

## Verification
- [ ] Focused tests updated
- [ ] Manual run command documented
- [ ] Follow-ups for console UX / chaining are deferred to later stories
- [ ] Risks are captured before merge

