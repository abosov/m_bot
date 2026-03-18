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

TASK_INTENT
[ONE SENTENCE: EXACT CHANGE AND WHY IT BELONGS TO THIS STORY]

OUT_OF_SCOPE
[EXACT ITEMS THAT MUST NOT BE CHANGED OR FIXED IN THIS RUN]

ATOMIC_TASK_ISOLATION
[STATE THE SINGLE PURPOSE OF THIS RUN, THE HARD SCOPE BOUNDARY, AND WHEN CODEX MUST STOP AND CREATE FOLLOW-UP WORK]

ATOMIC_TASK_ISOLATION_ENFORCEMENT
[STATE THAT ATOMIC TASK ISOLATION IS A MANDATORY CONTRACT FOR THIS RUN AND THAT CODEX MUST REFUSE IMPLEMENTATION IF THE PROMPT VIOLATES IT]

FOLLOW_UP_SPLIT_RULE
[IF REVIEW OR IMPLEMENTATION DISCOVERS MULTIPLE INDEPENDENT ISSUES, EACH ISSUE MUST BECOME ITS OWN FOLLOW-UP PROMPT; DO NOT BATCH THEM INTO THIS RUN]

FOLLOW_UP_CAPTURE_RULE
[ANY OUT-OF-SCOPE FINDING MUST BE RECORDED AS EXPLICIT FOLLOW-UP WORK IN THE OUTPUT; DO NOT IMPLEMENT IT IN THIS RUN]

EXECUTION_GATE
[IF THIS PROMPT IS MISSING OR LEAVES AMBIGUOUS THE INTENT, OUT_OF_SCOPE, ALLOWED/FORBIDDEN FILE BOUNDARIES, FOLLOW_UP_CAPTURE_RULE, HARD-STOP CONDITIONS, OR A SINGLE ATOMIC PURPOSE, CODEX MUST STOP AND REFUSE IMPLEMENTATION UNTIL THE PROMPT IS CORRECTED]

TASK_INTENT_DECLARATION
[BEFORE MAKING CHANGES, STATE THE ONE-SENTENCE TASK INTENT EXACTLY AS WRITTEN IN TASK_INTENT AND CONFIRM THAT NO OTHER INDEPENDENT CHANGE IS INCLUDED IN THIS RUN]

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

## ATOMIC TASK ISOLATION (MANDATORY)

You must strictly follow Atomic Task Isolation.
Atomic Task Isolation is a mandatory execution contract for this story run. If the prompt is missing any required contract field or includes more than one independently reviewable change, you must refuse implementation until the prompt is corrected.

### 1. One Task = One Purpose
- Implement ONLY the explicitly defined behavior of the story.
- If multiple concerns appear → STOP and report.
- This run must stay independently reviewable as one atomic change.
- If completion would require a second independently reviewable fix, stop and spin that work into a separate follow-up task.

### 2. No Scope Expansion
- DO NOT modify anything outside FILES_ALLOWED_TO_CHANGE.
- DO NOT modify FILES_THAT_MUST_NOT_CHANGE.
- DO NOT fix adjacent issues.
- If you see problems → report as follow-up tasks.
- Do NOT use this run to absorb cleanup, opportunistic hardening, or secondary fixes.

### 3. Explicit Intent Declaration
Before making changes, you MUST state:
- what exactly you are changing
- why this change is required for THIS story
- that this run contains no second independently reviewable change

### 4. Minimal Patch Rule
- Only minimal required diff is allowed.
- No refactoring unless explicitly requested.

### 5. Follow-up Task Protocol
If you detect issues outside scope, or multiple independent fixes are needed, you MUST stop that line of work and output one follow-up task per issue:

FOLLOW-UP TASK:
- Title:
- Problem:
- Suggested solution:
- Why it is out of scope for this story:

### 6. Hard Stop Condition
If task requires breaking these rules:
→ STOP and explain why task cannot be completed safely.
Do not continue by widening scope implicitly.
If this run reveals multiple independent fixes, implement none of the extra fixes here; emit one follow-up task per extra fix instead.
If the intent, out-of-scope, file-boundary, follow-up-capture, or hard-stop fields are missing or ambiguous, do not infer them; stop until the prompt is corrected.

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
- exact one-sentence task intent
- atomic task isolation statement
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

5. FOLLOW-UP TASKS (REQUIRED WHEN APPLICABLE)
- list every out-of-scope finding discovered during this run
- one follow-up task per finding (no batching)
- if none, state: `No out-of-scope findings discovered.`
