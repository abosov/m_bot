# Система логирования взаимодействий (Logging System) — v2.0

## Обзор
Система фиксирует все события в экосистеме. Версия 2.0 ориентирована на "читаемость глазами" и глубокую отладку через FSM-состояния.

## Что логируется (в MVP)
- входящие и исходящие сообщения Telegram (таблица `message_logs`);
- технические проверки доступности сервиса:
  - `/readyz` → `service_heartbeats` (готовность сервиса);
  - команда `/status` в master_bot → `bot_health_checks` (здоровье личных ботов).

`/readyz` по умолчанию включён только в `prod` на VPS.
В `local` он выключен, если явно не задано `ENABLE_READYZ=true`.

## Что запрещено логировать
В логах и технических таблицах **нельзя** хранить секреты и токены:
- `MASTER_BOT_TOKEN`, `bot_token`;
- `refresh_token`, `access_token`;
- `webhook_secret`;
- `oauth` `code`/`state` (кроме безопасного внутреннего идентификатора).

Если нужно указать причину ошибки — пишется краткий тип/код ошибки
без деталей, содержащих секреты.

## Схема данных (Table: `message_logs`)

| Группа | Поле | Тип | Описание |
| :--- | :--- | :--- | :--- |
| **IDs** | `id` | UUID | Идентификатор записи лога. |
| **Time** | `created_at` | DateTime | Время события (UTC). |
| **Actors** | `direction` | Enum | `IN` или `OUT`. |
| | `bot_id` | BigInt | ID бота Telegram (`getMe.id`). |
| | `bot_username` | String | Username бота специалиста. |
| | `specialist_name`| String | Публичное имя специалиста. |
| | `user_handle` | String | Никнейм (@username) или имя клиента. |
| **Content**| `message_type` | String | `message`, `callback_query`, `text` и т.д. |
| | `content` | Text | Тело сообщения. |
| **Context**| `fsm_state` | String | Текущий шаг пользователя в боте (FSM State). |
| | `handler_name` | String | Какая функция обработала запрос. |
| **IDs** | `specialist_id` | UUID | Внутренний ID специалиста. |
| | `tg_user_id` | BigInt | ID пользователя в Telegram. |
| **Debug** | `is_error` | Boolean | Была ли ошибка. |
| | `error_details` | Text | Traceback ошибки. |
| | `processing_time`| Float | Время ответа в секундах. |

Примечание:
- Логи хранятся в БД и используются для отладки FSM и бизнес-логики.

## Таблица `service_heartbeats`

Хранит историю технических heartbeat-записей с `/readyz` для диагностики доступности сервиса.
Запись создаётся не чаще одного раза в минуту, чтобы не перегружать БД.

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| `id` | UUID | Идентификатор записи. |
| `service_name` | Text | Имя сервиса (например, `backend`). |
| `ts` | DateTime | Время записи (UTC). |
| `db_ok` | Boolean | Статус проверки БД. |
| `loop_ok` | Boolean | Статус проверки event loop. |
| `latency_ms` | Integer | Время ответа `/readyz` в миллисекундах. |
| `details` | Text/JSON | Дополнительные детали (например, ошибка БД). |

## Таблица `bot_health_checks`

Хранит результаты проверок `/status` для personal bot каждого специалиста.
Записи позволяют анализировать периодические ошибки или проблемы с токенами.
В `error_details` допускается только краткая техническая причина без секретов.

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| `id` | UUID | Идентификатор записи. |
| `specialist_id` | UUID | Внутренний ID специалиста. |
| `bot_user_id` | BigInt | Telegram ID бота (`getMe.id`). |
| `checked_at` | DateTime | Время проверки (UTC). |
| `status` | Enum | `ok`, `unauthorized`, `temp_error`. |
| `latency_ms` | Integer | Время ответа в миллисекундах. |
| `error_details` | Text | Краткая техническая причина без секретов. |

## Service heartbeat (loop tick)

Помимо логирования сообщений, сервис пишет технические логи health-checks:
- heartbeat_task фиксирует старт/останов фоновой корутины, которая обновляет
  тик event loop каждые 5 секунд. Это позволяет детектировать зависание
  цикла, даже если HTTP-сервер продолжает отвечать.
- `/readyz` логирует `db_ok`, `loop_ok`, `latency_ms` для наблюдаемости
  состояния БД и жизнеспособности event loop.
