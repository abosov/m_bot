# Zumbot Codex Review Prompt Template

[USER STORY ID / REVIEW]

Review this diff strictly against the approved user story and Zumbot project rules.

GOALS
- detect scope creep
- detect architectural violations
- detect hidden regressions
- detect missing tests
- detect missing docs
- detect unsafe assumptions
- detect broken layer boundaries
- detect places where Codex changed more than necessary

USER STORY
[PASTE USER STORY HERE]

PROJECT CONTEXT
docs/40_ai/zumbot_codex/PROJECT_CONTEXT.md

REVIEW RULES
- Be strict.
- Prefer minimal, precise criticism.
- Do not suggest broad refactors.
- Focus on correctness, scope control, maintainability, safety, and story compliance.

CHECKLIST
1. Does the diff solve the requested story and only that story?
2. Are changed files justified?
3. Were any unrelated files touched?
4. Are source-of-truth rules respected?
5. Are architectural boundaries respected?
6. Are state transitions and business logic explicit?
7. Are tests sufficient and focused?
8. Are docs updated where required?
9. Are there rollback or deployment implications?
10. What exact follow-up changes are required before merge?

OUTPUT FORMAT

1. VERDICT
- approve
- needs changes

2. FINDINGS
- critical
- medium
- minor

3. REQUIRED FIXES
- exact actionable fixes only

4. OPTIONAL IMPROVEMENTS
- only if truly useful and in-scope
