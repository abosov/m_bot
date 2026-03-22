# US-AUTO-40 PROMPT 1

## Goal
Design and implement a strict workflow contract ensuring that review artifacts used by the review/gate flow are faithful to the actual code under review, and that stale or materially inconsistent artifacts are rejected fail-closed.

## Source of Truth
- The authoritative reviewed code delta is the actual git diff for the branch under review, normally `origin/main...HEAD` unless the current workflow already defines a tighter equivalent.
- Existing review/gate scripts, tests, and docs in the allowed scope are the implementation baseline.
- The final active bundle must reflect the implemented contract after completion.

## Files Allowed To Change
- automation/scripts/review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- docs/90_codex/STORY_EXECUTION_CHECKLIST.md
- docs/90_codex/STORY_BUNDLE_SPEC.md
- tests/test_review_story_run.py
- tests/test_review_gate_story_run.py
- automation/bundles/active/US-AUTO-40/01_context_bundle.md
- automation/bundles/active/US-AUTO-40/02_file_scope.md
- automation/bundles/active/US-AUTO-40/04_review_checklist.md
- automation/bundles/active/US-AUTO-40/05_followups.md
- automation/bundles/active/US-AUTO-40/06_manual_actions.md

## Files Not Allowed To Change
Do not broaden scope into:
- ledger runtime hygiene / rollback implementation
- unrelated automation runner redesign
- broader bundle scope-authority redesign reserved for US-AUTO-41
- unrelated registry/backlog files unless absolutely required for correctness

## Output
Make the required code, test, and documentation changes directly in the repository.

The result must:
- preserve US-AUTO-39 HEAD-binding behavior;
- enforce artifact fidelity against actual diff;
- reject stale/incomplete artifacts deterministically;
- keep the implementation tightly scoped to US-AUTO-40;
- update the active bundle to reflect the final contract.

## Context
US-AUTO-39 solved "wrong HEAD" approval by binding review/gate decisions to reviewed HEAD and rejecting checkout HEAD mismatch fail-closed.

The remaining integrity gap is that review artifacts may still describe a change set that no longer fully matches the actual branch diff.

This story closes that gap.

## Constraints
- Preserve fail-closed behavior.
- Do not create a second competing source of truth for reviewed content.
- Prefer machine-verifiable checks based on real repository state.
- Keep blast radius minimal.

## Tasks
1. Inspect where artifact fidelity can drift from actual HEAD diff.
2. Define the fidelity contract:
   - authoritative diff,
   - compared artifact data,
   - enforcement point,
   - reject/failure condition,
   - remediation path.
3. Implement the smallest robust enforcement change set.
4. Add focused tests for approve vs reject paths.
5. Update docs and active bundle to reflect the new contract.