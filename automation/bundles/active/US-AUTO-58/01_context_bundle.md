## Source of Truth

Primary registry:

    docs/90_codex/epics/US-AUTO_REGISTRY.md

Primary operator workflow document:

    docs/90_codex/US_AUTO_OPERATOR_GUIDE.md

Relevant scripts:

    automation/scripts/run_story.sh
    automation/scripts/analyze_story_run.sh
    automation/scripts/refresh_review_evidence.sh
    automation/scripts/ai_review_story_run.sh
    automation/scripts/review_story_run.sh
    automation/scripts/classify_review_story_run.sh
    automation/scripts/review_gate_story_run.sh

Relevant tests:

    tests/test_run_story.py
    tests/test_analyze_story_run.py
    tests/test_refresh_review_evidence.py
    tests/test_ai_review_story_run.py
    tests/test_review_story_run.py
    tests/test_classify_review_story_run.py
    tests/test_review_classification_script.py
    tests/test_review_gate_story_run.py
    tests/test_review_pipeline_validation_contract.py

Known current registry rows:

    US-AUTO-58:
    Stage-loop cap and forced escalation threshold.
    Detect repeated stage/rerun/polish loops and force an explicit operator decision instead of allowing indefinite run_story cycles.

    US-AUTO-31:
    Mandatory analyze gate before rerun, refresh, review continuation, classification, gate, or phase advance.

    US-AUTO-79:
    Story pipeline orchestrator for deterministic stage chaining.

    US-AUTO-80:
    Compact operator/AI decision packet UX for non-deterministic stops.

Known current Next Recommended Story:

    1. US-AUTO-58 — stage-loop cap and forced escalation threshold

## Current Code Reality

The pipeline already contains separate scripts for run, analyze, refresh evidence, review, classification, and gate.

Existing workflow invariants include:

    - never work a story on main;
    - after any amend/commit, old AUTOMATION_RUN_DIR is stale unless the explicit no-Codex refresh path applies;
    - review/classify/gate require evidence corresponding to current committed HEAD;
    - review/classify/gate must not run with dirty tree;
    - do not run run_story.sh after accepted implementation merely to refresh review evidence;
    - ledger-only dirtiness in automation/story_change_ledger.jsonl should be restored before push/merge review;
    - PR merged does not equal story closed.

US-AUTO-60 added the no-Codex refresh path for accepted implementation.

US-AUTO-78 documented the full story pipeline and the distinction between deterministic safe steps and decision-dependent stops.

However, the current runtime workflow can still fall into repeated loops:

    run_story
    -> small docs/code polish
    -> fidelity blocker
    -> amend
    -> refresh
    -> classification reject
    -> amend
    -> refresh
    -> review/gate again

The current tools may still recommend another run or refresh when the process is no longer converging.

## Architectural Intent

US-AUTO-58 should add a bounded loop-cap layer to the existing pipeline without replacing analyze authority.

The preferred implementation shape is:

    - detect repeated stage transitions or repeated same-story attempts from available run/review artifacts;
    - preserve existing safety checks;
    - when threshold is reached, print a forced escalation / operator decision message;
    - prevent blind next-command recommendations that continue the same non-converging loop.

The implementation may be located in analyze if analyze already computes the safest next action. It may also use a helper module or script if that keeps the logic testable.

The loop detector should be conservative. It should avoid false positives for normal first-pass retry/fix workflows but should catch repeated continuation attempts after the same story has already reached accepted implementation or repeated classification/gate churn.

The result should prepare the ground for US-AUTO-31 and US-AUTO-79 without implementing them prematurely.

## Risks

Risk: weakening safety by allowing continuation after stale evidence.

Mitigation: preserve existing stale evidence and dirty-tree blockers.

Risk: blocking legitimate safety fixes.

Mitigation: allow narrow fixes for explicit safety/source-of-truth blockers.

Risk: overfitting to US-AUTO-78.

Mitigation: define stage-loop categories generically across run, refresh, review, classification, gate, fix, and amend.

Risk: implementing too much of US-AUTO-79.

Mitigation: do not build automatic deterministic stage chaining. Only cap loops and force decisions.

Risk: classification rejects become ignored.

Mitigation: classification rejects must still block unless explicitly routed to narrow fix, escalation, or follow-up.

Risk: tests become too brittle around exact console wording.

Mitigation: test stable status markers and decision categories, not long prose unless existing test style requires exact strings.

## Acceptance Notes

The final output must include tests proving the loop cap.

The loop cap must produce a clear machine-readable or stable textual marker suitable for future US-AUTO-79/80 consumption.

Recommended stable marker examples:

    RUN STATUS: ESCALATION REQUIRED
    LOOP CAP: REACHED
    REQUIRED DECISION: operator_escalation

Exact naming may be adjusted to match existing script style.

The story should document the policy in US_AUTO_OPERATOR_GUIDE.md.

Registry row may be clarified during implementation, but final status should be changed to Implemented only in the registry closeout PR after merge.

