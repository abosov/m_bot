# US-AUTO-19: Context Bundle

## Source of Truth
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/scripts/review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`

## Current Code Reality
- Run artifacts already exist under `automation/runs/<STORY_ID>/<RUN_ID>/`.
- Review, classification, and gate scripts already write their own artifacts.
- There is no single operator command that summarizes run state and artifact availability in one place.
- Debugging often requires manually opening multiple files.

## Architectural Intent
- Add one narrow read-only analysis layer for operator UX.
- Reuse existing artifact formats instead of redesigning them.
- Keep execution flow unchanged and avoid coupling this story to orchestration or retry behavior.

## Risks
- Over-parsing artifact content could make the script brittle.
- Treating missing artifacts as implied success would mislead the operator.
- Scope creep into orchestration, retries, or pipeline mutation must be avoided.

## Acceptance Notes
- The analysis command must remain read-only.
- It must tolerate incomplete runs and missing artifacts.
- It must produce a concise summary with a final operator-facing run status.

