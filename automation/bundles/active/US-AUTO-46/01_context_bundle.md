# US-AUTO-46: Context Bundle

## Source of Truth
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Current Code Reality
- The pipeline is now stable through `run -> review -> classify -> gate -> analyze -> finalize`.
- `US-AUTO-41` already forces story artifacts to be committed before `run_story.sh`.
- `US-AUTO-45` makes gate reuse deterministic once pinned review/classification artifacts already exist.
- The unresolved gap is conceptual rather than purely mechanical: review can still be invoked in a checkout whose workspace reality is not identical to committed `HEAD`, which undermines trust in review output.

## Architectural Intent
- Preserve a single repository truth boundary for governance: `origin/main...HEAD`.
- Make review entry fail closed unless that truth boundary is valid at review time.
- Keep the contract explicit, narrow, and operator-readable.
- Prevent downstream governance from evaluating state that was never committed.

## Why This Story Exists
- Escalation, loop detection, and cost-control stories all depend on trustworthy review semantics.
- If review comments on workspace-only state while the contract says review is about committed diff, governance decisions become non-deterministic and misleading.
- This is therefore a P0 architectural invariant even though it can likely be implemented with a small patch.

## Likely Implementation Shape
- Add or strengthen a dirty-worktree guard in `review_story_run.sh` for the primary checkout before review begins.
- Reuse existing operator-guidance patterns where possible rather than inventing a new UX vocabulary.
- Keep downstream scripts aligned with the same boundary contract, but avoid broad refactors unless strictly necessary.
- Add focused tests proving both the blocked case and the happy path.

## Risks
- Duplicating preflight logic inconsistently with `run_story.sh`.
- Checking too many paths and producing false positives from runtime-only artifacts.
- Letting the patch drift into gate redesign or auto-commit territory.

## Acceptance Notes
- The committed-HEAD contract is explicit in both code behavior and docs.
- Review boundary semantics are deterministic.
- The implementation remains atomic and limited to the listed files.

