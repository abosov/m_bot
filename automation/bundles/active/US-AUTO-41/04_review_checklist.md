# Review Checklist — US-AUTO-41

## Scope Validation
- [ ] only allowed files changed
- [ ] no unrelated refactors introduced
- [ ] rollback lifecycle behavior was not weakened

## Functional Validation
- [ ] `automation/scripts/commit_story_artifacts.sh` exists
- [ ] script requires a story id argument
- [ ] script commits only allowed story artifact paths
- [ ] script fails when unrelated dirty files exist
- [ ] script fails when no eligible artifact changes exist
- [ ] `run_story.sh` blocks on dirty story artifacts
- [ ] remediation message points to the handoff script
- [ ] no implicit auto-commit exists in run flow

## Verification
- [ ] relevant tests pass
- [ ] docs updated
- [ ] epic registry updated
- [ ] operator flow is documented as `materialize -> commit -> run`