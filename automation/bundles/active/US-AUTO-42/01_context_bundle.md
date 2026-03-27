# US-AUTO-42: Context Bundle

## Source of Truth
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/bundle_packs/US-AUTO-28.bundle.md`

## Current Code Reality
- The pipeline now has a stable execution chain around committed artifacts and deterministic review boundaries.
- `US-AUTO-28` exposed a narrower remaining governance bug: escalation resolution handling in `run_story.sh` is not yet fully fail-closed for invalid resolution input.
- The registry explicitly identifies `US-AUTO-42` as the next recommended atomic fix for this gap.
- This story should be implemented as a narrow follow-up, not as a continuation of the broader `US-AUTO-28` scope.

## Architectural Intent
- Treat escalation resolution as a governance gate, not a best-effort hint.
- Require valid, explicit operator-approved resolution input before continuing.
- Prefer deterministic stop behavior over silent continuation.
- Keep the boundary narrow: fix only invalid-resolution handling in `run_story.sh`, with focused tests and minimal docs updates.

## Risks
- Scope creep into broader escalation orchestration.
- Reintroducing fail-open behavior through implicit defaults.
- Updating tests incompletely so only one invalid-input class is covered.
- Documentation drifting from the actual runtime contract.

## Acceptance Notes
- The implementation remains confined to the atomic defect.
- The runtime contract becomes stricter, not looser.
- The operator receives deterministic remediation when escalation input is invalid.
- New out-of-scope findings are captured as follow-ups instead of being fixed inline.

