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
- Компонент-цель: `frontend/components/specialist/Header.tsx`
- Website bridge route: `web_server.py` (`GET /{public_slug}`) рендерит ту же структуру sticky header/меню и использует тот же public API.
- Стили: `frontend/styles/specialist.css`

Ключевые CSS параметры:
- `position: sticky`
- `top: 0`
- `z-index: 100`

Чтобы header не перекрывал первый блок, у контейнера страницы задан `padding-top`, равный высоте header (`--specialist-header-height`).

## Безопасность
Компонент не принимает пользовательский ввод для разметки и не использует `dangerouslySetInnerHTML`.


## Примечание по routing
Legacy minimal page с `specialist-loading` / `specialist-content` и только тремя полями больше не является основной публичной страницей. Route `/{public_slug}` теперь сразу отдаёт полноразмерную структуру public specialist page с якорными секциями.
