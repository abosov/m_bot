## Source of Truth
- Review pipeline scripts
- AI review output artifact

## Current Code Reality
- AI review не гарантирует структуру
- normalization ожидает структуру, но не валидирует заранее
- echo output ломает pipeline

## Architectural Intent
- Ввести строгий контракт output
- Fail-closed на ранней стадии
- Обеспечить deterministic поведение pipeline

## Risks
- Жёсткая валидация может отсеять частично валидные ответы
- Возможна необходимость future retry механизма

## Acceptance Notes
- Все невалидные output блокируются
- Все валидные проходят без изменений

---

