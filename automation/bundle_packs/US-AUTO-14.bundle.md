# Story Bundle Pack
Story-ID: US-AUTO-14
Version: 1

=== FILE: 00_story.md ===
# US-AUTO-14: Allowed Files Guard

## Story ID and Title
- Story ID: `US-AUTO-14`
- Title: `Allowed Files Guard`

## Objective
Add a deterministic allowed-files guard that stops the Codex pipeline when the implementation changes files outside the scope explicitly declared in the active story bundle.

## Scope
- Add `automation/scripts/check_allowed_files.sh`.
- Parse the active story bundle file `02_file_scope.md`.
- Read the section `## Files Allowed To Change`.
- Support exact file paths and simple recursive wildcard patterns ending with `/**`.
- Compare the declared allowed paths against the actual changed files collected after Codex materialization.
- Fail fast if any changed file is outside the declared allowed scope.
- Integrate the guard into `automation/run_codex_task.sh` after worktree materialization and changed-files collection, but before pytest and downstream review steps.
- Add focused tests for the guard behavior.
- Update workflow docs/checklists only as needed for the new execution gate.

## Non-goals
- Do not add diff-size limits in this story.
- Do not add AI review gate logic in this story.
- Do not redesign story bundle validation structure.
- Do not change `finalize_story.sh`.
- Do not add background polling, retry loops, or GitHub Actions changes.
- Do not implement repository map injection changes here.

## Dependencies
- Existing bundle pack / materialization / validation flow.
- Existing `automation/run_codex_task.sh` execution flow with isolated worktree materialization.
- Existing active story bundles that define `02_file_scope.md`.
- Existing review / pytest artifact generation in the runner.

## Source of Truth
- `automation/run_codex_task.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/bundles/active/US-AUTO-14/02_file_scope.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Current Code Reality
- Story execution already validates the existence and structure of all seven bundle files before launching the runner.
- Bundle validation already requires `02_file_scope.md` to contain `## Files Allowed To Change` and `## Files Not Allowed To Change`.
- The runtime runner already materializes isolated worktree changes into the primary checkout and produces a deterministic changed-files artifact.
- There is currently no runtime scope enforcement after Codex writes changes, so Codex can still modify files outside the intended story boundary if they end up materialized into the main checkout.

## Target Outcome
- Every Codex story run is blocked if changed files exceed the explicit file scope declared by the story.
- The guard is deterministic, shell-based, and easy to audit.
- The failure message clearly shows which files violated scope.
- The runner fails before pytest / review if scope is violated.
- Allowed-files enforcement becomes a standard pipeline layer for all future stories.

=== FILE: 01_context_bundle.md ===
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

=== FILE: 02_file_scope.md ===
# US-AUTO-14: File Scope

## Files Allowed To Change
- `automation/scripts/check_allowed_files.sh`
- `automation/run_codex_task.sh`
- `tests/test_allowed_files_guard.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundle_packs/US-AUTO-14.bundle.md`
- `automation/bundles/active/US-AUTO-14/**`

