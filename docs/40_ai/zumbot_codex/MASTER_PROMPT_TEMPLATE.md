# Zumbot Codex Master Prompt Template

[USER STORY ID / PROMPT ID]

You are implementing a single scoped change for the Zumbot repository.

Follow the Zumbot Codex Operating System and zumbot-user-story-workflow skill principles.

PROJECT CONTEXT
- Read and follow the repository project context file.
- Read and follow the repository structure map.
- Respect all architectural boundaries and source-of-truth rules.
- Minimal patch only.

REQUIRED CONTEXT FILES
- docs/40_ai/zumbot_codex/PROJECT_CONTEXT.md
- docs/40_ai/zumbot_codex/REPOSITORY_MAP.md

USER STORY
[PASTE USER STORY HERE]

PROJECT CONTEXT FILE
docs/40_ai/zumbot_codex/PROJECT_CONTEXT.md

FILES_ALLOWED_TO_CHANGE
[EXACT FILE PATHS OR GLOBS]

FILES_THAT_MUST_NOT_CHANGE
[EXACT FILE PATHS OR AREAS]

BEFORE IMPLEMENTING
1. Identify the exact existing files to modify.
2. Identify the exact symbols, routes, handlers, services, models, migrations, tests, scripts, or components involved.
3. State the source of truth for this change.
4. State what must not be changed.
5. State whether new files are strictly necessary.

IMPLEMENTATION RULES
- Minimal patch only.
- No unrelated refactor.
- No formatting-only edits.
- No drive-by fixes.
- No speculative cleanup unless directly required by the story.
- Do not touch files outside FILES_ALLOWED_TO_CHANGE.
- Reuse existing patterns in the repo.
- Preserve backward compatibility unless the story explicitly changes a contract.

DATABASE / API / DOMAIN RULES
- SQL migrations are the source of truth for DB schema.
- Do not infer schema changes outside migrations.
- Keep business logic in the correct service/domain layer.
- Do not hide business decisions inside routes or handlers.
- Make state transitions explicit.
- Preserve idempotency and transactional safety where relevant.

TESTING RULES
- Add or update focused tests for the changed behavior.
- Prefer the smallest sufficient test surface.
- Do not rewrite unrelated tests.
- Reuse existing test patterns and fixtures.

DOCUMENTATION RULES
- Update user story / architecture / operations docs when behavior or contracts change.
- Keep docs aligned with implementation.

OUTPUT FORMAT

1. IMPLEMENTATION PLAN
- exact files to modify
- exact symbols/components/routes involved
- source of truth
- non-goals
- risks/assumptions

2. PATCH SUMMARY
- what changed
- why
- what did not change

3. TEST PLAN
- tests added/updated
- manual checks to run

4. DOC UPDATES
- exact docs to update
