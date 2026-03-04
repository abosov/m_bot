# US-AD-8 — Admin Audit Log Viewer

Status: Planned

## 1. User Story

Как `super_admin`  
Я хочу видеть историю действий администратора  
Чтобы понимать кто и когда изменял систему.

## 2. Scope

Просмотр записей `admin_audit_log` через UI.

## 3. Endpoint

`GET /admin/ui/audit-log`

- cookie required
- unauth -> `404`

## 4. Filters

Поддерживаемые query-параметры:

- `since`
- `until`
- `action`
- `target_type`
- `target_id`
- `success`
- `limit`
- `offset`

`limit` clamp: `1..500`.

## 5. Response

```json
{
  "items": [...],
  "limit": 50,
  "offset": 0
}
```

## 6. Security

- payload sanitized
- secrets forbidden
- cookie auth
- `404` unauth

## 7. Tests

- filters
- pagination
- auth
- payload sanitization

## Security review outcome

- Payload sanitization confirmed: sensitive keys related to secrets/tokens are removed from UI payload output.
- Secret exposure check passed: audit response for UI does not return secret values.
- Token exposure check passed: access/refresh tokens are not exposed in UI response payload.
- Authentication model confirmed: endpoint requires valid admin cookie session.
- Anti-enumeration confirmed: unauthenticated request returns `404`.
