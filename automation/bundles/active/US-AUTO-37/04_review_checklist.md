# US-AUTO-37: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No unrelated runner refactor was introduced
- [ ] No broad ignore rule was introduced
- [ ] No weakening of US-AUTO-39 or US-AUTO-40 invariants was introduced

## Functional Validation
- [ ] `automation/story_change_ledger.jsonl` is treated as an ephemeral automation path
- [ ] Happy-path `run_story.sh` does not leave ledger dirt
- [ ] Happy-path `finalize_story.sh` does not leave ledger dirt
- [ ] Real implementation changes remain detectable

## Verification
- [ ] Focused tests were run
- [ ] Bundle materialization and validation succeeded
- [ ] Final diff and docs were reviewed

