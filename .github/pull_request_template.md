## Title
Short description of the change.

## User Story
Reference to the User Story.

Examples:
- US-AD-8
- US-DOCS-3

## Goal
Explain the goal of this change.

## Context
Explain why the change is needed.

## Architecture Review
Confirm which layers are affected:

- [ ] API
- [ ] Services
- [ ] ORM
- [ ] Database migrations
- [ ] Infrastructure
- [ ] Documentation

## Database Impact
Confirm the following:

- [ ] No database schema change
- [ ] Schema change via SQL migration
- [ ] ORM models updated to reflect migration

**Rule:** SQL migrations are the source of truth for database schema.

## Testing
List tests added or executed.

Examples:
- `pytest`
- unit tests updated
- integration tests verified

## Security Review
Confirm:

- [ ] No secrets introduced
- [ ] No OAuth scope changes
- [ ] Access control unchanged
- [ ] Audit logging unaffected

## Deployment Impact
Confirm:

- [ ] No deployment changes
- [ ] Requires migration before deploy
- [ ] Requires config update

## Smoke Checks
Commands to verify production health after deployment:

```bash
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/readyz
journalctl -u zumbot-backend -n 100 --no-pager
```

## Documentation Updates
List updated docs:

- `docs/90_codex/CODEX_OPERATING_SYSTEM.md`
- `README.md`
- other docs

## Definition of Done
Confirm:

- [ ] User Story referenced
- [ ] Architecture reviewed
- [ ] Tests executed
- [ ] Documentation updated
- [ ] No architectural rule violations
