## Role
You are the implementation engineer for a fail-closed automation pipeline. Work narrowly, preserve invariants, and do not broaden policy beyond the exact defect described here.

## Goal
Implement a narrow execution-layer fix so that code-only stories do not fail solely because Codex emitted a recognized companion registry or documentation edit outside the intended implementation scope. Those companion artifacts must be filtered out of the effective execution review surface, while all real out-of-scope edits continue to hard-fail.

## Source of Truth
Use these sources of truth:
- `docs/90_codex/epics/US-AUTO_REGISTRY.md` for story intent, status context, and dependency framing :contentReference[oaicite:8]{index=8}
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `tests/test_run_story.py`
- `tests/test_run_codex_task.py`

Registry facts relevant to this story:
- US-AUTO-57 is blocked by a companion-artifact diff added to `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- US-AUTO-69 is the designated follow-up to resolve that blocker narrowly at the execution layer
- the epic’s remaining gaps are optimization and workflow clarity problems, not justification for fail-open behavior :contentReference[oaicite:9]{index=9}

## Files Allowed To Change
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- `tests/test_run_story.py`
- `tests/test_run_codex_task.py`

## Files Not Allowed To Change
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/story_change_ledger.jsonl`
- any unrelated production or test file not explicitly listed as allowed

## Atomic Task Isolation Contract
You must solve one problem only:
execution filtering of recognized companion artifacts for code-only stories.

You must not:
- redesign scope validation broadly
- change review-stage semantics
- alter registry workflow
- add telemetry or UX layers
- create fallback behavior that silently allows unknown extra edits

Treat ambiguity as reject, not as permission to expand logic.

## Execution Gate
Hard-stop rules:
- if the change seems to require widening allowed scope, stop
- if unknown extra paths cannot be deterministically classified as companion artifacts, keep reject behavior
- if filtering changed-files would diverge from the execution diff surface, fix the inconsistency inside allowed files or stop
- do not touch any file outside the allowed list
- do not auto-edit the registry

The desired behavior is fail-closed:
- recognized companion-only extra paths: filtered
- any remaining non-companion out-of-scope path: reject
- mixed companion + non-companion: reject
- ambiguous classification: reject

## Implementation Requirements
Implement only the minimal logic needed to satisfy the story:
1. Add or refine explicit companion-artifact path recognition for code-only story execution.
2. Ensure those recognized companion paths are removed from the effective implementation review surface used by execution-stage scope decisions.
3. Keep all unknown or non-companion extra paths as hard failures.
4. Ensure any relevant execution evidence or diff surface exposed by the allowed files remains consistent with the filtered changed-files surface.
5. Add focused regression tests for:
   - companion-only registry/doc edit does not fail
   - non-companion out-of-scope path still fails
   - mixed companion + non-companion still fails
   - deterministic behavior when no companion artifact is present

Do not add generic abstractions unless they are the smallest clean way to express the exact classifier/filter.

## Verification Requirements
Run only the minimum targeted verification needed for this story:
- `pytest -q tests/test_run_story.py`
- `pytest -q tests/test_run_codex_task.py`

If a smaller targeted subset is clearly sufficient during development, that is acceptable, but final verification must cover both listed test files.

## Output
Produce:
- the minimal code changes within allowed files
- focused tests proving the binary behavior above
- no unrelated refactors
- no registry edits
- no explanatory prose in code comments beyond what is necessary for maintainability

