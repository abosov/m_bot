# US-AUTO-45: Master Prompt

## Role
You are the System Architect + Developer + QA + Security Reviewer for Zumbot.

## Goal
Make `automation/scripts/review_gate_story_run.sh` deterministic by forcing it to consume pinned run review artifacts as source of truth and fail closed when those prerequisites are missing or invalid, without recomputing upstream review or classification stages.

## Source of Truth
- `automation/bundles/active/US-AUTO-45/00_story.md`
- `automation/bundles/active/US-AUTO-45/01_context_bundle.md`
- `automation/bundles/active/US-AUTO-45/02_file_scope.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- Existing pinned run artifacts for the selected run

## Files Allowed To Change
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `tests/test_review_gate_story_run.py`
- `tests/test_analyze_story_run.py`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/build_bundle_pack.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/run_codex_task.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/merge_recommendation_contract.sh`

## Implementation Rules
- Keep the patch minimal and story-scoped.
- Do not invent new artifact formats.
- Do not silently recover by recomputing upstream artifacts.
- Preserve fail-closed behavior.
- Preserve pinned-run and stale-head protections.
- If an out-of-scope dependency is discovered, record it as a follow-up instead of implementing it here.
- Explicitly restate the one-sentence task intent before edits.
- Do not broaden scope beyond declared intent.

## Execution Gate
- Refuse implementation if this story would require upstream producer changes.
- Refuse implementation if deterministic reuse cannot be enforced within the allowed files.
- Refuse implementation if a second independently reviewable fix would need to be bundled into this run.

## Test Plan
- Add or update focused tests for deterministic reuse.
- Add or update focused tests for missing-artifact fail-closed behavior.
- Add or update focused tests for no-recompute expectations.
- Run targeted pytest for touched gate and analyze tests.

## Output
Return:
1. changed files summary
2. implementation rationale
3. exact lifecycle integration points used
4. tests run and results
5. risks or follow-ups discovered but not implemented
6. final diff summary

