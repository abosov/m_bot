# Zumbot Codex Follow-up Prompt Template

[USER STORY ID / FOLLOW-UP N]

Apply only the required fixes from review.

DO NOT expand scope.
DO NOT refactor unrelated code.
DO NOT touch files outside the allowed set unless explicitly required by a listed fix.

CONTEXT

Original user story:
[PASTE SHORT VERSION]

Review findings:
[PASTE REQUIRED FIXES]

FOLLOW_UP_TARGET_FINDING
[EXACTLY ONE FINDING ID OR ONE BLOCKER LABEL FROM REVIEW INPUT; THIS FOLLOW-UP MAY NOT ADDRESS MORE THAN THIS ONE TARGET]

FILES_ALLOWED_TO_CHANGE
[EXACT FILES]

FILES_THAT_MUST_NOT_CHANGE
[EXACT FILES OR AREAS]

FOLLOW-UP_INTENT
[ONE SENTENCE: EXACT FIX AND WHY IT BELONGS TO THIS FOLLOW-UP]

OUT_OF_SCOPE
[EXACT ITEMS THAT MUST NOT BE CHANGED IN THIS FOLLOW-UP]

ATOMIC_TASK_ISOLATION
[STATE THE SINGLE REVIEW FINDING OR BLOCKER BEING FIXED, THE HARD SCOPE BOUNDARY, AND WHEN CODEX MUST STOP AND SPIN OUT ANOTHER FOLLOW-UP]

FOLLOW_UP_INPUT_RULE
[LIST EXACTLY ONE REVIEW FINDING OR ONE BLOCKER HERE; IF REVIEW FOUND MULTIPLE ISSUES, SPLIT THEM INTO MULTIPLE FOLLOW-UP PROMPTS BEFORE EXECUTION]

EXECUTION_GATE
[IF THIS FOLLOW-UP DOES NOT TARGET EXACTLY ONE FINDING/BLOCKER OR IS MISSING INTENT, OUT_OF_SCOPE, OR FILE BOUNDARIES, CODEX MUST STOP AND REFUSE IMPLEMENTATION UNTIL THE FOLLOW-UP PROMPT IS SPLIT OR CORRECTED]

TASK
Implement only the required fixes.

OUTPUT FORMAT

1. FIX PLAN
Before making changes, state:
- the exact failing issue being fixed
- why this fix is the minimum sufficient fix
- what is explicitly out of scope
- the atomic task isolation statement for this follow-up

2. PATCH SUMMARY

3. TEST IMPACT

4. DOC IMPACT

5. FOLLOW-UP TASKS (REQUIRED WHEN APPLICABLE)
- if additional out-of-scope findings are discovered, record each as its own follow-up task
- do not implement those additional findings in this run
- if none, state: `No additional follow-up tasks created.`

## ATOMIC TASK ISOLATION (FOLLOW-UP MODE)

You are working in follow-up mode. The same Atomic Task Isolation rules apply, with stricter constraints.

### 1. Do NOT expand original scope
- You must ONLY address the exact issue from the previous run.
- Do NOT introduce new behavior.
- Do NOT fix adjacent or newly discovered problems.
- This follow-up must stay independently reviewable as one atomic fix.
- If the review listed multiple independent findings, this prompt may carry only one of them.

### 2. Fix only the minimal cause
- Identify the smallest possible fix.
- Do NOT refactor.
- Do NOT improve structure unless strictly required.

### 3. Respect original boundaries
- Do NOT modify files outside FILES_ALLOWED_TO_CHANGE.
- Do NOT modify FILES_THAT_MUST_NOT_CHANGE.
- Even inside allowed files, do NOT touch unrelated logic.

### 4. No cascade fixes
- If fixing one issue reveals another:
  → STOP
  → Report it as FOLLOW-UP TASK
  → Do NOT fix it in the same run

If the current issue cannot be resolved without a second independent change:
  → STOP
  → Create a new follow-up prompt for that second change
  → Do NOT batch both fixes here

FOLLOW-UP TASK:
- Title:
- Problem:
- Suggested solution:
- Why it is out of scope for this follow-up:

### 5. Mandatory failure containment
- Your goal is to make the current run pass, not to improve the system.
- If the pass condition requires a second independent fix, stop and create another follow-up prompt.

### 6. Hard stop condition
If the fix requires:
- touching multiple concerns
- changing architecture
- modifying unrelated logic

→ STOP and explain why a new story is required
→ Do not widen this follow-up to absorb the second issue; record that issue as a separate follow-up task instead
