# US-AUTO-16: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/90_codex/REVIEW_CLASSIFICATION_RULES.md`

## Current Code Reality
- Review artifacts are already produced in `automation/runs/<STORY_ID>/<RUN_ID>/`.
- AI review already writes `ai_review_result.md`.
- Classification already writes `review_classification.md`.
- No script currently converts these artifacts into a single gate result for downstream automation.
- `finalize_story.sh` is still independent from AI review classification.

## Architectural Intent
Build a narrow review gate layer on top of existing artifacts and scripts:
- orchestrate existing review steps,
- produce one final decision artifact,
- preserve clean boundaries,
- avoid coupling to finalization until a follow-up story.

## Risks
- Free-form LLM output can be ambiguous unless the gate decision is normalized.
- Parsing logic must fail closed if recommendation is absent or malformed.
- Scope creep into finalize/merge blocking must be avoided in this story.

## Acceptance Notes
- One entrypoint script owns review gate orchestration.
- Review result + classification result remain readable artifacts.
- Gate decision is machine-readable and stable for future automation.