## Files Not Allowed To Change
- `automation/scripts/finalize_story.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- `.github/workflows/**`

## Scope Notes
- Keep the guard runtime-only and deterministic.
- Do not mix in diff-size policy or AI review policy.
- Do not refactor unrelated runner behavior.
- Only exact paths and recursive directory patterns ending with `/**` are required in this story.

=== FILE: 03_master_prompt.md ===
# US-AUTO-14 PROMPT 1 — Allowed Files Guard

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Story
US-AUTO-14 — Allowed Files Guard.

## Goal
Implement a deterministic runtime guard that reads the active story bundle file scope and rejects Codex-generated changes outside the allowed file set before pytest and review continue.

## Source of Truth
- `automation/run_codex_task.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `automation/bundles/active/US-AUTO-14/02_file_scope.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`

## Files Allowed To Change
- `automation/scripts/check_allowed_files.sh`
- `automation/run_codex_task.sh`
- `tests/test_allowed_files_guard.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundle_packs/US-AUTO-14.bundle.md`
- `automation/bundles/active/US-AUTO-14/**`

## Files Not Allowed To Change
- `automation/scripts/finalize_story.sh`
- `automation/scripts/materialize_story_bundle.sh`
- `automation/scripts/validate_story_bundle.sh`
- `automation/scripts/run_story.sh`
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- `.github/workflows/**`

## Implementation Requirements
1. Add `automation/scripts/check_allowed_files.sh`.
2. The script must accept:
   - `STORY_ID`
   - optional path to changed-files list
   - optional path to bundle directory
3. The script must parse `02_file_scope.md` and extract patterns only from `## Files Allowed To Change`.
4. The parser must ignore:
   - blank lines
   - markdown bullet prefixes
   - inline backticks
5. The parser must stop when the next `## ` section starts.
6. Support matching:
   - exact file path
   - recursive directory pattern ending with `/**`
7. The script must fail if:
   - the bundle dir is missing
   - the scope file is missing
   - no allowed patterns are found
   - any changed file is outside the allowed scope
8. The failure output must list violating files clearly.
9. Integrate the script into `automation/run_codex_task.sh` after changed-files collection and before pytest.
10. Add focused tests covering:
   - exact path allowed
   - recursive directory allowed
   - violation detected
   - empty change list accepted
   - malformed / empty allowed section rejected
11. Keep implementation simple, explicit, and shell-first.

## Testing
Add or update focused tests that verify:
- allowed exact file passes
- allowed recursive directory passes
- out-of-scope file fails
- missing allowed rules fails
- runner gate executes before pytest

## Documentation
Update workflow docs/checklists only where needed to state that allowed-files guard is now part of the standard execution pipeline after Codex materialization.

## Output
Return:
1. changed files summary
2. design rationale
3. validation performed
4. risks / follow-ups
5. final diff

=== FILE: 04_review_checklist.md ===
# US-AUTO-14: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No diff-size guard logic was added
- [ ] No AI review gate logic was added
- [ ] No unrelated runner refactor was introduced
- [ ] No GitHub merge/finalization logic was changed

## Functional Validation
- [ ] Guard parses `## Files Allowed To Change` correctly
- [ ] Exact path matching works
- [ ] Recursive directory matching via `/**` works
- [ ] Out-of-scope changed files fail the run
- [ ] Empty changed-files input passes
- [ ] Guard runs before pytest in `automation/run_codex_task.sh`

## Architecture Validation
- [ ] `02_file_scope.md` remains the runtime source of truth for story scope
- [ ] Scope enforcement is a separate layer from bundle validation
- [ ] Scope enforcement is a separate layer from AI review and finalization
- [ ] Failure behavior is deterministic and fail-fast

## Verification
- [ ] Focused tests updated
- [ ] Manual story-run check performed
- [ ] Docs/checklist updated if needed
- [ ] Follow-ups captured separately

=== FILE: 05_followups.md ===
# US-AUTO-14: Follow-Ups

## Follow-Up Prompt Queue
- `US-AUTO-15` — Diff Size Guard
- `US-AUTO-16` — AI Review Gate
- `US-AUTO-17` — Repository Map Injection

## Iteration Notes
- Keep this story focused on file-scope enforcement only.
- Do not mix in diff-size thresholds here.
- Do not mix in semantic/AI review here.
- Keep matching intentionally small and deterministic in v1.

=== FILE: 06_manual_actions.md ===
# US-AUTO-14: Manual Actions

## Required Human Actions
- Run one real story through the pipeline with a valid in-scope diff.
- Run one negative check with a deliberately out-of-scope file and confirm fail-fast behavior.
- Inspect the failure message for clarity.
- Confirm the guard blocks the run before pytarts.

## Execution Notes
- Preferred verification path:
  - materialize the bundle
  - run the story on a feature branch
  - inspect `automation/runs/<STORY_ID>/<RUN_ID>/changed_files.txt`
  - confirm allowed-files validation behavior against real runner artifacts

## Completion Status
- [ ] No manual actions required
- [ ] Manual actions completed and documented
