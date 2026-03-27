# US-AUTO-46 — Review operates strictly on committed HEAD

## Story ID and Title
- **Story ID:** `US-AUTO-46`
- **Title:** `Review operates strictly on committed HEAD`

## Objective
Enforce branch fidelity at the review boundary so `review_story_run.sh` and downstream review/classification/gate steps operate only on committed repository state and fail closed when workspace-only changes would make review semantically diverge from `origin/main...HEAD`.

## Scope
- Add a deterministic pre-review guard that blocks review when the primary checkout contains uncommitted changes relevant to repository state.
- Ensure the guard explains the exact remediation path to the operator.
- Add focused regression tests for the committed-HEAD review contract.
- Update workflow documentation so the canonical sequence is explicit at the review boundary as well as the run boundary.
- Materialize the story bundle for US-AUTO-46.

## Non-goals
- Do not redesign the runner pipeline.
- Do not introduce auto-commit behavior.
- Do not relax the clean-tree contract anywhere.
- Do not change merge recommendation semantics.
- Do not redesign AI review prompts or classifier logic beyond what is required for the committed-HEAD contract.
- Do not implement escalation policy changes.
- Do not modify Codex execution internals in `automation/run_codex_task.sh`.

## Dependencies
- `US-AUTO-41` commit-before-run handoff contract.
- `US-AUTO-44` dirty-path operator guidance.
- `US-AUTO-45` deterministic gate reuse.
- Existing review/classification/gate flow and run artifact contract.

## Source of Truth
- `automation/scripts/review_story_run.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/run_story.sh`
- `docs/90_codex/STORY_EXECUTION_CHECKLIST.md`
- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`

## Current Code Reality
- `run_story.sh` already enforces a clean-tree precondition before execution.
- `US-AUTO-41` established the canonical handoff `materialize -> commit_story_artifacts -> run_story`.
- `US-AUTO-45` made gate reuse deterministic for pinned upstream artifacts.
- A remaining architectural gap exists at the review boundary: review can become semantically unreliable if implementation reality exists only as workspace changes and is not committed to `HEAD`.

## Target Outcome
- Review refuses to proceed when committed `HEAD` is not the sole source of truth for repository state.
- Operator guidance clearly says how to restore fidelity before review.
- Review/classify/gate semantics remain pinned to `origin/main...HEAD`.
- False reject/approve decisions caused by workspace-only divergence are eliminated by fail-closed review entry behavior.

## Atomic Task Isolation Contract
- **Single purpose:** enforce committed-HEAD fidelity at the review boundary.
- **Intent statement:** add a fail-closed review precondition that blocks review when workspace-only changes would make review differ from committed `HEAD`.
- **Out of scope:** escalation redesign, gate logic redesign, runner redesign, auto-commit, bundle-pack sync, broad UX improvements.
- **Allowed file boundary:** only the files listed in `02_file_scope.md`.
- **Forbidden file boundary:** any file not listed as allowed, especially runtime engine internals and unrelated automation stories.
- **Hard-stop condition:** stop immediately if the fix requires changing runner semantics, adding auto-commit behavior, or touching multiple independent findings beyond review-boundary fidelity.
- **Follow-up rule:** newly discovered out-of-scope issues must be captured in `05_followups.md` instead of being folded into this change.
- **Atomic follow-up rule:** each future follow-up prompt must isolate exactly one review finding or one narrowly defined blocker.

## Allowed Files
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
- `tests/test_review_gate_story_run.py`

## Forbidden Files
- `automation/run_codex_task.sh`
- `automation/scripts/finalize_story.sh`
- `automation/scripts/escalate_story.sh`
- `automation/scripts/commit_story_artifacts.sh`
- `docs/40_ai/**`
- `backend/**`
- `frontend/**`
- `database/**`
- `scripts/migrations/**`

## Risks
- Over-scoping into runner or gate redesign instead of a review-boundary guard.
- Blocking legitimate operator workflows if the dirty-state check is too broad or poorly messaged.
- Reintroducing duplicated clean-tree logic inconsistent with existing preflight contracts.

## Manual Actions
- Materialize the bundle.
- Validate the bundle.
- Review the active prompt for atomic scope before execution.
- After implementation, run the focused review-story test targets and inspect operator messaging in the failure path.

## Acceptance Notes
- Review fails closed when workspace-only changes would undermine committed-HEAD fidelity.
- Operator guidance is deterministic and actionable.
- Tests cover the new blocked path and the clean path.
- Documentation explicitly states that review/classify/gate operate on committed repository state only.

