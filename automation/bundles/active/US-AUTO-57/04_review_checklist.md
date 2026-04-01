## Scope Validation
- APPROVE only if changed files are limited to:
  - `automation/scripts/run_story.sh`
  - `automation/scripts/_helpers.sh`
  - `tests/test_run_story.py`
- REJECT if any review-stage script, analyze script, registry file, bundle artifact, ledger file, or unrelated test file is changed.
- REJECT if the implementation adds telemetry, analyze enforcement, stage-loop escalation, artifact reuse, or lightweight review refresh behavior.
- REJECT if the implementation expands beyond preflight rerun-skip detection.
- REJECT immediately if any docs, registry, roadmap, planning, or status-tracking file appears in changed files for this story.

## Functional Validation
- APPROVE only if `run_story.sh` can block a rerun before Codex execution when sameness is conservatively proven.
- APPROVE only if the skip path is fail-closed and deterministic.
- APPROVE only if ordinary rerun behavior remains intact when proof is absent or uncertain.
- REJECT if the implementation skips reruns on guesswork, stale evidence, malformed evidence, or ambiguous comparisons.
- REJECT if the implementation changes manual-finish continuation semantics, review-stage semantics, or committed-HEAD boundary semantics.

## Verification
- Run focused verification for the touched scope, including the relevant `tests/test_run_story.py` coverage.
- Confirm that the skip path does not invoke Codex.
- Confirm that deterministic operator guidance is emitted on the skip path.
- Confirm that uncertainty falls through to normal run behavior.
- Confirm that no forbidden files were changed.

### HARD BLOCK
- REJECT if any forbidden file changed.
- REJECT if any fail-open skip path exists.
- REJECT if the implementation relies on non-committed or workspace-only state as proof of sameness.
- REJECT if the change weakens or bypasses existing pipeline invariants.
- Binary decision only:
  - APPROVE
  - REJECT

