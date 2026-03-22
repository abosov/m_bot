# File Scope — US-AUTO-40

## In Scope

Primary implementation targets:

- automation/scripts/review_story_run.sh
- automation/scripts/review_gate_story_run.sh

Supporting documentation:

- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/STORY_BUNDLE_SPEC:

- tests/test_review_story_run.py
- tests/test_review_gate_story_run.py

## Scope Intent

This story should implement fidelity enforcement between review artifacts and the actual branch diff.

The expected code change should stay concentrated in the review / gate workflow layer and its tests/docs.

## Allowed Secondary Touches

Secondary bundle/documentation alignment updates are allowed only if required to:

- document the fidelity contract;
- reflect result schema changes;
- explain remediation steps for stale artifacts.

## Out of Scope

Do not use this story to redesign the full scope authority model across bundle files.
That belongs to US-AUTO-41.

Do not solve runtime side-effects of:

- automation/story_change_ledger.jsonl

That belongs to US-AUTO-37 / US-AUTO-38.

Do not broaden into run selection redesign or unrelated preflight work:

- run-local resolution redesign belongs to US-AUTO-35
- hygiene guard redesign belongs to US-AUTO-36

## Review Expectation

The implemented diff should be explainable as:

- one fidelity contract;
- one enforcement path;
- focused tests;
- focused docs.

## Drift Guard

If implementation requires modifying files outside this scope, that should only happen when directly necessary for the fidelity contract to work end-to-end.
Any such expansion should remain minimal and justified by the actual implementation.
