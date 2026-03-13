# US-AUTO-1 — Story bundle bootstrap automation

## Goal
Add a script that creates a new active story bundle from reusable templates.

## Scope
- Add `automation/scripts/new_story_bundle.sh`
- Reuse existing templates under `automation/templates/`
- Optionally make minimal documentation updates in `docs/90_codex/`

## Non-goals
- No changes to runtime Zumbot logic
- No review-loop automation in this story
- No CI/CD or deploy changes
- No changes to `automation/run_codex_task.sh`
