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
- Для корректной работы якорей без хрупкого верхнего отступа используется связка `scroll-padding-top` + `scroll-margin-top`:
  - `frontend/pages/specialist_profile_page.tsx` измеряет текущую высоту sticky header в runtime и записывает `--specialist-sticky-offset` в `document.documentElement`;
  - `.specialist-page` в `frontend/styles/specialist.css` использует `scroll-padding-top: var(--specialist-sticky-offset, 120px)`;
  - `.specialist-page__section` использует `scroll-margin-top: var(--specialist-sticky-offset, 120px)`.

## Проверка
Клик по пункту меню переводит к секции с тем же `id`.

## Безопасность
Пользовательский ввод не используется.
