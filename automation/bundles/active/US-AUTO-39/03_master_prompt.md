# US-AUTO-39 PROMPT 1 — Re-review / Re-gate Finalized Post-Commit HEAD

## Role

You are the Zumbot workflow automation engineer working under the repository's CODEX Operating System.

## Goal

Implement a fail-closed post-finalize re-review / re-gate contract so that merge readiness is valid only when review/gate evidence is explicitly bound to the current finalized HEAD.

## Source of Truth

- `automation/scripts/finalize_story.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/run_codex_task.sh`
- `tests/test_finalize_story_script.py`
- `docs/90_codex/**`
- `automation/bundles/active/US-AUTO-39/**`

## Files Allowed To Change

- `automation/scripts/finalize_story.sh`
- `automation/scripts/ai_review_story_run.sh`
- `automation/scripts/classify_review_story_run.sh`
- `automation/scripts/analyze_story_run.sh`
- `automation/scripts/review_gate_story_run.sh`
- `automation/scripts/run_story.sh`
- `automation/scripts/run_codex_task.sh`
- `tests/test_finalize_story_script.py`
- targeted review/gate orchestration tests directly required for HEAD-bound approval
- `docs/90_codex/**`
- `automation/bundles/active/US-AUTO-39/**`

## Files Not Allowed To Change

- `backend/**`
- `frontend/**`
- `database/**`
- `migrations/**`
- unrelated deployment scripts
- unrelated workflow redesign outside this story

## Context

US-AUTO-32 proved that a pre-merge finalized commit can be created safely, but it exposed a workflow integrity bug: when finalize creates a new commit, existing review/gate evidence still belongs to the prior HEAD, so merge readiness may reflect stale approval.

The required invariant is:

- reviewed HEAD == finalized HEAD == merged HEAD

## Requirements

1. Preserve the ability of finalize to create a durable pre-merge finalized commit.
2. Make the finalized HEAD the canonical merge target.
3. Ensure pre-finalize approval becomes stale if finalize changes HEAD.
4. Require review/gate evidence to be explicitly associated with a HEAD identity.
5. Fail closed if current HEAD differs from reviewed/gated HEAD.
6. Add or update tests proving stale approval rejection and post-finalize re-approval behavior.
7. Update workflow documentation and active bundle files accordingly.

## Constraints

- Keep the implementation as small and targeted as possible.
- Do not absorb US-AUTO-40 / 41 / 35 / 36 / 37 / 38 except for minimal shared plumbing strictly required for this story.
- Do not reintroduce any fail-open behavior.
- Prefer explicit metadata and deterministic checks over latest-run heuristics.
- Preserve durable ledger behavior.

## Output

Return:
1. changed files summary
2. design rationale
3. validation performed
4. risks / follow-ups
5. final diff

