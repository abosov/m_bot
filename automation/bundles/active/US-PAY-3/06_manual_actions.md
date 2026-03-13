# US-PAY-3 Manual Actions

## Purpose
Track manual checks or operational actions that may be required during or after implementation.

## Expected Manual Checks
- verify authenticated specialist route behavior locally
- manually inspect returned `confirmation_url` shape in dev/test flow
- confirm no UI path or return route marks payment as successful
- confirm duplicate click/retry behavior is stable from API perspective
- confirm router registration if new route path is introduced

## Environment / Operational Notes
- no production deploy actions are part of this file yet
- no secret rotation is expected in this story
- webhook end-to-end manual verification belongs mainly to `US-PAY-4`

## Current Manual Actions
- None yet.
