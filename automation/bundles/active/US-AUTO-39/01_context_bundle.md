# US-AUTO-39: Context Bundle

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

- US-AUTO-32 confirmed that pre-merge finalization can create a new commit before merge.
- Review/gate evidence may still belong to an earlier HEAD when finalize mutates the branch HEAD.
- Some review flows resolve the latest available run rather than a run explicitly bound to the current HEAD.
- This creates a stale-approval condition where reviewed evidence can differ from the finalized snapshot intended for merge.

## Architectural Intent

- Preserve durable pre-merge finalization.
- Make the finalized HEAD the canonical merge target.
- Require review/gate evidence to be explicitly bound to a specific HEAD identity.
- Fail closed when current HEAD differs from reviewed/gated HEAD, and persist both identities in gate evidence.
- Restore the invariant: reviewed HEAD == finalized HEAD == merged HEAD.

## Risks

- Overreaching into broader run-resolution redesign that belongs in later stories.
- Accidentally keeping a latest-run loophole while adding partial HEAD metadata.
- Allowing operator UX to imply approval is still valid after HEAD mutation.
- Updating docs/tests incompletely and leaving the contract ambiguous.

## Acceptance Notes

- Finalize may still create a new commit before merge.
- Any approval from the pre-finalize HEAD must become stale if HEAD changes.
- Re-review / re-gate on the finalized HEAD must be required before merge readiness is restored.
- The implementation must remain narrowly scoped to this contract.
