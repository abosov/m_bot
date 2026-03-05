# User Flow: Public Specialist Page (Frontend Template)

## Базовая структура страницы
Страница `specialist_profile_page` реализована как одностраничный лендинг с базовыми блоками (без стилизации):

1. `Header`
2. `Hero`
3. `SectionAbout`
4. `SectionEducation`
5. `SectionDocuments`
6. `SectionServices`
7. `SectionReviews`
8. `SectionCTA`

## Data flow
1. Роутер передает `slug` в `SpecialistProfilePage`.
2. На фронтенде выполняется валидация slug:
   - regex `^[A-Za-z]+[A-Za-z]_[1-9][0-9]$`
   - исключение зарезервированных путей: `pricing`, `privacy`, `terms`, `revoke-access`, `api`, `static`, `assets`
   - числовой суффикс в диапазоне `10..30`
3. Если slug валиден — вызывается API `GET /api/public/specialists/{slug}`.
4. Если slug невалиден — отображается ошибка и API не вызывается.

## Безопасность
Frontend-валидация slug выполняется перед сетевым запросом, чтобы не отправлять запросы с невалидными или служебными путями.
