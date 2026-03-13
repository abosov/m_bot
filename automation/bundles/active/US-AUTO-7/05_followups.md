# US-AUTO-7 Follow-ups

## Possible follow-up stories

### 1. Explicit review base selection
If current remediation hardcodes a review base assumption, a future story may expose the base selection explicitly and validate it more strictly.

Potential future scope:
- configurable review base
- clearer operator messages about which base was used
- stricter mismatch detection

### 2. Stage logging for automation scripts
Operator UX is still weak in long-running automation steps.

Potential future scope:
- add `[INFO]`, `[OK]`, `[ERROR]` stage logs
- make Codex-running stages visible
- improve troubleshooting during long waits

### 3. Hardening against prompt injection in review/classification steps
AI-generated review artifacts should be treated as untrusted input everywhere they are embedded into downstream prompts.

Potential future scope:
- explicit untrusted-content guardrails
- stronger prompt hardening
- additional tests

## Not part of US-AUTO-7
- no product runtime logic changes
- no merge gate redesign
- no full pipeline redesign
- no deployment/system changes
