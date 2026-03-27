# US-AUTO-49 — Scope validation ignores committed active-story bundle artifacts

## Story ID and Title
- **Story ID:** US-AUTO-49
- **Title:** Scope validation ignores committed active-story bundle artifacts

## Objective
Make story-run scope validation fail closed on true out-of-scope implementation changes while ignoring already-committed bundle artifacts for the active story that were intentionally materialized and committed before `run_story.sh` started.

This story exists to restore a valid execution path for atomic follow-ups such as `US-AUTO-28-F1` without weakening scope enforcement for Codex-produced changes.

## Scope
In scope:
- adjust the story-run scope-baseline logic so committed active-story bundle artifacts for the same story are excluded from implementation-delta scope validation
- preserve fail-closed behavior for all actual Codex-produced tracked and untracked changes outside the allowed file list
- add regression coverage for the committed-bundle-artifact scenario and for a true out-of-scope implementation change in the same execution path
- keep the change isolated to runtime orchestration and its tests

Out of scope:
- changing story bundle format or validator contract
- changing review-stage classification rules
- changing epic registry format
- changing bundle commit handoff policy from `US-AUTO-41`
- changing `US-AUTO-28-F1` implementation logic itself
- broad retry, escalation, UX, or review-pipeline redesign

## Non-goals
- do not relax allowed-file enforcement globally
- do not ignore uncommitted bundle artifacts
- do not ignore bundle artifacts for other stories
- do not introduce a fallback mode when story identity or artifact provenance cannot be determined
- do not modify review gate, finalize flow, or registry automation

## Dependencies
- `US-AUTO-41` story artifact commit handoff before run must remain the canonical prerequisite
- active bundle structure and validator contract defined by `STORY_BUNDLE_SPEC.md` and `validate_story_bundle.sh`
- existing allowed-files enforcement in the story-run pipeline must remain fail closed
- `US-AUTO-28-F1` stays blocked until this orchestration defect is fixed

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- `automation/run_codex_task.sh`
- current test coverage for story-run orchestration and scope validation

## Current Code Reality
Current workflow correctly requires bundle materialization and commit before a story run, but runtime scope validation still treats those already-committed active-story bundle artifacts as if they were part of the current implementation delta.

That causes a false reject before review stage even when Codex only changed allowed implementation files. The defect is orchestration-level: scope validation is using an insufficient baseline for runtime changes and does not distinguish committed story artifacts from Codex-produced implementation edits.

## Target Outcome
After this story:
- committed active-story bundle artifacts for the same story are ignored by scope validation during the run
- real implementation changes are still validated strictly against the allowed file list
- if story identity, artifact provenance, or baseline derivation is ambiguous, the pipeline fails closed
- `US-AUTO-28-F1` can be rerun only after this story is merged and the branch state is clean

## Atomic Task Isolation Contract
- This story fixes exactly one problem: false out-of-scope detection caused by committed active-story bundle artifacts being counted in runtime scope validation.
- Allowed implementation surface is limited to runtime orchestration and its tests.
- No changes to review logic, registry schema, bundle validator schema, or follow-up story content.
- If the implementation requires touching another pipeline stage or weakening scope enforcement semantics, stop and record a follow-up instead of expanding this story.
- The patch must preserve fail-closed behavior and determinism.

## Risks
### Complexity
- **Complexity:** Medium

### Risk
- **Risk:** Medium

### Blast Radius
- **Blast Radius:** Medium

### Main Risks
- a too-broad ignore rule could accidentally hide true out-of-scope changes
- story identity matching could be implemented loosely and misclassify artifacts from another story
- regression risk in runtime diff/baseline handling if the ignore rule is applied after rather than before authoritative change classification

### Risk Controls
- ignore only committed artifacts for the active story ID
- keep all other files subject to normal allowed-files checks
- add regression tests for both the valid ignore path and the reject path
- fail closed if the active story ID cannot be derived or the artifact path does not match the canonical story locations

## Manual Actions
- materialize this bundle to `automation/bundles/active/US-AUTO-49/`
- validate the bundle before any branch work
- update `docs/90_codex/epics/US-AUTO_REGISTRY.md` so `US-AUTO-49` becomes the current blocker-follow-up and `US-AUTO-28-F1` remains blocked pending this fix
- create a dedicated branch for this story
- commit bundle artifacts before running `automation/scripts/run_story.sh US-AUTO-49`
- after merge, rerun selection logic from the registry; the expected next candidate is `US-AUTO-28-F1`

## Acceptance Notes
- bundle must pass `materialize_story_bundle.sh US-AUTO-49` and `validate_story_bundle.sh US-AUTO-49`
- story run must ignore already-committed bundle artifacts for `US-AUTO-49` when evaluating implementation scope
- story run must still reject a true out-of-scope implementation file change
- no validator-contract files or review-stage logic may be changed
- deterministic review outcome must remain possible because the runtime diff presented for review contains only the actual implementation delta

