# US-AUTO-4: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `automation/run_codex_task.sh`

## Current Code Reality
- `automation/run_codex_task.sh` assembles a story context before calling `codex exec`
- Bundle files include both execution-critical content and human/process-oriented content
- Not all bundle files are equally useful for every Codex implementation run

## Target Architecture
- Introduce lean context as the default execution mode
- Keep full context available via explicit flag
- Record selected context files into run artifacts for traceability
- Preserve existing story-id derivation and artifact generation behavior

## Risks
- Under-including context for complex stories
- Breaking existing run flow if argument parsing is careless
- Making the mode-selection logic harder to understand than necessary

## Acceptance Notes
- Lean mode includes only the minimal default bundle files
- Full mode includes the whole bundle
- Run artifacts show exactly which files were selected
