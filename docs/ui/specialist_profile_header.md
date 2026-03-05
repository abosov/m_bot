# UI: Sticky Header на странице специалиста

## Назначение
Фиксированная шапка публичной страницы специалиста всегда остается в верхней части экрана и дает доступ к навигации по секциям лендинга.

## Состав header
- `display_name`
- `specialization`
- Меню:
  - О себе
  - Образование
  - Документы
  - Услуги и цены
  - Отзывы
  - Записаться

## Реализация
- Компонент: `frontend/components/specialist/Header.tsx`
- Стили: `frontend/styles/specialist.css`

Ключевые CSS параметры:
- `position: sticky`
- `top: 0`
- `z-index: 100`

Чтобы header не перекрывал первый блок, у контейнера страницы задан `padding-top`, равный высоте header (`--specialist-header-height`).

## Безопасность
Компонент не принимает пользовательский ввод для разметки и не использует `dangerouslySetInnerHTML`.
