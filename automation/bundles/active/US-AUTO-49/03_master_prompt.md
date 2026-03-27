# Master Prompt — US-AUTO-49

## Role
You are implementing a narrow runtime-orchestration fix in the US-AUTO pipeline.

## Goal
Refine story-run scope validation so that already-committed canonical bundle artifacts for the active story are ignored during implementation-delta scope validation, while all true implementation changes remain strictly enforced.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`

## Files Allowed To Change
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`

## Files Not Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/check_allowed_files.sh`
- `automation/story_change_ledger.jsonl`
- `automation/bundle_packs/US-AUTO-28-F1.bundle.md`
- `automation/bundles/active/US-AUTO-28-F1/**`
- `automation/bundle_packs/US-AUTO-49.bundle.md`
- `automation/bundles/active/US-AUTO-49/**`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Atomic Task Isolation Contract
- Restate the task intent in one sentence before making changes.
- Fix exactly one issue: committed active-story bundle artifacts are incorrectly counted as scope-relevant implementation changes during the run.
- Do not change any other pipeline stage.
- Do not weaken fail-closed behavior.
- Do not broaden the ignore rule beyond canonical bundle artifacts for the active story.
- If the minimal fix appears to require touching additional files or stages, stop and surface that as a follow-up instead of expanding scope.

## Execution Gate
- Hard stop unless the implementation can be completed only within the allowed files.
- Hard stop if you cannot prove that the ignored paths are canonical bundle paths for the active story.
- Hard stop if the proposed logic would ignore uncommitted artifacts, artifacts for another story, or non-bundle implementation files.
- Hard stop if tests cannot cover both:
  - the valid same-story committed-bundle ignore path
  - the reject path for a real out-of-scope implementation change
- No fallback mode, no best-effort scope relaxation, no silent continue.

## Implementation Requirements
- Refine runtime change accounting in `automation/run_codex_task.sh` so committed canonical bundle artifacts for the active story are excluded before allowed-files scope validation is evaluated for the implementation delta.
- Preserve existing fail-closed semantics for every other changed file.
- Canonical bundle artifact paths are limited to:
  - `automation/bundle_packs/<STORY_ID>.bundle.md`
  - `automation/bundles/active/<STORY_ID>/...`
- The ignore rule must apply only when `<STORY_ID>` matches the active story being run.
- If story ID derivation or path matching is ambiguous, treat the file as normal and enforce existing scope validation.
- Add regression tests in `tests/test_run_codex_task.py` that prove:
  - same-story committed bundle artifacts do not trigger a scope failure
  - a true out-of-scope implementation file still triggers a scope failure
- Keep the patch deterministic and minimal.

## Verification Requirements
- Run targeted tests for `tests/test_run_codex_task.py`
- Verify no forbidden file changed
- Verify the implementation delta presented to downstream review excludes only the canonical same-story bundle artifacts and nothing else
- Verify the reject path still fails closed for a true out-of-scope implementation file

## Output
Provide:
- a minimal patch in the allowed files only
- targeted test evidence
- a brief note confirming that scope validation still fails closed for all non-canonical or cross-story changes

