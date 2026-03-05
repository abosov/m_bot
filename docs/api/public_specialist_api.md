# Public Specialist API (canonical reference)

Этот файл оставлен как точка входа в раздел API.

Единый источник правды по публичному endpoint специалиста:
- `GET /api/public/specialists/{public_slug}`
- правила slug (формат `^[A-Za-z]+[A-Za-z0-9]*_[0-9]{2}$` и диапазон `10..30`)
- published-only поведение
- точная форма ответа `PublicSpecialistResponse` (`profile`, `blocks`, `media`)
- security notes (включая запрет на возврат `file_key`, токенов и внутренних полей)

См. подробную спецификацию в `docs/api/public_specialist.md`.
