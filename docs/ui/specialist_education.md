# UI: Блок "Образование" специалиста

Компонент: `frontend/components/specialist/SectionEducation.tsx`.

## Источник данных
Используется `specialist_public_block` с `block_type = education`.

## Отображение
- Если блок отсутствует — секция не рендерится.
- Если есть данные — показывается список (`<ul><li>...</li></ul>`).
- Поддерживаются форматы:
  - массив строк (`items`)
  - строка, разбитая по переводам строки (`content/body/text`)

## Безопасность
Перед отображением каждый элемент проходит sanitization:
- удаляются `<script>...</script>`
- удаляются inline-обработчики (`on*`)
- удаляются `javascript:` payload
