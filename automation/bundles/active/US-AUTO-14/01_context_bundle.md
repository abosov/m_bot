# US-AUTO-14: Context Bundle

## Source of Truth
- `automation/run_codex_task.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- active story bundle format with `02_file_scope.md`

## Current Code Reality
- `run_story.sh` resolves `automation/bundles/active/<STORY_ID>/03_master_prompt.md`, requires all seven bundle files, validates the bundle, and delegates to `automation/run_codex_task.sh`.
- `validate_story_bundle.sh` already enforces required sections for `02_file_scope.md`, so the file-scope structure exists and can be trusted as an input contract.
- `run_codex_task.sh` already:
  - runs Codex in an isolated worktree,
  - materializes tracked and untracked changes into the primary checkout,
  - collects `changed_files.txt`,
  - then runs pytest and review artifact generation.
- This means the natural insertion point for allowed-files enforcement is after `collect_git_artifacts` and before `run_pytest`.

## Architectural Intent
- Keep scope enforcement as a separate runtime guard layer.
- Reuse `02_file_scope.md` as the single source of truth for story scope.
- Keep matching simple and deterministic:
  - exact file path match
  - recursive directory match via `/**`
- Avoid overcomplicated glob engines in this story.
- Make the guard callable as a standalone script so it is testable outside the runner.

## Risks
- Existing or future bundles may use inconsistent scope notation if not normalized.
- Simple matching rules may need later expansion if stories require more advanced patterns.
- Untracked files must be included in scope checks because Codex may create new files.
- If the script parses markdown too loosely, content outside the allowed section could accidentally be treated as a pattern.

## Acceptance Notes
- The guard must fail on any changed file not covered by `## Files Allowed To Change`.
- The guard must ignore blank lines and markdown bullet syntax.
- The guard must stop parsing allowed patterns when the next markdown section begins.
- The runner integration must fail before pytest if allowed-files validation fails.

