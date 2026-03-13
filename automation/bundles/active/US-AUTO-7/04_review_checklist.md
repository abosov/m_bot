# US-AUTO-7 Review Checklist

## Scope and architecture
- [ ] Only allowed automation/workflow files changed
- [ ] No product runtime code changed
- [ ] No DB/schema/deployment changes introduced
- [ ] Patch stays minimal and focused on stable review evidence

## Functional checks
- [ ] Review artifacts still work when story changes are already committed
- [ ] `changed_files.txt` reflects actual story diff
- [ ] `diff.patch` reflects the same stable diff source
- [ ] `manifest.md` does not incorrectly report `changed_files_detected: no`
- [ ] Review bundle changed-files section is consistent with actual diff
- [ ] Review bundle diff section is consistent with actual diff

## Reproducibility
- [ ] Review evidence does not depend only on uncommitted working tree state
- [ ] Diff source is stable and explainable
- [ ] Re-running review on the same committed branch remains consistent

## Tests
- [ ] Relevant tests added or updated
- [ ] Clean-working-tree committed-diff scenario is covered
- [ ] No obvious regression in review/run workflow

## Manual verification
- [ ] `git diff --name-only origin/main...HEAD` matches review evidence
- [ ] generated run artifacts under `automation/runs/<STORY_ID>/<RUN_ID>/` are coherent
- [ ] no false blocker caused only by empty working tree evidence
