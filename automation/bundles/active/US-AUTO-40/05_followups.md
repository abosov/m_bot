# Follow-ups — US-AUTO-40

## Expected follow-up stories outside this scope

### US-AUTO-41
Single source of truth for scope contract.

This story may expose remaining ambiguity around which bundle file is authoritative for declared reviewed scope.
US-AUTO-40 should enforce fidelity, but not fully redesign multi-file scope authority.

### US-AUTO-37
Ephemeral automation paths contract.

Runtime-managed files such as `automation/story_change_ledger.jsonl` still need to be classified and handled as workflow artifacts rather than normal implementation diff in the wrong contexts.

### US-AUTO-38
Automatic rollback after failed automation run.

A faid run should not leave the operator with manual cleanup burden.
This remains a separate operational hygiene story.

### US-AUTO-35
Head-bound run resolution and run-local scope enforcement.

Once fidelity is enforced, a further improvement is to ensure review/gate always bind to the most relevant run for the current HEAD and evaluate scope using run-local delta only.

### US-AUTO-36
Preflight hygiene enforcement.

Earlier operator-visible hygiene failures before Codex execution still remain valuable and should be enforced separately.

## Implementation notes for future work

Depending on the final implementation of US-AUTO-40, future work may need to:

- centralize reviewed file-set declaration;
- formalize artifact freshness markers;
- distinguish declarative review scope from operational runtime artifacts more cleanly;
- improve remediation UX when fidelity checks fail.
