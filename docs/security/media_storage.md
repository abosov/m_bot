# Media storage security rules

## Scope
Private specialist profile media uploads (`photo` and `document`) saved to local filesystem and tracked in `specialist_public_media`.

## Storage model
- Files are stored under `PROFILE_UPLOADS_DIR` (default: `/var/lib/zumbot/uploads`).
- `file_key` format:
  - `media/specialists/<specialist_id>/profile_photo.jpg` (hero-photo, единственный актуальный файл)
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
- Image pipeline for profile photo:
  - magic-bytes validation (jpeg/png/webp),
  - EXIF orientation normalize, center crop 4:5, resize 800x1000, JPEG quality=85,
  - decoded image pixels limit: 20MP.
- Content type allowlist:
  - photo upload input: jpeg/png/webp,
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
- Public specialist endpoints must not leak private media storage details.
- Public media delivery is restricted to profile photos (`media_type=photo`) only.
- Document keys remain private and are rejected from public media route.

## Specialist delete lifecycle coverage
- В текущем репозитории destructive specialist delete реализован в admin/test контурах:
  - `POST /admin/ui/specialists/{specialist_id}/delete-test` (`web_server.py`),
  - test reset flow (`services/test_data_reset.py`).
- Cleanup media files/rows должен выполняться в этих реальных destructive потоках; отдельного общего runtime delete-service сейчас нет.

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
