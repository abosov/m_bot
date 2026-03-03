# Admin Console

## 1. Цель

Admin Console — это внутренний модуль управления системой Zumbot, предназначенный для роли `super_admin`.

Цели:
- наблюдение за состоянием системы
- анализ активности специалистов
- продуктовая аналитика
- мониторинг технического состояния
- в перспективе — управление специалистами и биллинг

Admin Console не является публичной частью продукта.

---

## 2. Подход к разработке

Разработка Admin Console ведётся строго по следующему жизненному циклу:

Каждая фича проходит этапы:

1. Архитектор
2. Архитектор данных
3. UX-дизайнер
4. Разработчик
5. Технический писатель
6. Тестировщик
7. Специалист по информационной безопасности

Каждый этап фиксируется в документации.

---

## 3. Использование User Stories

Каждая функциональность реализуется через короткие User Stories.

Формат:

US-AD-<номер>

Как <роль>  
Я хочу <действие>  
Чтобы <ценность>

Обязательные разделы:

- Acceptance Criteria
- Data impact
- API impact
- Security impact
- Tests required
- Documentation required

---

## 4. Эпики Admin Console

### EPIC A — Foundation
- A1: Admin UI entry point
- A2: Admin authentication model
- A3: Role-based access model

### EPIC B — Specialists Dashboard
- B1: Specialists list
- B2: Specialist activity metrics
- B3: Specialist detail view
- B4: Filters and sorting

### EPIC C — Product Overview
- C1: Global system metrics
- C2: Activity trends

### EPIC D — System Monitoring
- D1: Heartbeat visibility
- D2: Error inspection
- D3: Webhook / Google API failures

### EPIC E — Admin Actions (Future)
- E1: Disable specialist
- E2: Reset OAuth
- E3: Force onboarding state

---

## 5. Принципы проектирования

- Минимальный MVP сначала
- Атомарные изменения
- Каждая фича — отдельный логический блок
- Никаких "скрытых" изменений без документации
- Все изменения должны быть обратимыми
- Security-by-default

---

## 6. Definition of Done для каждой User Story

User Story считается завершённой только если:

- Реализован backend
- Реализован frontend (если требуется)
- Обновлена документация
- Добавлены тесты
- Пройден security-review
- Нет регрессии существующего функционала

---

## 7. Связанные документы

- docs/30_architecture/*
- docs/20_user_stories/*
- docs/31_security_model.md (если существует)
- docs/35_ops/*
- docs/36_runbooks/*

---

## 8. Access & Security

- `/admin` и `/admin/*` не публикуются наружу (без внешнего nginx/public routing).
- Доступ выполняется только через SSH tunnel до `127.0.0.1:8000`.
- Авторизация выполняется через заголовок `X-API-Key` (значение `ADMIN_API_KEY`).
- Для `GET /admin` любой неуспех авторизации возвращает `404` (anti-enumeration).
- Запрещено логировать значение `X-API-Key`/`ADMIN_API_KEY` в приложении, прокси и диагностических скриптах.

---

## Implemented

### US-AD-1 — Admin Console Entry Point
Status: Implemented
Access: X-API-Key header
Security model: return 404 if unauthorized

### US-AD-2 — Specialists list dashboard (MVP)
Status: Implemented (backend endpoint)
Doc: [US-AD-2 specification](./us_ad_2_specialists_list.md)

---

## 9. Endpoints

Все endpoint-ы Admin Console являются внутренними (`/admin/*`) и требуют заголовок `X-API-Key`.

### GET /admin/specialists

Назначение: список специалистов для MVP dashboard с базовыми метриками.

Query params:
- `limit` (optional, default `100`, clamp `1..500`)
- `offset` (optional, default `0`)
- `status` (optional, exact match)

Response:
- `items`: список специалистов с полями:
  - `specialist_id`
  - `public_name`
  - `status`
  - `created_at`
  - `tariff_plan`
  - `clients_count`
  - `last_activity_at` (nullable)
- `limit`
- `offset`

---

## 10. Access

Подробный runbook по доступу к Admin Console (SSH tunnel и примеры `curl`):

- [Access Runbook](./access.md)
