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

ATOMIC_TASK_ISOLATION_ENFORCEMENT
[STATE THAT ATOMIC TASK ISOLATION IS A MANDATORY CONTRACT FOR THIS FOLLOW-UP RUN AND THAT CODEX MUST REFUSE IMPLEMENTATION IF THE PROMPT TARGETS MORE THAN ONE FINDING OR OMITS REQUIRED ISOLATION FIELDS]

FOLLOW_UP_INPUT_RULE
[LIST EXACTLY ONE REVIEW FINDING OR ONE BLOCKER HERE; IF REVIEW FOUND MULTIPLE ISSUES, SPLIT THEM INTO MULTIPLE FOLLOW-UP PROMPTS BEFORE EXECUTION]

FOLLOW_UP_CAPTURE_RULE
[IF THIS FIX REVEALS ANOTHER INDEPENDENT ISSUE, RECORD IT AS A SEPARATE FOLLOW-UP TASK AND DO NOT IMPLEMENT IT IN THIS RUN; FOLLOW-UP PROMPTS ARE NOT AN EXCEPTION PATH AROUND ATOMIC TASK ISOLATION]

EXECUTION_GATE
[IF THIS FOLLOW-UP DOES NOT TARGET EXACTLY ONE FINDING/BLOCKER OR IS MISSING OR LEAVES AMBIGUOUS THE TARGET FINDING, INTENT, OUT_OF_SCOPE, ALLOWED/FORBIDDEN FILE BOUNDARIES, FOLLOW_UP_CAPTURE_RULE, OR HARD-STOP CONDITIONS, OR IF IT BATCHES A SECOND INDEPENDENTLY REVIEWABLE FIX, CODEX MUST STOP AND REFUSE IMPLEMENTATION UNTIL THE FOLLOW-UP PROMPT IS SPLIT OR CORRECTED]

TASK_INTENT_DECLARATION
[BEFORE MAKING CHANGES, STATE THE ONE-SENTENCE FOLLOW-UP INTENT EXACTLY AS WRITTEN IN FOLLOW-UP_INTENT AND CONFIRM THAT NO SECOND FINDING OR INDEPENDENT CHANGE IS INCLUDED IN THIS RUN]

TASK
Implement only the required fixes.

OUTPUT FORMAT

1. FIX PLAN
Before making changes, state:
- the exact failing issue being fixed
- why this fix is the minimum sufficient fix
- what is explicitly out of scope
- the atomic task isolation statement for this follow-up
- the one-sentence follow-up intent exactly as written in `FOLLOW-UP_INTENT`

2. PATCH SUMMARY

3. TEST IMPACT

4. DOC IMPACT

5. FOLLOW-UP TASKS (REQUIRED WHEN APPLICABLE)
- if additional out-of-scope findings are discovered, record each as its own follow-up task
- do not implement those additional findings in this run
- if none, state: `No additional follow-up tasks created.`

## ATOMIC TASK ISOLATION (FOLLOW-UP MODE)

You are working in follow-up mode. The same Atomic Task Isolation rules apply, with stricter constraints.
Atomic Task Isolation is a mandatory execution contract for this follow-up run. If the prompt targets more than one finding or omits required isolation fields, you must refuse implementation until it is corrected.
Follow-up mode is not an exception path around the contract; one follow-up prompt still equals one independently reviewable finding or blocker.

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
→ If the target finding, intent, out-of-scope, file-boundary, follow-up-capture, or hard-stop fields are missing or ambiguous, stop instead of inferring them
