## Story ID and Title
US-AUTO-50 — AI review must produce structured output

## Objective
Гарантировать, что AI review всегда возвращает строго структурированный artifact, пригодный для normalization, classification и gate, без возможности неструктурированного ответа.

## Scope
- Валидация структуры AI review output
- Детектирование echo / prompt leakage
- Fail-closed останов pipeline при некорректном output
- Минимальные изменения внутри review pipeline

## Non-goals
- Изменение Codex runner
- Изменение логики classification
- Редизайн формата review
- Retry / orchestration логика

## Dependencies
- US-AUTO-49 (реализована)
- review pipeline (ai_review → normalization → classification → gate)

## Source of Truth
- automation/scripts/ai_review_story_run.sh
- automation/scripts/review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh

## Current Code Reality
- AI review может вернуть echo prompt
- Нет строгой проверки структуры
- normalization падает поздно
- classify блокируется неявно

## Target Outcome
- AI review output строго валидируется
- Любой невалидный output → fail-closed
- classify не запускается при invalid input
- причина ошибки явно фиксируется

## Atomic Task Isolation Contract
- Только enforcement структуры output
- Никаких изменений вне review pipeline
- Минимальный diff
- Один тип дефекта: invalid AI review output

## Risks
- Ложно-положительные reject (слишком строгая валидация)
- Нарушение совместимости с текущими valid output

## Manual Actions
- Проверить работу на валидном и невалидном output
- Прогнать полный pipeline

## Acceptance Notes
- Нет прохода pipeline при неструктурированном output
- Valid output проходит без изменений
- Gate возвращает корректную причину отказа

---

