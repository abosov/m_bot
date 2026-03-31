# Context Bundle

## Source of Truth
- docs/90_codex/epics/US-AUTO_REGISTRY.md
- automation/scripts/ai_review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh
- existing committed manual-finish continuation logic from US-AUTO-52
- existing committed diff fidelity behavior from US-AUTO-53 and US-AUTO-54
- focused regression suites covering review boundary and pipeline validation contracts

## Current Code Reality
The pipeline currently has two simultaneously true facts:
1. manual-finish continuation is explicitly allowed after `blocked_non_converging_rerun`
2. downstream review stages still expect pinned artifacts to align directly with the final reviewed `HEAD`

That mismatch causes the allowed continuation path to behave like a compliance violation once the branch tip advances through manual finish.

The defect is not in:
- diff.patch fidelity
- basic committed-head enforcement
- rerun boundary detection

The defect is in downstream interpretation of allowed continuation lineage versus final reviewed `HEAD`.

## Architectural Intent
The workflow must remain fail-closed.

The intended architecture is:
- normal review operates on a fresh committed-head rerun
- manual-finish continuation is a tightly constrained exception
- exceptions must still be evidence-based and deterministic
- downstream stages must never guess that a newer `HEAD` is compliant; they must prove the exact allowed lineage or reject

The correct repair is therefore:
- add or interpret deterministic continuation evidence for final-HEAD compliance in the exact allowed manual-finish path
- preserve strict rejection for all other stale or ambiguous variants

## Risks
- Broadening the exception beyond the exact allowed path
- Accepting descendant `HEAD` without proving it belongs to the approved continuation
- Divergent logic between AI review, classification, gate, and analyze
- Confusing evidence model that forces future stories to patch around hidden semantics
- Turning an allowed exception into an implicit general rule

## Acceptance Notes
A good implementation:
- keeps the exception narrow
- uses deterministic committed evidence, not heuristics
- preserves ordinary review invariants
- gives analyze/gate enough information to explain why the exact path is allowed or rejected
- does not reopen the rerun loop

