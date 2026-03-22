# US-AUTO-39: Re-review / Re-gate Finalized Post-Commit HEAD

## Story ID and Title
- Story ID: `US-AUTO-39`
- Title: `Re-review / Re-gate Finalized Post-Commit HEAD`

## Objective
Restore the workflow invariant that reviewed evidence, finalized branch state, and merge-ready state must all refer to the same HEAD. If finalize creates a new commit, any earlier approval must become stale until review/gate are rerun for the new finalized HEAD.

## Scope
- Define the contract for post-finalize re-review / re-gate.
- Bind review/gate evidence to an explicit HEAD identity.
- Update workflow scripts only as needed to fail closed on HEAD mismatch.
- Add or update focused tests for stale approval after finalize mutates HEAD.
- Update workflow docs and active bundle files for this story.

## Non-goals
- Do not redesign the whole run directory model.
- Do not solve all branch-wide scope issues in this story.
- Do not implement global ephemeral path policy.
- Do not implement failed-run rollback/cleanup here.
- Do not absorb US-AUTO-40, US-AUTO-41, US-AUTO-35, US-AUTO-36, US-AUTO-37, or US-AUTO-38 except for minimal plumbing strictly required for this story.

## Dependencies
- Findings and closure state from US-AUTO-32.
- Existing finalize/review/gate workflow scripts.
- Existing story bundle materialization/validation workflow.

## Source of Truth
- `automation/scripts/finalize_story.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/run_codex_task.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `automation/bundle_packs/US-AUTO-39.bundle.md`

## Current Code Reality
- US-AUTO-32 proved that pre-merge finalization can create a new commit safely.
- Existing workflow behavior can leave review/gate evidence bound to an earlier HEAD after finalize mutates branch HEAD.
- Some review flows resolve the latest run rather than a run explicitly bound to current HEAD.
- This creates a stale-approval risk where reviewed evidence may not match the finalized snapshot that is actually considered for merge.

## Target Outcome
- Finalize may still create a pre-merge finalized commit.
- That finalized HEAD becomes the only valid merge target.
- Pre-finalize approval becomes stale automatically if HEAD changes.
- Review/gate evidence must be explicitly associated with the finalized HEAD.
- Merge readiness fails closed unless reviewed HEAD == finalized HEAD == merged HEAD.

