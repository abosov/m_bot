# US-AUTO-22: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/40_ai/zumbot_codex/MASTER_PROMPT_TEMPLATE.md`
- `docs/40_ai/zumbot_codex/FOLLOWUP_PROMPT_TEMPLATE.md`

## Current Code Reality
- The Codex workflow already contains some scope-control language, but the contract is fragmented between templates and not stated as a single mandatory Atomic Task Isolation rule.
- Story bundle workflow already expects explicit scope and source-of-truth discipline, so this change should strengthen existing behavior rather than introduce a new process family.

## Architectural Intent
- Make Atomic Task Isolation an explicit workflow contract across story prompts and follow-up prompts.
- Treat missing Atomic Task Isolation fields or multi-purpose prompts as execution blockers rather than review-time suggestions.
- Keep the implementation documentation-only in this story.
- Defer any shell enforcement or runtime automation to a separate future story.
- Make Codex restate the exact one-sentence task or follow-up intent before edits so reviewers can verify that the run stayed atomic.

## Risks
- If wording is too vague, Codex may continue to broaden scope despite the new rule.
- If this story drifts into automation-script changes, it will violate its own isolation contract.

## Acceptance Notes
- Bundle content must be fully resolved with no canonical placeholder tokens.
- Materialized files must clearly express allowed scope, forbidden scope, and hard stop conditions.
- Master and follow-up prompts must require a one-sentence intent declaration before edits and must state that Atomic Task Isolation is a mandatory execution contract.
- The resulting story must remain documentation/prompt-template only.

