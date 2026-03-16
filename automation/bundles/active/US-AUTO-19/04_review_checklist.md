# US-AUTO-19: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No core pipeline execution semantics were changed
- [ ] No AI review / classification / gate logic was modified
- [ ] No unrelated refactor or formatting-only edits

## Functional Validation
- [ ] `automation/scripts/analyze_story_run.sh` is read-only
- [ ] Latest run resolution works
- [ ] `AUTOMATION_RUN_DIR` override works
- [ ] Missing artifacts are surfaced clearly
- [ ] Incomplete runs still produce useful output
- [ ] Output includes final status line
- [ ] Output remains concise and operator-oriented

## Verification
- [ ] Focused tests added
- [ ] Docs updated for the new operator command
- [ ] Manual command for local use is recorded
- [ ] Risks and follow-ups captured before merge

