# Review Checklist — US-AUTO-48

## Scope Validation
- Confirm the patch changes only the AI review artifact contract and direct downstream handling
- Confirm rerun convergence logic from `US-AUTO-47` is untouched
- Confirm no unrelated workflow scripts are modified
- Confirm no unrelated docs or bundle packs are modified

## Functional Validation
- Confirm `ai_review_result.md` is explicitly validated before classification uses it
- Confirm malformed or missing normalized artifacts fail closed deterministically
- Confirm raw AI review output remains available for debugging
- Confirm classification and gate no longer rely on implicit normalized artifact presence
- Confirm analysis clearly reports the contract failure state

## Verification
- Run focused tests for AI review artifact handling
- Run focused tests for classification behavior
- Run focused tests for gate behavior
- Run focused tests for analysis/reporting if changed
- Confirm the relevant test subset passes without unrelated changes

