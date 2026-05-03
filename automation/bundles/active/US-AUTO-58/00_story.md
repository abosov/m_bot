## Story ID and Title

US-AUTO-58 — Stage-loop cap and forced escalation threshold

## Objective

Add runtime enforcement that detects repeated stage loops across the US-AUTO automation pipeline and forces an explicit operator decision instead of allowing blind rerun/refresh/review loops to continue indefinitely.

The story must address the broader loop pattern observed after US-AUTO-60 and US-AUTO-78:

    run_story
    -> Codex or docs polish
    -> dirty tree or stale/fidelity blocker
    -> amend or small fix
    -> no-Codex refresh
    -> AI review / classification / gate
    -> classification reject or another small fix
    -> refresh again

The goal is not to prohibit legitimate fixes. The goal is to stop non-converging stage loops and route the operator to a bounded decision:

    - accept safe path;
    - run a narrow safety/source-of-truth fix;
    - escalate;
    - create follow-up;
    - abort;
    - intentionally override only when explicitly allowed by existing safety contracts.

## Source of Truth

Primary registry:

    docs/90_codex/epics/US-AUTO_REGISTRY.md

Primary operator workflow document:

    docs/90_codex/US_AUTO_OPERATOR_GUIDE.md

Primary runtime scripts:

    automation/scripts/run_story.sh
    automation/scripts/analyze_story_run.sh
    automation/scripts/refresh_review_evidence.sh
    automation/scripts/ai_review_story_run.sh
    automation/scripts/review_story_run.sh
    automation/scripts/classify_review_story_run.sh
    automation/scripts/review_gate_story_run.sh

Primary test surface:

    tests/test_run_story.py
    tests/test_analyze_story_run.py
    tests/test_refresh_review_evidence.py
    tests/test_ai_review_story_run.py
    tests/test_review_story_run.py
    tests/test_classify_review_story_run.py
    tests/test_review_classification_script.py
    tests/test_review_gate_story_run.py
    tests/test_review_pipeline_validation_contract.py

## Current Code Reality

The repository already has separate scripts for run, analyze, refresh evidence, AI review, review, classification, and gate.

US-AUTO-60 added the accepted-implementation freeze / no-Codex review-evidence refresh path.

US-AUTO-78 updated the roadmap and Operator Guide but also reproduced a broader loop pattern:

    run_story
    -> small docs/story-artifact polish
    -> blocked_review_artifact_fidelity
    -> amend
    -> no-Codex refresh
    -> classification reject
    -> amend
    -> no-Codex refresh

The current runtime can still recommend another run or refresh when the process is no longer converging.

## Target Outcome

The pipeline detects repeated stage loops and stops blind continuation.

When a loop cap is reached, output must force an explicit operator decision instead of recommending another blind run_story or refresh.

The result must preserve:

    - dirty-tree blockers;
    - stale evidence blockers;
    - committed-HEAD safety;
    - US-AUTO-60 no-Codex refresh path;
    - classification and review gate authority;
    - narrow fix path only for explicit safety/source-of-truth blockers.

## Scope

Implement a stage-loop cap and forced escalation threshold for the US-AUTO automation pipeline.

The cap must cover repeated cycles across these stages:

    - run_story / rerun;
    - refresh_review_evidence;
    - analyze;
    - AI review;
    - classification;
    - review gate;
    - small fix / amend;
    - refresh again.

The implementation must preserve the US-AUTO-60 no-Codex refresh path. It must not regress pinned-run, committed-HEAD, dirty-tree, refresh evidence, classification, or review-gate safety invariants.

This is a runtime/enforcement story, not a docs-only story.

## Non-goals

Do not implement the full deterministic story orchestrator. That belongs to US-AUTO-79.

Do not implement the full compact operator/AI decision packet UX. That belongs to US-AUTO-80, unless a minimal decision message is required for this story.

Do not weaken existing analyze authority.

Do not make review/classify/gate runnable with dirty tree.

Do not allow stale run evidence after implementation commits except through the explicitly allowed US-AUTO-60 no-Codex refresh path.

Do not solve non-essential polish by automatically applying more implementation changes.

Do not modify tests merely to relax existing safety contracts.

## Dependencies

US-AUTO-60 is complete and provides the accepted-implementation freeze / no-Codex review-evidence refresh path.

US-AUTO-78 is complete and updated the roadmap and Operator Guide to define the active line:

    US-AUTO-58 -> US-AUTO-31 -> US-AUTO-79 -> US-AUTO-80 -> US-AUTO-74

US-AUTO-31 is planned after this story and will make analyze the mandatory decision authority before rerun, refresh, review continuation, classification, gate, or phase advance.

US-AUTO-79 and US-AUTO-80 are planned after US-AUTO-58 and US-AUTO-31. US-AUTO-58 must not build a partial orchestrator that accelerates loops.

## Acceptance Criteria

A repeated stage-loop is detected before the pipeline recommends or permits another blind continuation.

The loop detection covers at least:

    - repeated run/rerun attempts for the same story without convergence;
    - repeated refresh/review/classification/gate cycles after accepted implementation;
    - repeated small fix/amend/refresh patterns;
    - classification or gate rejects that are not explicit safety/source-of-truth blockers.

When the loop threshold is reached, the tool output must force an operator decision rather than suggesting another blind run_story or blind refresh.

The forced decision output must clearly distinguish:

    - explicit safety or source-of-truth blocker: narrow fix allowed;
    - non-safety polish or preference: follow-up/escalation preferred;
    - repeated evidence/fidelity churn: stop and escalate or use accepted freeze/refresh policy;
    - dirty tree: commit/discard/restore before continuing;
    - stale evidence: use the proper refresh path only when allowed.

Existing review safety contracts must remain valid.

Targeted tests must be added or updated for the new loop-cap behavior.

Relevant documentation must be updated to describe the loop cap and escalation threshold.

## Completion Notes

Implementation PR should deliver runtime enforcement and tests.

Registry closeout must happen separately after the implementation PR is merged.

Story is not closed until:

    - implementation PR merged;
    - registry closeout PR merged or registry explicitly checked and update not required;
    - local main updated;
    - working tree clean;
    - related branches cleaned up.

