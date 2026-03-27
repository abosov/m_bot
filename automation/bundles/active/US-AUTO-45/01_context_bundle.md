# US-AUTO-45: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- Pinned run evidence under `automation/runs/<STORY_ID>/<RUN_ID>/`

## Current Code Reality
- The current review pipeline is supposed to allow operators to pin a run directory and then execute review, classification, and gate against that exact evidence set.
- In practice, the same pinned run can lead to different final outcomes: manual AI review plus classification may produce approve, while `review_gate_story_run.sh` later yields reject.
- This indicates the pinned run is not yet being treated as immutable source-of-truth evidence at the gate boundary.

## Architectural Intent
- Make review gate a strict consumer of already-produced pinned review artifacts.
- Preserve fail-closed behavior when evidence is missing or invalid.
- Preserve pinned-run selection via `AUTOMATION_RUN_DIR`.
- Preserve stale-run and head-consistency protections.
- Keep implementation limited to gate artifact consumption, operator analysis, tests, and docs.

## Risks
- If hidden fallback or recomputation logic still exists, nondeterminism may remain.
- If docs or analyze output still imply gate can regenerate upstream artifacts, operator behavior may remain inconsistent.
- If this story broadens into producer-script changes, it will exceed the intended scope.

## Acceptance Notes
- Bundle content must be fully resolved with no duplicated file sections and no placeholder tokens.
- Gate must consume existing pinned artifacts and must not implicitly regenerate them.
- Missing or invalid pinned artifacts must produce deterministic fail-closed behavior.
- Analyze and docs must align with the stricter pinned-artifact gate contract.
- Reverse sync and bundle-pack tooling changes remain out of scope for this story.

