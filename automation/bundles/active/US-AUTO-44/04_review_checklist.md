# Review Checklist — US-AUTO-44

## Scope Validation
- [ ] only allowed files changed
- [ ] no unrelated refactors introduced
- [ ] `commit_story_artifacts.sh` was not modified
- [ ] `run_codex_task.sh` was not modified
- [ ] rollback behavior was not broadened or weakened

## Functional Validation
- [ ] `run_story.sh` contains an explicit preflight stage
- [ ] clean tree continues normally
- [ ] request-story artifact dirtiness produces deterministic handoff output
- [ ] unrelated dirty paths produce deterministic blocked output
- [ ] operator guidance includes exact next commands
- [ ] no auto-commit exists in run flow
- [ ] no auto-clean exists in run flow
- [ ] clean-tree enforcement remains fail-closed

## Verification
- [ ] relevant tests pass
- [ ] docs updated
- [ ] epic registry updated
- [ ] canonical operator flow documents preflight explicitly

## Messaging Validation
- [ ] blocked messages clearly distinguish story-artifact dirtiness from unrelated dirtiness
- [ ] messages are stable enough for regression tests
- [ ] remediation does not suggest broad commits outside the story scope

