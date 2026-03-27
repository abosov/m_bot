# US-AUTO-43: Review Checklist

## Scope Validation
- only allowed files changed
- no scope expansion
- no forbidden files touched

## Functional Validation
- invalid AI review blocks classification
- missing artifact triggers failure
- malformed output triggers failure
- incomplete output triggers failure
- unreadable/non-UTF8 output triggers failure
- logical invalidity triggers failure

## Verification
- tests cover all failure scenarios
- pipeline stops on invalid input
- behavior deterministic
