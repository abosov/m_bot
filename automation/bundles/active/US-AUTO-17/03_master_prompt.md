# US-AUTO-17 PROMPT 1 — Repository Map Injection v2

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Goal
Upgrade runtime repository-map injection so Codex receives stronger anti-hallucination architecture context before implementation starts.

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
- `automation/bundle_packs/US-AUTO-17.bundle.md`
- `automation/bundles/active/US-AUTO-17/**`

## Files Not Allowed To Change
- `automation/scripts/check_allowed_files.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/finalize_story.sh`
- `backend/**`
- `migrations/**`
- `.github/workflows/**`

## Output
1. changed files summary
2. design rationale
3. validation performed
4. risks / follow-ups
5. final diff

## Implementation Requirements
1. Extend `generate_repository_map_runtime()` so the runtime artifact includes an explicit `Architecture Layers` section.
2. Add a `Story-Local Context` section derived from the active story bundle when one exists. At minimum surface:
   - story id
   - active bundle path
   - files allowed to change
   - files not allowed to change (if present and parseable)
3. Add an `Anti-Hallucination Rules` section with compact rules such as:
   - do not invent files
   - do not broaden scope
   - edit only allowed files for this story
   - if source-of-truth docs conflict, stop and report before broad changes
4. Add a `Pipeline Dependency Hints` section that explains the artifact relationships for the automation flow.
5. Keep generation deterministic and lightweight. Do not add non-deterministic scanning or heavyweight repository analysis.
6. Preserve existing manifest metadata and existing prompt/story-context references to the repository-map artifact.
7. Update focused tests to verify the new injected sections.
8. Update `docs/90_codex/STORY_EXECUTION_CHECKLIST.md` so the stronger repository map is part of the expected run artifact.

## Testing
- `pytest tests/test_run_codex_task.py`

## Documentation
- Update only the docs required by the story scope.

