# US-AUTO-2: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `automation/run_codex_task.sh`
- `automation/scripts/new_story_bundle.sh`

## Current Code Reality
- The existing pipeline is launched by passing a master prompt path directly to `automation/run_codex_task.sh`
- Active stories live under `automation/bundles/active/<STORY_ID>/`
- Each active story bundle is expected to contain `00_story.md` through `06_manual_actions.md`
- `US-AUTO-1` already automated bundle creation, but launch is still path-based rather than story-based

## Target Architecture
- Add a thin launcher script that accepts `STORY_ID`
- The launcher resolves `automation/bundles/active/<STORY_ID>/03_master_prompt.md`
- The launcher performs lightweight preflight checks for missing bundle / missing required files
- The launcher delegates actual execution to `automation/run_codex_task.sh`
- `run_codex_task.sh` remains the execution source of truth

## Risks
- Duplicating validation or execution logic that already belongs in `run_codex_task.sh`
- Making the launcher overly clever instead of keeping it as a thin wrapper
- Poor error messages could make failed launches harder to debug

## Acceptance Notes
- The launcher succeeds for a valid existing story bundle
- The launcher fails clearly for a missing story id or missing bundle
- The launcher fails clearly if `03_master_prompt.md` is missing
- The launcher does not modify unrelated files
- Manual verification should include at least one successful invocation and one failing invocation
