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

## Planned

### US-AD-2 — Specialists list dashboard (MVP)
Status: Planned / In progress
Doc: [US-AD-2 specification](./us_ad_2_specialists_list.md)

### US-AD-9 — Admin Security Hardening

Admin Console protected by multiple layers:

1. SSH tunnel access
2. Nginx Basic Auth
3. Admin session cookie
4. CSRF token validation
5. ADMIN_API_KEY for API endpoints

This layered security prevents:

- brute-force access
- endpoint enumeration
- unauthorized admin access

### US-AD-10 — Test specialist identification
Status: Implemented (marker + visibility)
Doc: [US-AD-10 specification](./us_ad_10_test_specialist_marking.md)

Implemented scope:
- `specialist.is_test` marker in schema (single source of truth)
- incompatibility guard for `is_system` + `is_test`
- admin payload visibility (`GET /admin/ui/specialists`, `GET /admin/ui/specialists/{id}`)
- `test_only=1` filter in specialists list
- UI `TEST` marker in specialists list/detail

Boundary clarification:
- US-AD-10 introduces classification/visibility/filtering only.
- Destructive test-only guards and destructive workflows are implemented in follow-up stories (US-AD-11 / US-AD-12 / US-AD-13), not fully in US-AD-10.

### US-AD-11 — Safe deletion of one test specialist
Status: Planned
Doc: [US-AD-11 specification](./us_ad_11_delete_test_specialist.md)

### US-AD-12 — Bulk delete all test accounts
Status: Planned
Doc: [US-AD-12 specification](./us_ad_12_bulk_delete_test_accounts.md)

### US-AD-13 — Reset test specialist data without deleting specialist
Status: Planned
Doc: [US-AD-13 specification](./us_ad_13_reset_test_specialist_data.md)

### US-AD-14 — Admin diagnostics / cleanup tools (read-only diagnostics)
Status: Planned
Doc: [US-AD-14 specification](./us_ad_14_admin_diagnostics_cleanup_tools.md)


---

### US-AD-1 — Admin Console Entry Point
Status: Implemented
Access: X-API-Key header
Security model: return 404 if unauthorized

### US-AD-2 — Specialists list dashboard (MVP)
Status: Implemented (backend endpoint)
Doc: [US-AD-2 specification](./us_ad_2_specialists_list.md)

### US-AD-3 — Admin Overview (MVP)
Status: Implemented
Doc: [US-AD-3 specification](./us_ad_3_overview.md)

### US-AD-4.1 — System specialists filtering
Status: Implemented
Doc: [US-AD-4.1 specification](./us_ad_4_1_system_accounts.md)

### US-AD-4 — Specialists Operational Table
Status: Implemented
Doc: [US-AD-4 specification](./us_ad_4_specialists_operational_table.md)

### US-AD-5 — Specialist Detail Page
Status: Implemented
Doc: [US-AD-5 specification](./us_ad_5_specialist_detail_page.md)

### US-AD-6 — Observability (Logs + Heartbeats)
Status: Implemented
Admin observability tools:
- logs viewer
- heartbeat monitor

Endpoints:
- `GET /admin/ui/logs`
- `GET /admin/ui/heartbeats`

Doc: [US-AD-6 specification](./us_ad_6_observability_logs_heartbeats.md)

### US-AD-8 — Admin Audit Log Viewer
Status: Implemented
Admin audit log viewer.

Endpoint:
- `GET /admin/ui/audit-log`

Doc: [US-AD-8 specification](./us_ad_8_admin_audit_log_viewer.md)

---

### US-AD-7 — Admin Actions: Specialist Management
Status: Implemented
Doc: [US-AD-7 specification](./us_ad_7_admin_actions_specialist_management.md)


## 9. Endpoints

Все endpoint-ы Admin Console являются внутренними (`/admin/*`) и требуют заголовок `X-API-Key`.

- `GET /admin/ui/overview` (UI cookie auth)
  - Query param: `include_system` (`0|1`, optional, default `0`).
  - По умолчанию системные аккаунты исключаются; для включения используйте `include_system=1`.

- `GET /admin/ui/specialists` (UI cookie auth)
  - Query params: `limit`, `offset`, `status`, `include_system=0|1` (default `0`), `oauth_missing=0|1` (default `0`), `calendar_missing=0|1` (default `0`), `inactive_days_gt` (`>=1`, optional).

- `GET /admin/ui/logs` (UI cookie auth)
  - Просмотр журналов системы в Admin Console.

- `GET /admin/ui/heartbeats` (UI cookie auth)
  - Мониторинг heartbeat-сигналов интеграций/воркеров.

- `GET /admin/ui/audit-log` (UI cookie auth)
  - Просмотр audit-журнала административных действий.

- `GET /admin/ui/specialists/{specialist_id}` (UI cookie auth)
  - Детальная JSON карточка специалиста (`basic`, `integration`, `activity`, `errors`).
  - При невалидной/отсутствующей cookie возвращает `404` (anti-enumeration).

- `POST /admin/ui/specialists/{specialist_id}/disable` (UI cookie auth + CSRF)
  - Отключение специалиста (idempotent), для system account -> `403`.

- `POST /admin/ui/specialists/{specialist_id}/enable` (UI cookie auth + CSRF)
  - Включение специалиста (idempotent).

- `POST /admin/ui/specialists/{specialist_id}/reset-oauth` (UI cookie auth + CSRF)
  - Сброс OAuth-связки специалиста, без возврата секретов.

- `POST /admin/ui/specialists/{specialist_id}/tariff` (UI cookie auth + CSRF)
  - Смена `specialist_profile.tariff_plan` по allowlist enum `TariffPlan`.

- `GET /admin/specialists/{specialist_id}`
  - API режим: JSON detail payload при валидном `X-API-Key` (`403` при неверном/отсутствующем ключе).
  - Browser HTML режим: detail page при `Accept: text/html` и валидной cookie `admin_session` (`404` без cookie).

### GET /admin/specialists

Назначение: список специалистов для MVP dashboard с базовыми метриками.

## 9.1 Admin Console Navigation

- Overview
- Specialists
- Logs
- Heartbeats
- Audit Log

Query params:
- `limit` (optional, default `100`, clamp `1..500`)
- `offset` (optional, default `0`)
- `status` (optional, exact match)
- `include_system` (optional, default `0`):
  - по умолчанию системные аккаунты исключаются;
  - при `include_system=1` системные аккаунты включаются в список.

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
