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
- `/legal` → `legal.html`
- `/privacy-ru` → `privacy-ru.html`
- `/terms-ru` → `terms-ru.html`
- `/revoke-access-ru` → `revoke-access-ru.html`
- `/success` → `success.html`

Также:

- `/assets/*` раздаётся из `web/assets` через `StaticFiles`.
- Если `web/` или `web/index.html` отсутствуют, сайт не монтируется, но API продолжает работать.

## Единые шаблонные плейсхолдеры

Страницы в `web/*.html` должны использовать централизованные плейсхолдеры:

- `{{SITE_HEADER}}` — единая шапка сайта.
- `{{SITE_FOOTER}}` — единый подвал сайта.

Оба блока подставляются в `web_server.py` при рендеринге страницы. Хедер и футер нельзя дублировать вручную внутри HTML-страниц.

## Правила ссылок в футере

`{{SITE_FOOTER}}` рендерится в зависимости от языка страницы:

- RU страницы (`/`, `/features`, `/pricing`, `/specialists`, `/contacts`, `/privacy-ru`, `/terms-ru`, `/legal`, `/revoke-access-ru`, `/success`):
  - `Политика конфиденциальности` → `/privacy-ru`
  - `Пользовательское соглашение` → `/terms-ru`
  - `Реквизиты и правовая информация` → `/legal`
- EN страницы (`/privacy`, `/terms`, `/revoke-access`):
  - `Privacy Policy` → `/privacy`
  - `Terms of Service` → `/terms`
  - `Legal details` → `/legal`

Для футера используются только относительные ссылки (`/privacy`, `/terms` и т.д.); абсолютные URL вида `https://zumbot.ru/...` не допускаются.


## Правило внешних ссылок и Telegram CTA

Все переходы в Telegram и другие внешние сервисы должны открываться **только в новой вкладке**, чтобы пользователь не терял текущую страницу сайта.

- Для ссылок используйте `target="_blank"` и `rel="noopener noreferrer"`.
- Нельзя заменять текущую страницу сайта переходом во внешний сервис через текущий tab.

## Runbook'и по публичному сайту

- Contact form (`/contacts`): `docs/runbook/contact-form.md`

## Юрисдикция в Terms

Для страницы условий использования (`/terms`, `/terms-ru`) формулировка о применимом праве должна соответствовать опубликованной юрисдикции и реквизитам исполнителя (РФ). Не допускайте противоречивых формулировок в духе другой страны.
