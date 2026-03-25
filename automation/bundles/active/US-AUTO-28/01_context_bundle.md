# Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- current behavior in:
  - `automation/scripts/run_story.sh`
  - `automation/scripts/review_story_run.sh`
  - `automation/scripts/classify_review_story_run.sh`
  - `automation/scripts/review_gate_story_run.sh`
  - `automation/scripts/analyze_story_run.sh`
  - `automation/scripts/finalize_story.sh`

## Current Code Reality
The pipeline now has stronger run/review/gate fidelity and an explicit commit handoff before run, but repeated reject cycles can still happen when the system keeps rejecting the same story without meaningful progress. The current system can fail closed, but it does not yet provide a deterministic governance handoff path when repeated reject outcomes represent stagnation rather than an ordinary implementation defect.

## Architectural Intent
Introduce a small deterministic escalation layer above ordinary reject handling. The system must distinguish between:
- ordinary reject, where constrained follow-up work may continue
- repeated reject stagnation, where automated continuation must stop and a human must choose the next governance action

The first version should remain simple, auditable, and fail-closed.

## Risks
- false-positive escalation if stagnation criteria are too broad
- accidental weakening of review gate if escalation is treated like approval
- operator ambiguity if escalation actions are not explicit
- evidence drift if escalation is not tied to concrete reviewed run / HEAD metadata

## Acceptance Notes
A valid outcome for this story should include:
- deterministic escalation criteria
- explicit escalation-required state
- blocked automatic continuation after escalation
- explicit human resolution path:
  - accept-as-is
  - force-followup
  - abort
- updated analysis/remediation messaging
- focused tests and documentation updates

