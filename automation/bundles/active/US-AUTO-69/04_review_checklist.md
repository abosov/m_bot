## Scope Validation
APPROVE only if:
- changed files are limited to the four allowed files
- the implementation remains strictly about companion-artifact execution filtering for code-only stories
- no review-stage, analyze-stage, registry, telemetry, or UX logic was changed
- no scope widening was introduced

REJECT if:
- any unlisted file changed
- the implementation broadens into general scope-policy redesign
- registry mutation or registry auto-handling was added
- the story solves more than the execution-filtering defect

## Functional Validation
APPROVE only if:
- recognized companion registry/doc edits are filtered from the effective execution review surface
- a code-only run no longer fails solely because of those recognized companion edits
- non-companion out-of-scope edits still fail hard
- mixed companion and non-companion extra edits still fail hard
- behavior is deterministic and fail-closed for ambiguous cases

REJECT if:
- companion artifacts are treated as generally allowed scope
- unknown paths are silently ignored
- mixed cases pass
- filtering affects unrelated workflow phases
- changed-files and execution diff surface become inconsistent

## Verification
Required evidence:
- passing targeted tests in `tests/test_run_story.py`
- passing targeted tests in `tests/test_run_codex_task.py`

HARD BLOCK:
- REJECT if tests were not run
- REJECT if assertions do not cover companion-only allow, non-companion reject, and mixed-case reject
- REJECT if the implementation relies on manual operator steps instead of deterministic code behavior

Binary review result:
- APPROVE
- REJECT

