# US-AUTO-21: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No redesign of runner snapshot semantics
- [ ] No changes to `automation/run_codex_task.sh`
- [ ] No hidden auto-commit behavior introduced

## Functional Validation
- [ ] Review is blocked when working tree is dirty
- [ ] Gate is blocked before AI review/classification starts
- [ ] `review_story_run.sh` clearly reports blocked review safety state
- [ ] Error message is actionable and explicit
- [ ] Clean working tree still allows normal review/gate flow

## Architecture / Source of Truth
- [ ] Commit-based review remains the source of truth
- [ ] Fail-fast boundary is enforced at review stage
- [ ] Review/gate layer does not rely on hidden git mutation
- [ ] Docs reflect the new workflow rule

## Verification
- [ ] Tests cover clean-tree pass case
- [ ] Tests cover dirty-tree block case
- [ ] Gate output is verified
- [ ] No unrelated automation behavior changed

