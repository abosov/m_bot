# Admin Console Security

## Current security baseline

### Authentication

Admin login uses:

- `admin_session` cookie

Unauthenticated requests return:

- `404`

### CSRF

- `POST /admin/ui/*` endpoints require CSRF token.

### Audit

All admin actions write record to:

- `admin_audit_log`

### Sensitive data

- Tokens and secrets must be removed from payload.

### Future hardening

- US-AD-8.5 — session hardening
- US-AD-9 — rate limiting / fail2ban
