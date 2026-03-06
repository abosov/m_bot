# UI: Sticky Header + Sticky Section Navigation на странице специалиста

## Назначение
Публичная страница использует двухуровневую sticky-навигацию:
1. **Top sticky header** — identity специалиста (`display_name`, `specialization`).
2. **Sticky section nav** — pill/tab навигация по секциям (`О себе`, `Образование`, `Документы`, `Услуги и цены`, `Отзывы`).

Такое разделение снижает визуальный шум и делает long-scroll страницу управляемой на desktop/tablet/mobile.

## Состав
### Header (`#specialist-sticky-header`)
- `display_name`
- `specialization`

### Section nav (`#specialist-section-nav`)
- semantic `<nav aria-label="Навигация по разделам специалиста">`
- links в формате chips/pills
- active state текущей секции

## Реализация
- Header: `frontend/components/specialist/Header.tsx`
- Section nav: `frontend/components/specialist/SectionNav.tsx`
- Runtime page: `frontend/pages/specialist_profile_page.tsx`
- Bridge route (`GET /{public_slug}`): `web_server.py`
- Styles: `frontend/styles/specialist.css`

## Active section tracking
Текущая секция определяется через `IntersectionObserver`:
- observer отслеживает видимые секции;
- выбирается наиболее релевантная видимая секция (по intersection ratio + top position);
- соответствующий chip получает active-state (`.specialist-subnav__link--active`);
- активный пункт мягко подскролливается в видимую область горизонтального nav-container на узких экранах.

## Anchor/offset поведение
Чтобы заголовки секций не перекрывались sticky-элементами:
- страница использует `scroll-padding-top: var(--specialist-sticky-offset, 120px)`;
- секции используют `scroll-margin-top: var(--specialist-sticky-offset, 120px)`;
- runtime измеряет высоты header + section-nav и обновляет CSS variables:
  - `--specialist-header-height`
  - `--specialist-subnav-height`
  - `--specialist-sticky-offset`

## Responsive behavior
- **Desktop**: pills в строку без дополнительной CTA-кнопки в subnav.
- **Tablet**: compact horizontal chip-nav, без ломания layout.
- **Mobile**: horizontal-scroll chip-nav и скрытые грубые scrollbar-артефакты.

## Безопасность
Компоненты header/subnav не рендерят HTML из пользовательского ввода и не используют `dangerouslySetInnerHTML`.
