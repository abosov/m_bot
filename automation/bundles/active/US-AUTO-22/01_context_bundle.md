# US-AUTO-22: Context Bundle

## Source of Truth
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/STORY_BUNDLE_SPEC.md`
- `docs/40_ai/zumbot_codex/MASTER_PROMPT_TEMPLATE.md`
- `docs/40_ai/zumbot_codex/FOLLOWUP_PROMPT_TEMPLATE.md`

## Current Code Reality
- The source-of-truth Codex workflow docs already state Atomic Task Isolation as a mandatory contract, but the template and bundle language still needs alignment so that the same rule is explicit and audit-ready at execution time.
- Story bundle workflow already expects explicit scope and source-of-truth discipline, so this change should strengthen existing behavior rather than introduce a new process family.

## Architectural Intent
- Make Atomic Task Isolation an explicit workflow contract across story prompts and follow-up prompts.
- Treat missing Atomic Task Isolation fields or multi-purpose prompts as execution blockers rather than review-time suggestions.
- Keep the implementation documentation-only in this story.
- Defer any shell enforcement or runtime automation to a separate future story.
- Make Codex restate the exact one-sentence task or follow-up intent before edits so reviewers can verify that the run stayed atomic.
- Require the executable prompt to stop when required intent, out-of-scope, file-boundary, follow-up-capture, or hard-stop fields are missing or ambiguous.
- Make follow-up prompts state explicitly that follow-up mode is not an exception path around Atomic Task Isolation and cannot batch a second independently reviewable fix.

## Risks
- If wording is too vague, Codex may continue to broaden scope despite the new rule.
- If this story drifts into automation-script changes, it will violate its own isolation contract.

## Acceptance Notes
- Bundle content must be fully resolved with no canonical placeholder tokens.
- Materialized files must clearly express allowed scope, forbidden scope, and hard stop conditions.
- Master and follow-up prompts must require a one-sentence intent declaration before edits and must state that Atomic Task Isolation is a mandatory execution contract.
- Follow-up prompts must explicitly reject any attempt to use follow-up mode to batch a second independently reviewable fix.
- The resulting story must remain documentation/prompt-template only.
