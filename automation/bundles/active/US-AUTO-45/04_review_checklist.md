# US-AUTO-45: Review Checklist

## Scope Validation
- [ ] Changes stay inside `02_file_scope.md`
- [ ] No forbidden files changed
- [ ] No unrelated refactor or formatting-only edits
- [ ] No producer-script or materialization scope creep was introduced

## Functional Validation
- [ ] `review_gate_story_run.sh` consumes pinned artifacts only
- [ ] Gate does not invoke AI review or classification stages
- [ ] Missing pinned artifacts cause fail-closed behavior
- [ ] Invalid pinned classification causes fail-closed behavior
- [ ] The same pinned evidence produces the same gate outcome

## Architecture Validation
- [ ] Review gate acts as an evidence consumer, not an upstream recomputation stage
- [ ] Pinned-run semantics remain explicit
- [ ] Stale-run and head-consistency protections remain intact
- [ ] Docs and operator guidance stay aligned with the stricter contract

## Verification
- [ ] Focused tests updated
- [ ] Validation commands are recorded
- [ ] Manual verification steps are recorded when needed
- [ ] Risks and follow-ups are captured before merge

## Review Prompt Seed
- Verify that gate behavior is deterministic for a pinned run with valid existing review artifacts.
- Verify that missing or invalid artifacts produce deterministic fail-closed behavior.
- Verify that no implicit recomputation path remains.

