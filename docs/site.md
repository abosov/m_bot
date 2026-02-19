# Статический сайт (landing) в FastAPI

## Где лежит сайт

Статические файлы находятся в `web/`:

- `web/index.html` — главная страница.
- `web/assets/` — стили, JS и прочие статические файлы.

## Публичные страницы (SITE_PAGES)

Актуальный список маршрутов из `web_server.py`:

- `/` → `index.html`
- `/features` → `features.html`
- `/pricing` → `pricing.html`
- `/specialists` → `specialists.html`
- `/contacts` → `contacts.html`
- `/privacy` → `privacy.html`
- `/terms` → `terms.html`
- `/revoke-access` → `revoke-access.html`
- `/privacy-ru` → `privacy-ru.html`
- `/terms-ru` → `terms-ru.html`

Также:

- `/assets/*` раздаётся из `web/assets` через `StaticFiles`.
- Если `web/` или `web/index.html` отсутствуют, сайт не монтируется, но API продолжает работать.
