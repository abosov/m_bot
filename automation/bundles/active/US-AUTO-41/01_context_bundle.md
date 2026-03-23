# Context Bundle — US-AUTO-41

## Source of Truth
- `automation/scripts/new_story_bundle.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Current Code Reality
US-AUTO-38 fixed rollback and cleanup behavior after failed or interrupted runs. That reduced dirty-tree problems after execution, but it did not address operator friction before execution.

After `new_story_bundle.sh` and `materialize_story_bundle.sh`, the repository contains generated story artifacts that must be committed before `run_story.sh` can pass its clean-tree preflight.

The effective operator flow before this story was:
1. create bundle
2. materialize bundle
3. hit clean-tree block in `run_story.sh`
4. manually inspect and commit generated story files
5. rerun

This is not a correctness bug in `run_story.sh`; it is a missing explicit workflow transition.

## Architectural Intent
Formalize a distinct transition state between materialization and execution:
- **draft**: story artifacts exist but are uncommitted
- **committed**: story artifacts are committed and the tree is clean
- **runnable**: `run_story.sh` may proceed

The design intent is to preserve strict clean-tree enforcement while removing guesswork around what must be committed.

The canonical operator flow should become:
1. create bundle
2. materialize
3. `automation/scripts/commit_story_artifacts.sh <STORY_ID>`
4. `automation/scripts/run_story.sh <STORY_ID>`

## Risks
- broad matching logic may accidentally include unrelated files
- hidden auto-commit behavior would blur responsibility boundaries
- too much scope in this story could turn a narrow contract fix into another workflow redesign

## Acceptance Notes
Keep this story narrow. The goal is to make the missing handoff canonical, not to introduce automation layers beyond that handoff.