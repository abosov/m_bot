# US-AD-14 — Admin diagnostics tools

Status: Implemented (MVP)

## User Story

As a `super_admin`, I want to run safe diagnostics from Admin Console and get structured findings, so I can detect orphan specialist media and server dev artifacts without risking production data.

Core principle for US-AD-14: **read-only diagnostics only**.

---

## Scope

### In scope (implemented)

1. **Orphan specialist media diagnostics** (`orphan_specialist_media_scan`)
   - Checks DB `specialist_public_media.file_key` references against files in `PROFILE_UPLOADS_DIR`.
   - Reports:
     - `MISSING_MEDIA_FILE` — DB reference exists, file missing in storage.
     - `ORPHAN_MEDIA_OBJECT` — file exists in storage, no DB reference.

2. **Server dev artifacts diagnostics** (`server_clutter_scan`)
   - Scans only allowlisted directories:
     - `PROFILE_UPLOADS_DIR`
     - `LOG_DIR` (only when configured)
   - Detects clutter patterns such as `*.bak`, `*.old`, `*.tmp`, `*.swp`, `*~`, `*.sql.dump`, `*.sqlite3`.
   - Applies finding cap and emits `RESULT_TRUNCATED` when limit is reached.

3. **Admin-only run from UI API**
   - Endpoint is under `/admin/ui/*` and requires valid admin session cookie.
   - CSRF middleware is enforced for POST requests.

### Out of scope (not in US-AD-14)

- Any cleanup/delete action from diagnostics endpoint.
- Arbitrary command execution or user-provided scan paths.
- Auto-remediation workflows.

---

## API

### POST `/admin/ui/diagnostics/run`

Runs one predefined diagnostic check and returns result synchronously.

Request:

```json
{
  "check_type": "orphan_specialist_media_scan"
}
```

Allowed values for `check_type`:
- `orphan_specialist_media_scan`
- `server_clutter_scan`

Successful response example:

```json
{
  "status": "completed",
  "summary": {
    "scanned": 124,
    "findings_total": 2,
    "high": 1,
    "medium": 1,
    "low": 0
  },
  "findings": [
    {
      "severity": "high",
      "code": "MISSING_MEDIA_FILE",
      "entity_ref": "db:file_key:specialist/.../docs/file.pdf",
      "message": "DB reference points to missing storage file",
      "recommended_action": "Restore file or remove stale reference in dedicated remediation flow"
    }
  ]
}
```

Failure response example:

```json
{
  "status": "failed",
  "summary": {
    "scanned": 0,
    "findings_total": 1,
    "high": 1,
    "medium": 0,
    "low": 0
  },
  "findings": [
    {
      "severity": "high",
      "code": "DIAGNOSTIC_JOB_FAILED",
      "entity_ref": "server_clutter_scan",
      "message": "Diagnostic failed: RuntimeError",
      "recommended_action": "Check server logs and retry"
    }
  ]
}
```

---

## Security impact

1. **Read-only operations only**
   - Diagnostic code performs reads from DB and filesystem only.
   - No delete/update/write actions are performed by diagnostics.

2. **No shell injection surface**
   - No shell command execution is used.
   - No user-provided command/path parameters are accepted.

3. **Allowlisted scan paths only**
   - `server_clutter_scan` scans fixed allowlisted roots (`PROFILE_UPLOADS_DIR`, optional `LOG_DIR`).
   - Traversal uses `os.walk(..., followlinks=False)` and skips symlinked dirs/files.
   - Additional containment check ensures scanned files are inside allowlisted roots.

4. **Admin auth + CSRF required**
   - Valid admin session cookie required.
   - CSRF token required for POST `/admin/ui/*` endpoints.
   - Unauthenticated access is denied under existing admin UI policy.

5. **Reduced data exposure**
   - Findings for clutter scan use safe root-relative `entity_ref` values instead of raw absolute host paths.

---

## Tests

Implemented automated tests for US-AD-14 diagnostics API:

1. `test_admin_diagnostics_orphan_media_reports_missing_and_orphan`
   - Confirms both `MISSING_MEDIA_FILE` and `ORPHAN_MEDIA_OBJECT` are reported.
   - Verifies DB row count is unchanged (read-only invariant).

2. `test_admin_diagnostics_server_clutter_scan_reports_dev_artifacts`
   - Confirms pattern-based findings (`TEMP_ARTIFACT`, `STRAY_BACKUP_FILE`).

3. `test_admin_diagnostics_requires_authenticated_session`
   - Confirms anonymous request is rejected.

4. `test_admin_diagnostics_requires_csrf_for_post`
   - Confirms POST without CSRF token is rejected.

5. `test_admin_diagnostics_server_clutter_scan_is_allowlisted`
   - Confirms file inside allowlisted path is reported.
   - Confirms file outside allowlisted path is not reported.
