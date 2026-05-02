## Story ID and Title

US-AUTO-76 — Classifier scope semantics for governance story artifacts

## Objective

Teach the review classification layer to treat approved story governance artifacts as valid story workflow artifacts instead of merge blockers, when and only when they are explicitly approved by the story scope and belong to the active story workflow.

The immediate problem is that a technically complete story can still be rejected because the classifier treats normal governance artifacts as out-of-scope implementation changes, for example:

- `automation/bundle_packs/<STORY_ID>.bundle.md`
- `automation/bundles/active/<STORY_ID>/**`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

The target behavior is not to weaken review safety. Runtime and implementation files must still be validated separately. This story only clarifies classifier/review-gate semantics for intentional story governance artifacts.

## Scope

Implement narrow classifier and review-gate semantics for governance story artifacts.

Allowed story governance artifacts:

- bundle pack source-of-truth:
  - `automation/bundle_packs/<STORY_ID>.bundle.md`
- materialized active bundle output:
  - `automation/bundles/active/<STORY_ID>/**`
- lifecycle/governance registry update:
  - `docs/90_codex/epics/US-AUTO_REGISTRY.md`

These files may be treated as allowed story artifacts only when:

1. the bundle pack is the source-of-truth artifact for the same story ID;
2. the active bundle path belongs to the same story ID;
3. the registry update is an intentional lifecycle/governance update;
4. the files are explicitly present in the story scope;
5. implementation/runtime review surface remains separately validated.

Expected implementation surface:

- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- tests that exercise classifier and review-gate behavior for governance artifacts

Expected test surface:

- `tests/test_classify_review_story_run.py`
- `tests/test_review_gate_story_run.py`

Story artifact surface:

- `automation/bundle_packs/US-AUTO-76.bundle.md`
- `automation/bundles/active/US-AUTO-76/**`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Non-goals

Do not rewrite the review pipeline.

Do not implement operator workflow simplification.

Do not create or modify `docs/90_codex/US_AUTO_OPERATOR_GUIDE.md`.

Do not add `automation/scripts/next_step.sh`.

Do not centralize duplicated semantic projection logic.

Do not centralize companion-filter logic.

Do not refactor downstream scripts beyond the minimal classifier/review-gate change needed for this story.

Do not modify semantic projection producer behavior.

Do not change pinned run / HEAD safety checks.

Do not change stage-loop policy.

Do not reduce or bypass runtime review validation.

Do not fix regressions by weakening tests or changing external error/message contracts unless the story explicitly documents that as the intended contract change.

## Dependencies

US-AUTO-75 must already be merged.

The current roadmap refresh must already be merged into `main`.

US-AUTO-76 must start from a clean feature branch created from fresh `main`.

US-AUTO-77 must not start until US-AUTO-76 is resolved or explicitly parked.

US-AUTO-74 must not start until US-AUTO-76 and US-AUTO-77 are resolved or explicitly parked.

## Source of Truth

Primary source of truth:

- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-76.bundle.md`
- `automation/bundles/active/US-AUTO-76/**`

Behavioral source of truth:

- US-AUTO-75 established semantic projection and projection-aware review surface behavior.
- US-AUTO-76 only changes classifier/review-gate interpretation of approved governance/story artifacts.
- Runtime review surface must remain independently validated.

Required workflow source of truth:

- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`

## Current Code Reality

Several downstream review scripts already contain local story-artifact filtering logic.

The current classifier can still interpret normal governance artifacts as out-of-scope changes and produce a merge-blocking rejection even when the implementation/runtime review surface is valid.

Known problematic artifact categories:

- `automation/bundle_packs/<STORY_ID>.bundle.md`
- `automation/bundles/active/<STORY_ID>/**`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

This was observed after US-AUTO-75: the implementation was complete, but the remaining reject was a classifier scope-semantics limitation rather than a runtime correctness blocker.

The current implementation likely has path filters in multiple scripts. This story must avoid broad centralization work and change only the minimum needed classifier/review-gate semantics.

## Target Outcome

A story run that changes only approved story governance artifacts plus valid implementation files must not be classified as a merge blocker solely because the governance artifacts are present.

The classifier should clearly distinguish:

- approved story governance artifacts;
- implementation/runtime review surface;
- genuinely out-of-scope changes.

The review gate should respect the classifier’s improved distinction without weakening safety gates.

Expected result:

- governance artifacts for the active story are allowed when explicitly scope-approved;
- unrelated bundle packs, unrelated active bundle directories, and unrelated registry changes remain suspicious or blocking;
- implementation/runtime files remain separately validated;
- tests prove the intended behavior and protect against regression.

