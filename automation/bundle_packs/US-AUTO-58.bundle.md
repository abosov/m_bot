Story-ID: US-AUTO-58
Title: Stage-loop cap and forced escalation threshold
Type: enforcement
Status: Draft
Priority: P1
Depends-On: US-AUTO-60, US-AUTO-78
Created-From: post-US-AUTO-78 transfer context

=== FILE: 00_story.md ===
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

=== FILE: 01_context_bundle.md ===
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

=== FILE: 02_file_scope.md ===
## Files Allowed To Change

Runtime scripts:

    - automation/scripts/analyze_story_run.sh
    - automation/scripts/run_story.sh
    - automation/scripts/refresh_review_evidence.sh
    - automation/scripts/story_stage_loop.sh
    - automation/scripts/ai_review_story_run.sh
    - automation/scripts/review_story_run.sh
    - automation/scripts/classify_review_story_run.sh
    - automation/scripts/review_gate_story_run.sh

Test files:

    - tests/test_analyze_story_run.py
    - tests/test_run_story.py
    - tests/test_refresh_review_evidence.py
    - tests/test_ai_review_story_run.py
    - tests/test_review_story_run.py
    - tests/test_classify_review_story_run.py
    - tests/test_review_classification_script.py
    - tests/test_review_gate_story_run.py
    - tests/test_review_pipeline_validation_contract.py

Documentation:

    - docs/90_codex/US_AUTO_OPERATOR_GUIDE.md
    - docs/90_codex/epics/US-AUTO_REGISTRY.md

Story artifacts:

    - automation/bundle_packs/US-AUTO-58.bundle.md
    - automation/bundles/active/US-AUTO-58/00_story.md
    - automation/bundles/active/US-AUTO-58/01_context_bundle.md
    - automation/bundles/active/US-AUTO-58/02_file_scope.md
    - automation/bundles/active/US-AUTO-58/03_master_prompt.md
    - automation/bundles/active/US-AUTO-58/04_review_checklist.md
    - automation/bundles/active/US-AUTO-58/05_followups.md
    - automation/bundles/active/US-AUTO-58/06_manual_actions.md

