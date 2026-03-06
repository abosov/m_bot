# Media storage security rules

## Scope
Private specialist profile media uploads (`photo` and `document`) saved to local filesystem and tracked in `specialist_public_media`.

## Storage model
- Files are stored under `PROFILE_UPLOADS_DIR` (default: `/var/lib/zumbot/uploads`).
- `file_key` format:
  - `specialist/<specialist_id>/photo/<uuid>_<safe_filename>`
  - `specialist/<specialist_id>/docs/<uuid>_<safe_filename>`
- `file_key` is internal and must not be exposed in public contours.

## Security controls
- Path traversal protection:
  - sanitize uploaded filename,
  - strip separators `/` and `\\`,
  - neutralize `..` segments,
  - never join with user-controlled absolute paths.
- Size limits:
  - photo: default 10MB,
  - document: default 20MB.
- Content type allowlist:
  - photo: jpeg/png/webp,
  - document: pdf/jpeg/png.
- Atomic write:
  - write to temp file,
  - finalize via atomic rename.

## Access
- Upload/list endpoints require valid `web_auth_session` cookie.
- `specialist_id` is derived from session, not from request params/body.
- File contents and multipart bodies must not be logged.

## Public API isolation
- Public API must not return `file_key`.
- Public specialist endpoints remain unchanged and must not leak private media storage details.

## Ops check: orphan specialist media

Для операционной сверки диска и БД используется `scripts/check_orphan_specialist_media.sh`.

Назначение:
- обнаружить директории `specialist/<id>` на файловой системе,
  для которых отсутствует строка в таблице `specialist`.

Ограничения и безопасность:
- скрипт только диагностирует (`ORPHAN MEDIA: ...`) и ничего не удаляет автоматически;
- рассчитан на VPS-пути и локальный PostgreSQL, не является универсальным инструментом для произвольных окружений;
- удаление orphan-каталогов выполняется только после ручной проверки,
  чтобы исключить риск потери валидных медиа.
