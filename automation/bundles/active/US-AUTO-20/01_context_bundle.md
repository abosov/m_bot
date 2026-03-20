# US-AUTO-20: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/run_codex_task.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`

## Current Code Reality
- The repository already supports discrete automation stages:
  - story execution,
  - AI review,
  - review classification,
  - review gate,
  - run analysis.
- The operator still has to infer the next step manually from scattered run artifacts and existing scripts.
- `analyze_story_run.sh` already contains important consistency and staleness checks, so this story should build on that reality rather than inventing a parallel model.

## Architectural Intent
- Add orchestration guidance, not orchestration automation.
- Reuse existing artifacts and stage semantics instead of inventing a new execution model.
- Make the safe next step obvious and deterministic from repository evidence.
- Prefer a small explicit stage model and fail-closed behavior.

## Risks
- The implementation could accidentally duplicate logic already present in run analysis instead of reusing it.
- The workflow helper could become too broad and drift into general operator UX work.
- Resume output could be misleading if it does not clearly distinguish valid evidence from stale evidence.

## Acceptance Notes
- One canonical helper path must exist for “what do I do next?”
- The helper must emit one next recommended action or a blocked reason.
- The helper must support safe resume from the latest valid stage.
- Missing or stale evidence must stop continuation explicitly.

