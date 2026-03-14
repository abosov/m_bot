# US-AUTO-14: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No diff-size guard logic was added
- [ ] No AI review gate logic was added
- [ ] No unrelated runner refactor was introduced
- [ ] No GitHub merge/finalization logic was changed

## Functional Validation
- [ ] Guard parses `## Files Allowed To Change` correctly
- [ ] Exact path matching works
- [ ] Recursive directory matching via `/**` works
- [ ] Out-of-scope changed files fail the run
- [ ] Empty changed-files input passes
- [ ] Guard runs before pytest in `automation/run_codex_task.sh`

## Architecture Validation
- [ ] `02_file_scope.md` remains the runtime source of truth for story scope
- [ ] Scope enforcement is a separate layer from bundle validation
- [ ] Scope enforcement is a separate layer from AI review and finalization
- [ ] Failure behavior is deterministic and fail-fast

## Verification
- [ ] Focused tests updated
- [ ] Manual story-run check performed
- [ ] Docs/checklist updated if needed
- [ ] Follow-ups captured separately

