# US-AUTO-46 PROMPT 1 — Review Boundary Must Use Committed HEAD Only

## Role
You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Story
US-AUTO-46 — Review operates strictly on committed HEAD.

## Goal
Introduce a fail-closed review-boundary contract so `review_story_run.sh` and downstream governance steps analyze only committed repository state and refuse review when workspace-only changes would make review semantically diverge from `origin/main...HEAD`.

## Source of Truth
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Files Allowed To Change
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `tests/test_review_story_run.py`
- `tests/test_analyze_story_run.py`
- `automation/bundle_packs/US-AUTO-46.bundle.md`
- `automation/bundles/active/US-AUTO-46/**`

## Files Not Allowed To Change
- `automation/run_codex_task.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/escalate_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `docs/40_ai/**`
- `backend/**`
- `frontend/**`
- `database/**`
- `scripts/migrations/**`

## Implementation Requirements
1. Add the smallest possible committed-HEAD review precondition at review entry.
2. The guard must fail closed when workspace-only changes would make review semantically diverge from committed `HEAD`.
3. The blocked path must explain the exact remediation expectation to the operator.
4. The contract must remain aligned with `origin/main...HEAD` as the review source of truth.
5. Do not add auto-commit behavior.
6. Do not redesign `run_story.sh`.
7. Do not redesign gate logic or escalation policy.
8. Do not modify `automation/run_codex_task.sh`.
9. Add focused regression tests for:
   - blocked review when relevant workspace changes exist;
   - successful review path when checkout is clean;
   - analyze output remains coherent with the new boundary contract if touched.
10. Update documentation so review/classify/gate explicitly operate on committed repository state only.

## Testing
Add or update focused tests that verify:
- review is blocked on relevant uncommitted workspace divergence;
- review succeeds on a clean checkout;
- operator messaging is deterministic and actionable;
- analyze output stays coherent if touched.

## Documentation
Update workflow docs/checklists only where needed to state that review/classify/gate operate on committed repository state only and fail closed when workspace reality diverges from committed `HEAD`.

## Output
Return:
1. changed files summary
2. implementation rationale
3. exact review-boundary guard behavior
4. tests run and results
5. risks or follow-ups discovered but not implemented
6. final diff summary

## Atomic Task Isolation Contract
Atomic Task Isolation is a mandatory execution contract for this run.

You must:
1. Declare the one-sentence task intent before making changes.
2. Keep the patch limited to committed-HEAD review fidelity.
3. Treat any unrelated issue as follow-up work, not inline scope expansion.
4. Stop immediately if the fix requires runner redesign, auto-commit, or multiple independent findings.
5. Record new out-of-scope discoveries as explicit follow-ups instead of folding them into this patch.
6. Treat follow-up prompts as non-exceptional continuations that must also remain atomic.
7. Refuse to proceed if the task becomes non-atomic, underspecified, or split across multiple independent findings.

## Hard Stop Condition
If you discover that this cannot be implemented without changing runner semantics, adding auto-commit, or combining multiple independent review findings, stop and report that the story must be split rather than widening this patch.

