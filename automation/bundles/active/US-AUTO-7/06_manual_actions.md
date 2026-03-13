# US-AUTO-7 Manual Actions

## Before implementation
- Confirm hotfix branch is correct
- Keep patch limited to automation workflow files

## After implementation
Run manual checks:

1. `git diff --name-only origin/main...HEAD`
2. run story/review flow for the remediation story
3. inspect latest run artifacts under `automation/runs/US-AUTO-7/<RUN_ID>/`
4. confirm committed branch changes still appear in:
   - `changed_files.txt`
   - `diff.patch`
   - `manifest.md`
   - `review_bundle.md`

## Merge guidance
Do not merge until:
- stable diff evidence is confirmed
- tests pass
- review bundle is coherent
- no false `MERGE BLOCKER` is caused by empty working-tree-only evidence