Optional new helper files, only if justified by existing project structure:

    - automation/scripts/story_stage_loop.sh
    - automation/scripts/lib/*
    - tests/test_*loop*.py
## Files Not Allowed To Change

Do not modify unrelated business feature code.

Do not modify application runtime unrelated to the US-AUTO automation pipeline.

Do not modify production bot behavior.

Do not modify secrets, environment files, generated caches, or local-only artifacts.

Do not commit:

    tests/__pycache__/*
    .pytest_cache/*
    automation/runs/*
    automation/story_change_ledger.jsonl unless intentionally required and reviewed

## Scope Boundaries

This story may add loop-cap logic and tests.

This story may update operator documentation.

This story may clarify the US-AUTO-58 registry row while keeping the story Planned during implementation.

This story must not close US-AUTO-58 in the registry until the implementation PR has been merged and a separate registry closeout step is performed.

This story must not implement:

    - full deterministic orchestration;
    - automatic end-to-end stage advancement;
    - full decision packet UX;
    - broad refactors of all scripts;
    - changes to external review contracts unless explicitly required and tested.

## Review Notes

Review must verify that the implementation does not reintroduce the accepted-implementation rerun loop.

Review must verify that the no-Codex refresh path remains valid.

Review must verify that the loop cap stops repeated non-converging stage churn without blocking first-pass normal correction.

Review must verify that dirty tree and stale evidence safety checks remain stricter than convenience.

=== FILE: 03_master_prompt.md ===
## Role

You are implementing a safety/enforcement story for the Zumbot US-AUTO automation pipeline.

Act as a senior automation pipeline engineer with strict respect for the existing workflow invariants, validator contracts, review-stage safety gates, and story lifecycle rules.

Do not weaken external contracts to make tests pass.

## Goal

Implement US-AUTO-58: stage-loop cap and forced escalation threshold for the US-AUTO automation pipeline.

You are working in repository abosov/m_bot on a non-main feature branch.

The goal is to detect repeated stage loops and force an explicit operator decision instead of allowing indefinite blind run_story, refresh, review, classification, gate, amend, and refresh cycles.

## Source of Truth

Use these files as source of truth:

    docs/90_codex/epics/US-AUTO_REGISTRY.md
    docs/90_codex/US_AUTO_OPERATOR_GUIDE.md
    automation/scripts/analyze_story_run.sh
    automation/scripts/run_story.sh
    automation/scripts/refresh_review_evidence.sh
    automation/scripts/story_stage_loop.sh
    automation/scripts/ai_review_story_run.sh
    automation/scripts/review_story_run.sh
    automation/scripts/classify_review_story_run.sh
    automation/scripts/review_gate_story_run.sh
    tests/test_analyze_story_run.py
    tests/test_run_story.py
    tests/test_refresh_review_evidence.py
    tests/test_ai_review_story_run.py
    tests/test_review_story_run.py
    tests/test_classify_review_story_run.py
    tests/test_review_classification_script.py
    tests/test_review_gate_story_run.py
    tests/test_review_pipeline_validation_contract.py

Preserve existing workflow invariants:

    - never run automation on main;
    - after any new commit, old AUTOMATION_RUN_DIR is invalid unless the explicit no-Codex refresh path applies;
    - review/classify/gate require committed HEAD evidence;
    - dirty tree blocks review-stage continuation;
    - do not run run_story.sh after accepted implementation merely to refresh review evidence;
    - use no-Codex refresh evidence when accepted implementation needs current review evidence;
    - classification and gate rejects must not be ignored;
    - non-safety polish should become escalation/follow-up rather than infinite amendments.

## Files Allowed To Change

You may change:

    automation/scripts/analyze_story_run.sh
    automation/scripts/run_story.sh
    automation/scripts/refresh_review_evidence.sh
    automation/scripts/story_stage_loop.sh
    automation/scripts/ai_review_story_run.sh
    automation/scripts/review_story_run.sh
    automation/scripts/classify_review_story_run.sh
    automation/scripts/review_gate_story_run.sh
    tests/test_analyze_story_run.py
    tests/test_run_story.py
    tests/test_refresh_review_evidence.py
    tests/test_ai_review_story_run.py
    tests/test_review_story_run.py
    tests/test_classify_review_story_run.py
    tests/test_review_classification_script.py
    tests/test_review_gate_story_run.py
    tests/test_review_pipeline_validation_contract.py
    docs/90_codex/US_AUTO_OPERATOR_GUIDE.md
    docs/90_codex/epics/US-AUTO_REGISTRY.md
    automation/bundle_packs/US-AUTO-58.bundle.md
    automation/bundles/active/US-AUTO-58/*

You may add a small helper module or helper script only if it keeps loop detection testable and follows existing project conventions.

The preferred explicit helper path for shared stage-loop logic is:

    automation/scripts/story_stage_loop.sh

## Files Not Allowed To Change

Do not change unrelated application or business feature files.

Do not change tests to weaken external behavior contracts.

Do not commit generated cache files.

Do not commit automation/runs artifacts.

Do not commit local environment files or secrets.

Do not broaden the story into US-AUTO-79 or US-AUTO-80.

## Requirements

Add loop-cap enforcement for repeated pipeline stage churn.

The implementation should detect repeated non-converging loops across at least:

    - run_story / rerun;
    - refresh_review_evidence;
    - analyze;
    - AI review;
    - classification;
    - review gate;
    - small fix / amend;
    - refresh again.

When the cap is reached, output a stable escalation marker and do not recommend another blind run_story or blind refresh.

The forced decision output must identify allowed next actions, such as:

    - narrow fix only for explicit safety/source-of-truth blocker;
    - follow-up for non-safety polish or broad refactor;
    - escalation for repeated evidence/fidelity churn;
    - abort or operator override only where existing policy allows;
    - use no-Codex refresh only when accepted implementation needs evidence refresh and the working tree is clean.

Keep analyze as the decision authority where possible.

Add tests for:

    - normal first-pass path not capped;
    - repeated run/rerun loop capped;
    - repeated refresh/review/classify loop capped;
    - safety/source-of-truth blocker allows narrow fix path;
    - non-safety polish routes to escalation/follow-up;
    - dirty tree and stale evidence blockers remain intact.

Update documentation in US_AUTO_OPERATOR_GUIDE.md to describe the stage-loop cap policy.

Optionally clarify the US-AUTO-58 registry row, but do not mark it Implemented during the implementation PR unless the repository’s established workflow explicitly expects that. Registry closeout is separate after merge.

## Output

Implement the code, tests, and documentation updates.

Run targeted tests covering modified scripts.

Report:

    - files changed;
    - loop-cap behavior added;
    - tests run and results;
    - any follow-ups for US-AUTO-31, US-AUTO-79, or US-AUTO-80.

Do not claim full pytest unless full pytest was actually run.

Do not produce generated run artifacts as committed files.

=== FILE: 04_review_checklist.md ===
## Scope Validation

Confirm the implementation stays within US-AUTO-58.

Confirm it does not implement the full US-AUTO-79 orchestrator.

Confirm it does not implement the full US-AUTO-80 decision packet UX beyond minimal required forced-decision output.

Confirm it does not weaken dirty-tree, stale-run, committed-HEAD, refresh evidence, classification, or gate safety contracts.

Confirm it does not modify unrelated business feature code.

Confirm registry status is not prematurely changed to Implemented unless this is explicitly part of the accepted repository workflow.

## Functional Validation

Verify loop cap behavior for repeated stage loops.

Verify that repeated run/rerun loops are stopped.

Verify that repeated refresh/review/classification/gate loops are stopped.

Verify that non-safety polish loops route to escalation or follow-up instead of more blind implementation changes.

Verify that explicit safety/source-of-truth blockers can still permit a narrow fix.

Verify the US-AUTO-60 no-Codex refresh path remains valid.

Verify analyze remains the safest decision authority.

Verify outputs contain stable markers that future automation can parse or rely on.

## Verification

Run targeted tests relevant to changed scripts.

Expected targeted tests may include:

    python3 -m pytest tests/test_analyze_story_run.py tests/test_run_story.py tests/test_refresh_review_evidence.py tests/test_review_story_run.py tests/test_classify_review_story_run.py tests/test_review_gate_story_run.py tests/test_review_pipeline_validation_contract.py

If AI review script behavior changes, also run:

    python3 -m pytest tests/test_ai_review_story_run.py tests/test_review_classification_script.py

If full pytest is run, report the full result exactly.

Review git status before review-stage commands.

Do not proceed to review/classify/gate with dirty tree.

## Regression Checks

Check that old accepted workflows still pass.

Check that a first rerun or first refresh is not blocked merely because a prior stage exists.

Check that after commit/amend, old AUTOMATION_RUN_DIR is still considered stale unless explicitly refreshed through the allowed no-Codex path.

Check that ledger-only dirtiness guidance remains intact.

Check that analyze output does not recommend a forbidden next step.

=== FILE: 05_followups.md ===
## Follow-Up Prompt Queue

US-AUTO-31:

    Make analyze the mandatory decision authority before rerun, refresh, review continuation, classification, gate, escalation, follow-up, or phase advance.

US-AUTO-79:

    Add story pipeline orchestrator for deterministic stage chaining after US-AUTO-58 and US-AUTO-31 are resolved.

US-AUTO-80:

    Add compact operator/AI decision packet UX for non-deterministic stops, or fold into US-AUTO-79 only if still atomic.

Potential follow-up:

    Add machine-readable loop-state output if US-AUTO-58 only introduces textual markers and US-AUTO-79 needs structured fields.

Potential follow-up:

    Add better review artifact refresh command templates for docs/governance stories, including bundle validation, live HEAD proof, branch proof, and story-scoped pytest/full pytest where required.

## Iteration Notes

US-AUTO-78 showed that loops are broader than Codex rerun loops.

The loop can occur through refresh/review/classify/fix/refresh even when run_story is no longer used.

US-AUTO-58 must therefore treat stage-loop cap as a pipeline-level behavior, not only a run_story behavior.

Classification rejects should be interpreted carefully:

    - explicit safety/source-of-truth blocker: allow narrow fix;
    - non-safety polish/preference: prefer follow-up/escalation;
    - evidence/fidelity churn: force decision rather than repeat the loop.

Future orchestration must not accelerate loops. It must stop earlier with decision packets.

=== FILE: 06_manual_actions.md ===
## Required Human Actions

Before starting implementation:

    - confirm current branch is not main;
    - confirm working tree is clean;
    - validate and materialize this bundle.

Before review-stage commands:

    - run analyze on the pinned run;
    - confirm working tree is clean;
    - confirm run evidence corresponds to current committed HEAD or use the allowed no-Codex refresh path.

Before push or PR:

    - restore automation/story_change_ledger.jsonl if it is the only unintended dirty file;
    - confirm git status is clean except intended committed changes;
    - push feature branch;
    - create implementation PR.

After implementation PR merge:

    - update local main;
    - perform registry closeout check;
    - create registry closeout PR if required;
    - merge registry closeout PR;
    - delete local and remote story branches;
    - confirm working tree clean.

## Completion Status

Draft bundle prepared.

Implementation not started.

Review not started.

Registry closeout not started.

Story remains open until implementation PR and registry closeout are complete.
