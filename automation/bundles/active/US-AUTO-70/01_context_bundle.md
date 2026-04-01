## Source of Truth
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- `automation/scripts/run_story.sh`
- `tests/test_run_story.py`

## Current Code Reality
The registry now records that US-AUTO-69 was split because companion-artifact execution filtering and rerun-preflight stable-review recomputation are not one atomic change.

US-AUTO-69 already landed the execution-filtering half. The remaining work is explicitly tracked as US-AUTO-70 and is limited to `run_story.sh` plus its tests.

The defect is not stale evidence in the abstract. The defect is that rerun-preflight can still reason over the wrong effective surface after companion filtering has already narrowed what should count for the story.

## Architectural Intent
Preserve the existing fail-closed pipeline and committed-HEAD invariants while making rerun-preflight compute against the correct effective surface for the current story.

The desired architecture is narrow:
- execution filtering remains where it already lives
- rerun-preflight recomputation happens where rerun-preflight decisions are made
- review/gate/analyze contracts remain unchanged
- no new general-purpose reuse subsystem is introduced

This is a correction to decision input fidelity, not a redesign of the pipeline.

## Risks
- Scope drift into execution filtering or later review-stage scripts
- Regressions in normal rerun-preflight behavior for stories that are not companion-filtered
- Fail-open fallback if recomputation errors are swallowed
- Implicit contract drift if tests verify a broader behavior than the story intends

## Acceptance Notes
Review should reject if:
- any file outside the allowed pair changes
- the implementation depends on editing `run_codex_task.sh`
- the recomputation path is inferred loosely rather than deterministically
- errors fall back to the old widened surface
- tests do not prove the companion-filtered rerun-preflight case

