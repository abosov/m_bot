# Context Bundle

## Why this story exists
Current workflow still requires manual creation of the active story bundle structure before `run_codex_task.sh` can be used.

## Current pain
Manual bootstrap includes creating the story folder and multiple required markdown files by hand.

## Desired outcome
A single script should create the active story bundle structure with prefilled editable files so a new story can be started quickly and consistently.

## Relevant source of truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `automation/run_codex_task.sh`
- `automation/templates/*`
