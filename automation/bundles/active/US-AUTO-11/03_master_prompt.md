# US-AUTO-11 PROMPT 1 — Repository Map Injection

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Story
US-AUTO-11 — Repository Map Injection for Codex runs.

## Goal
Inject a dle repository map artifact into every Codex run so the model receives a stable architectural view of the repository before implementation starts.

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/40_ai/zumbot_codex/REPOSITORY_MAP.md`
- `docs/40_ai/zumbot_codex/PROJECT_CONTEXT.md`
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`

## Files Allowed To Change
- `automation/run_codex_task.sh`
- `tests/test_run_codex_task.py`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `automation/bundles/active/US-AUTO-11/**`

## Files Not Allowed To Change
- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- `.github/**`
- unrelated automation scripts

## Implementation Requirements
1. Add a repository map generation step before Codex execution.
2. Create a new run artifact:
   - `repository_map_runtime.md`
3. Make `story_context.md` explicitly reference the repository map artifact.
4. Add manifest metadata showing repository map injection status.
5. Keep the repository map generation lightweight and deterministic.
6. Reuse existing curated docs where practical instead of inventing new architecture.
7. Do not implement allowed-files guard or review gate logic in this story.

## Testing
Add or update focused tests that verify:
- repository map artifact is generated
- manifest records repository map injection
- story context references repository map artifact

## Documentation
Update `docs/90_codex/STORY_EXECUTION_CHECKLIST.md` to mention repository map injection as a mandatory run artifact.

## Output
Return:
1. changed files summary
2. design rationale
3. validation performed
4. risks / follow-ups
5. final diff
