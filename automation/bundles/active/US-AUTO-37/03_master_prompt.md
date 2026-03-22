# US-AUTO-37 PROMPT 1 — Ephemeral automation paths contract

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Story
US-AUTO-37 — Ephemeral automation paths contract.

## Goal
Implement a minimal, safe, and explicit workflow contract for `automation/story_change_ledger.jsonl` so it is treated as an ephemeral automation artifact instead of normal implementation diff, while preserving existing strict review and fidelity behavior.

## Source of Truth
- `automation/scripts/run_story.sh`
- `automation/scripts/finalize_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/finalize_story.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `tests/test_run_story.py`
- `tests/test_finalize_story.py`
- `tests/test_review_story_run.py`
- `tests/test_review_gate_story_run.py`
- `automation/bundle_packs/US-AUTO-37.bundle.md`
- `automation/bundles/active/US-AUTO-37/**`
- `automation/story_change_ledger.jsonl`

## Files Not Allowed To Change
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- unrelated CI workflow files
- unrelated product/runtime code
- any broad workaround that weakens real-diff validation

## Implementation Requirements
1. Treat `automation/story_change_ledger.jsonl` as an ephemeral automation path.
2. Keep the solution narrow and deterministic.
3. Ensure happy-path run does not leave this file as dirty state.
4. Ensure happy-path finalize does not leave this file as dirty state.
5. Ensure real implementation changes are still detected strictly.
6. Update focused tests and docs only as required.

## Testing
- Add or update focused tests for run behavior.
- Add or update focused tests for finalize behavior.
- Verify real implementation changes are still not masked.
- Run focused pytest targets relevant to the changed files.

## Documentation
- Update workflow docs/specs only where needed to reflect the ephemeral-path contract.
- Keep documentation aligned with actual implemented behavior.

## Output
Return:
1. changed files summary
2. design rationale
3. validation performed
4. risks / follow-ups
5. final diff

