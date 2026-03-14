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
