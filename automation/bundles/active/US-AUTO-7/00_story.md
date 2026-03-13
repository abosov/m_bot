# US-AUTO-7 — Stable review evidence from commit range

## Problem

Current review evidence can become invalid after a feature is already committed.

`automation/run_codex_task.sh` currently builds review artifacts from the current working tree after Codex execution.
Because of that, a story can be fully implemented and committed, but a later review run may still produce:

- empty `changed_files.txt`
- empty `diff.patch`
- `changed_files_detected: no`

This creates false `MERGE BLOCKER` results and breaks audit-trail reliability.

## Goal

Make review evidence stable and reproducible by generating review artifacts from a commit range instead of relying only on the post-run working tree.

## Desired behavior

For a story branch, review artifacts must reflect the actual branch diff against the review base, even when theorking tree is clean.

At minimum, the review pipeline must be able to produce:

- `changed_files.txt`
- `diff.patch`
- review bundle sections based on a stable diff source

using branch commit history rather than only uncommitted changes.

## Scope

Allowed:

- update automation review/run logic
- update review bundle generation logic
- update manifests if needed
- add/update tests for the new behavior
- update workflow documentation/checklists
- update active story bundle for US-AUTO-7

Not allowed:

- no product runtime changes
- no DB/schema changes
- no deployment changes
- no unrelated refactor

## Source of truth

- `automation/run_codex_task.sh`
- review artifacts under `automation/runs/<STORY_ID>/<RUN_ID>/`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Acceptance criteria

1. If a story branch contains committed changes relative to the review base, review artifacts must still show those changes even when the working tree is clean.
2. `changed_files.txt` must contain the real changed files for the story diff.
3. `diff.patch` must contain a usable patch for the same diff source.
4. `manifest.md` must not incorrectly report `changed_files_detected: no` when committed story changes exist.
5. Review bundle changed-files and diff sections must be consistent with the actual story diff.
6. Existing workflow remains atomic and reproducible.
7. Tests cover the stable-diff behavior.

## Notes

This story is a remediation for the false blocker discovered after merging US-AUTO-6.

The defect is in workflow evidence generation, not in Zumbot runtime logic.
