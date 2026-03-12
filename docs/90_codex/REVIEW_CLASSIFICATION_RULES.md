# REVIEW CLASSIFICATION RULES

## Purpose
Classify review findings consistently and route them to the correct action path.

## MERGE BLOCKER
Use when issue must be fixed before merge.

Criteria:
- Breaks stated story acceptance criteria.
- Violates architecture/source-of-truth constraints.
- Introduces security risk, secret exposure, or unsafe permissions.
- Causes failing tests in changed scope.
- Includes forbidden file changes or scope violations.
- Creates high-likelihood production incident risk.

Action:
- Fix in current story branch via follow-up prompt(s).
- Re-run tests and re-review before merge.

## MINOR IMPROVEMENT
Use when quality can improve but current behavior is acceptable for merge.

Criteria:
- Readability/maintainability improvement with low risk.
- Non-critical test/documentation enhancement.
- Small ergonomics issue with no acceptance impact.
- Internal cleanup that does not alter external behavior.

Action:
- Fix now if cheap and low-risk.
- Otherwise track as optional post-merge task.

## FOLLOW-UP STORY
Use when work is valid but out of current atomic scope.

Criteria:
- Requires new product/architecture decision not in current story.
- Spans additional layers beyond allowed file scope.
- Depends on future story ordering or external dependency.
- Significant effort that would violate atomic delivery.

Action:
- Do not expand current implementation scope.
- Create a new story bundle with explicit objective/dependencies.

## Tie-break Rule
If uncertain between `MERGE BLOCKER` and `MINOR IMPROVEMENT`, classify as `MERGE BLOCKER` until risk is resolved.
