# UI: Якорная навигация в меню страницы специалиста

## Цель
Меню sticky header прокручивает страницу к соответствующим секциям лендинга.

## Якоря меню
- `#about`
- `#education`
- `#documents`
- `#services`
- `#reviews`
- `#booking`

## Реализация
- Ссылки меню заданы в `frontend/components/specialist/Header.tsx`.
- На секциях страницы установлены соответствующие `id` в `frontend/pages/specialist_profile_page.tsx`.
- Для предотвращения перекрытия заголовков sticky header применяется `scroll-margin-top` у секций (`.specialist-page__section`) в `frontend/styles/specialist.css`.

## Проверка
Клик по пункту меню переводит к секции с тем же `id`.

## Безопасность
Пользовательский ввод не используется.
