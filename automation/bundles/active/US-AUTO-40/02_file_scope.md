# File Scope — US-AUTO-40

## Files Allowed To Change
Primary implementation targets:
- automation/scripts/review_story_run.sh
- automation/scripts/review_gate_story_run.sh

Supporting documentation:
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/STORY_BUNDLE_SPEC.md

Primary tests:
- tests/test_review_story_run.py
- tests/test_review_gate_story_run.py

Bundle alignment updates if needed:
- automation/bundles/active/US-AUTO-40/01_context_bundle.md
- automation/bundles/active/US-AUTO-40/02_file_scope.md
- automation/bundles/active/US-AUTO-40/04_review_checklist.md
- automation/bundles/active/US-AUTO-40/05_followups.md
- automation/bundles/active/US-AUTO-40/06_manual_actions.md

## Files Not Allowed To Change
Unless strictly required by the implementation, do not modify:
- unrelated automation scripts outside the review/gate path
- runtime hygiene / rollback scripts for ledger cleanup
- registry / backlog documents unrelated to US-AUTO-40
- broader scope-contract architecture files beyond focused documentation updates

## Scope Notes
This story is limited to enforcing fidelity between review artifacts and the actual branch diff.

Keep the blast radius small and do not use this story to solve:
- US-AUTO-41 single-source-of-truth redesign
- US-AUTO-37 ephemeral automation paths contract
- US-AUTO-38 automatic rollback after failed automation run
- US-AUTO-35 run-local resolution redesign
- US-AUTO-36 preflight hygiene redesign