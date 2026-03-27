# Context Bundle — US-AUTO-48

## Source of Truth
Primary sources of truth for this story:
- `docs/90_codex/epics/US-AUTO_REGISTRY.md`
- current implementations of:
  - `automation/scripts/ai_review_story_run.sh`
  - `automation/scripts/classify_review_story_run.sh`
  - `automation/scripts/review_gate_story_run.sh`
  - `automation/scripts/analyze_story_run.sh`
- current focused tests for AI review, classification, gate, and analysis
- the observed review-pipeline failure recorded as follow-up `US-AUTO-48` in the registry

## Current Code Reality
The current review pipeline can reach a state where:
- `ai_review_raw_output.txt` exists
- `ai_review_result.md` is missing or malformed
- classification cannot proceed deterministically from a validated normalized artifact
- gate rejects with `ai_review_missing_artifact`

This means the boundary between raw model output and the normalized review artifact is not enforced strongly enough for downstream consumers.

## Architectural Intent
The review pipeline must treat the normalized AI review artifact as an explicit contract boundary:
- raw output is diagnostic only
- downstream stages must consume validated normalized artifacts, not assumptions
- if normalization cannot produce a valid `ai_review_result.md`, the system must fail closed with deterministic evidence
- classification, gate, and analysis must present a clear contract failure state instead of an ambiguous partially-reviewed state

## Acceptance Notes
Accept the story only if all of the following are true:
- `ai_review_result.md` is explicitly required and validated before classification proceeds
- malformed or missing normalized AI review artifacts fail closed deterministically
- raw AI review output remains preserved for diagnosis
- downstream stages no longer rely on implicit artifact presence
- focused regression tests cover valid, missing, and malformed artifact paths
- no unrelated rerun convergence or broad pipeline redesign changes are introduced

## Risks
Main risks for this story:
- accidentally widening into general review-pipeline redesign
- changing downstream behavior without focused regression coverage
- introducing hidden fallback behavior that still relies on implicit artifact presence
- coupling this fix to rerun convergence work that belongs to `US-AUTO-47`

