# Story Bundle Pack
Story-ID: US-AUTO-50
Version: 1

=== FILE: 00_story.md ===
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

=== FILE: 01_context_bundle.md ===
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

=== FILE: 02_file_scope.md ===
## Files Allowed To Change
- automation/scripts/ai_review_story_run.sh
- automation/scripts/review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh
- tests/test_ai_review_story_run.py
- tests/test_analyze_story_run.py
- tests/test_classify_review_story_run.py
- tests/test_review_gate_story_run.py
- tests/test_review_pipeline.py
- tests/test_review_pipeline_validation_contract.py

## Files Not Allowed To Change
- automation/run_codex_task.sh
- automation/scripts/run_story.sh
- automation/scripts/finalize_story.sh
- automation/scripts/materialize_story_bundle.sh
- automation/scripts/validate_story_bundle.sh
- automation/bundle_packs/*
- automation/bundles/active/*

## Scope Notes
- Только review pipeline
- Никаких изменений execution pipeline
- Только validation + fail-closed

---

=== FILE: 03_master_prompt.md ===
## Role
You are a strict pipeline governance enforcer.

## Goal
Ensure AI review always produces a valid structured output and never allows invalid or unstructured responses to proceed.

## Source of Truth
- AI review output artifact
- Required structure sections

## Files Allowed To Change
- automation/scripts/ai_review_story_run.sh
- automation/scripts/review_story_run.sh
- automation/scripts/classify_review_story_run.sh
- automation/scripts/review_gate_story_run.sh
- automation/scripts/analyze_story_run.sh
- tests/test_ai_review_story_run.py
- tests/test_analyze_story_run.py
- tests/test_classify_review_story_run.py
- tests/test_review_gate_story_run.py
- tests/test_review_pipeline.py
- tests/test_review_pipeline_validation_contract.py

## Files Not Allowed To Change
- automation/run_codex_task.sh
- automation/scripts/run_story.sh
- automation/scripts/finalize_story.sh
- automation/scripts/materialize_story_bundle.sh
- automation/scripts/validate_story_bundle.sh
- automation/bundle_packs/*
- automation/bundles/active/*

## Atomic Task Isolation Contract
- Only enforce output structure
- Do not expand scope
- Do not refactor unrelated code
- Stop immediately on scope violation

## Execution Gate
- If output is invalid → STOP
- Do not proceed to classification
- Fail-closed always

## Implementation Requirements
1. Validate presence of:
   - "# AI Review"
   - "# AI Review Result"
2. Detect echo:
   - output identical or highly similar to prompt
3. Detect empty/malformed output
4. On failure:
   - emit reason: ai_review_normalization_failed
   - stop pipeline
5. Maintain compatibility with valid outputs

## Verification Requirements
- Invalid output → rejected
- Valid output → passes unchanged
- No regression in existing flows

## Output
- Deterministic structured validation
- Explicit failure reason

---

=== FILE: 04_review_checklist.md ===
## Scope Validation
- [ ] Только review pipeline изменён
- [ ] Нет изменений вне scope

## Functional Validation
- [ ] AI review output валидируется
- [ ] Echo корректно детектируется
- [ ] Empty output блокируется

## Verification
- [ ] Invalid output → REJECT
- [ ] Valid output → APPROVE
- [ ] classify не запускается при invalid input

## HARD BLOCK
- [ ] Любой невалидный output не проходит дальше

---

=== FILE: 05_followups.md ===
## Follow-Up Prompt Queue
- Add retry logic for AI review
- Introduce JSON schema validation
- Improve AI prompt robustness

## Iteration Notes
- Возможен future переход к строго JSON output
- Возможна метрика качества AI review

---

=== FILE: 06_manual_actions.md ===
## Required Human Actions
1. Создать bundle:
   automation/bundle_packs/US-AUTO-50.bundle.md

2. Materialize:
   automation/scripts/materialize_story_bundle.sh US-AUTO-50

3. Validate:
   automation/scripts/validate_story_bundle.sh US-AUTO-50

4. Создать ветку и commit:
   feat/us-auto-50-bundle

5. Запустить:
   automation/scripts/run_story.sh US-AUTO-50

6. Проверить:
   automation/scripts/analyze_story_run.sh US-AUTO-50

## Completion Status
- Bundle готов к materialize и validate
- Готов к запуску pipeline