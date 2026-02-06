# Система логирования взаимодействий (Logging System) — v2.0

## Обзор
Система фиксирует все события в экосистеме. Версия 2.0 ориентирована на "читаемость глазами" и глубокую отладку через FSM-состояния.

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
