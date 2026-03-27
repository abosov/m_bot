# Review Checklist

## Scope Validation
- only allowed files modified
- only escalation validation logic changed

## Functional Validation
- strict JSON parsing used
- schema validation implemented
- origin validation present
- fail-closed enforced

## Verification

### HARD BLOCK
- regex/sed JSON parsing exists → REJECT
- missing schema validation → REJECT
- missing origin validation → REJECT
- fallback logic present → REJECT
- non-deterministic error handling → REJECT

### RESULT
- APPROVE only if all checks pass

---

