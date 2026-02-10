from __future__ import annotations

import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from sqlalchemy import and_, insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.sqltypes import DateTime as SADateTime
from sqlalchemy.sql.sqltypes import Enum as SAEnum

from database import (
    Appointment,
    BotHealthCheck,
    Client,
    GoogleOAuth,
    MessageLog,
    OAuthState,
    Specialist,
    SpecialistAuthTelegram,
    SpecialistCalendarSettings,
    SpecialistProfile,
    TelegramBot,
    WeeklyAvailability,
)
from services.test_data_reset import (
    DEFAULT_REGISTRY_PATH,
    _load_registry,
    _resolve_specialists,
    _resolve_tg_user_ids,
    execute_test_data_reset,
)

SNAPSHOT_DIR = Path("var/test_snapshots")

SNAPSHOT_TABLES: list[tuple[str, Any]] = [
    ("specialist", Specialist),
    ("specialist_auth_telegram", SpecialistAuthTelegram),
    ("specialist_profile", SpecialistProfile),
    ("client", Client),
    ("appointment", Appointment),
    ("weekly_availability", WeeklyAvailability),
    ("specialist_calendar_settings", SpecialistCalendarSettings),
    ("google_oauth", GoogleOAuth),
    ("oauth_state", OAuthState),
    ("telegram_bot", TelegramBot),
    ("message_logs", MessageLog),
    ("bot_health_checks", BotHealthCheck),
]


class TestDataSnapshotError(RuntimeError):
    pass


def _snapshot_path(baseline_name: str) -> Path:
    normalized = baseline_name.strip()
    if not normalized:
        raise TestDataSnapshotError("Имя baseline не может быть пустым.")
    if "/" in normalized or "\\" in normalized:
        raise TestDataSnapshotError("Имя baseline не должно содержать '/' или '\\'.")
    return SNAPSHOT_DIR / f"{normalized}.json"


def _serialize_value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


def _deserialize_value(column, value: Any) -> Any:
    if value is None:
        return None

    column_type = column.type
    if isinstance(column_type, SAEnum):
        enum_class = getattr(column_type, "enum_class", None)
        if enum_class is not None:
            return enum_class(value)
        return value

    if hasattr(column_type, "as_uuid") and getattr(column_type, "as_uuid", False):
        return uuid.UUID(value)

    if isinstance(column_type, SADateTime) and isinstance(value, str):
        return datetime.fromisoformat(value)

    return value


def _sort_rows(model, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pk_columns = [column.name for column in model.__table__.primary_key.columns]
    if not pk_columns:
        return sorted(rows, key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False))
    return sorted(rows, key=lambda row: tuple(str(row.get(col)) for col in pk_columns))


async def _fetch_table_rows(session: AsyncSession, model, where_clause) -> list[dict[str, Any]]:
    rows = (await session.execute(select(model).where(where_clause))).scalars().all()
    payload: list[dict[str, Any]] = []
    for row in rows:
        row_data = {
            column.name: _serialize_value(getattr(row, column.name)) for column in model.__table__.columns
        }
        payload.append(row_data)
    return _sort_rows(model, payload)


async def create_test_data_snapshot(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    baseline_name: str,
    registry_path: str | Path = DEFAULT_REGISTRY_PATH,
) -> dict[str, Any]:
    registry_file = Path(registry_path)
    accounts, _ = _load_registry(registry_file)
    selected_tg_user_ids, _, _ = _resolve_tg_user_ids(
        registry_accounts=accounts,
        names=None,
        tg_user_ids=None,
    )

    selected_client_tg_ids = {
        account.tg_user_id for account in accounts if account.role == "client" and account.tg_user_id in selected_tg_user_ids
    }

    async with session_factory() as session:
        specialists = await _resolve_specialists(session, selected_tg_user_ids)
        specialist_ids = list(specialists.keys())
        if not specialist_ids:
            raise TestDataSnapshotError("Не найдено специалистов для snapshot по указанному реестру.")

        client_rows = await _fetch_table_rows(
            session,
            Client,
            and_(Client.specialist_id.in_(specialist_ids), Client.tg_user_id.in_(selected_client_tg_ids)),
        )
        client_ids = [uuid.UUID(row["client_id"]) for row in client_rows]

        data: dict[str, list[dict[str, Any]]] = {
            "specialist": await _fetch_table_rows(session, Specialist, Specialist.specialist_id.in_(specialist_ids)),
            "specialist_auth_telegram": await _fetch_table_rows(
                session,
                SpecialistAuthTelegram,
                SpecialistAuthTelegram.specialist_id.in_(specialist_ids),
            ),
            "specialist_profile": await _fetch_table_rows(
                session,
                SpecialistProfile,
                SpecialistProfile.specialist_id.in_(specialist_ids),
            ),
            "client": client_rows,
            "appointment": await _fetch_table_rows(
                session,
                Appointment,
                and_(Appointment.specialist_id.in_(specialist_ids), Appointment.client_id.in_(client_ids)),
            ),
            "weekly_availability": await _fetch_table_rows(
                session,
                WeeklyAvailability,
                WeeklyAvailability.specialist_id.in_(specialist_ids),
            ),
            "specialist_calendar_settings": await _fetch_table_rows(
                session,
                SpecialistCalendarSettings,
                SpecialistCalendarSettings.specialist_id.in_(specialist_ids),
            ),
            "google_oauth": await _fetch_table_rows(
                session,
                GoogleOAuth,
                GoogleOAuth.specialist_id.in_(specialist_ids),
            ),
            "oauth_state": await _fetch_table_rows(
                session,
                OAuthState,
                OAuthState.specialist_id.in_(specialist_ids),
            ),
            "telegram_bot": await _fetch_table_rows(
                session,
                TelegramBot,
                TelegramBot.specialist_id.in_(specialist_ids),
            ),
            "message_logs": await _fetch_table_rows(
                session,
                MessageLog,
                MessageLog.specialist_id.in_(specialist_ids) | MessageLog.tg_user_id.in_(selected_tg_user_ids),
            ),
            "bot_health_checks": await _fetch_table_rows(
                session,
                BotHealthCheck,
                BotHealthCheck.specialist_id.in_(specialist_ids),
            ),
        }

    snapshot_payload = {
        "baseline_name": baseline_name,
        "created_at": datetime.now().isoformat(),
        "registry_path": str(registry_file),
        "selected_tg_user_ids": sorted(selected_tg_user_ids),
        "specialist_ids": sorted(str(value) for value in specialist_ids),
        "tables": data,
    }

    path = _snapshot_path(baseline_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot_payload, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")

    return {
        "path": str(path),
        "specialist_count": len(specialist_ids),
        "table_counts": {table_name: len(rows) for table_name, rows in data.items()},
    }


async def restore_test_data_snapshot(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    baseline_name: str,
    registry_path: str | Path = DEFAULT_REGISTRY_PATH,
) -> dict[str, Any]:
    path = _snapshot_path(baseline_name)
    if not path.exists():
        raise TestDataSnapshotError(f"Snapshot не найден: {path}")

    snapshot_payload = json.loads(path.read_text(encoding="utf-8"))
    tables_payload = snapshot_payload.get("tables")
    if not isinstance(tables_payload, dict):
        raise TestDataSnapshotError("Snapshot повреждён: отсутствует раздел tables.")

    reset_report = await execute_test_data_reset(
        session_factory=session_factory,
        dry_run=False,
        registry_path=registry_path,
        force=True,
    )

    async with session_factory() as session:
        for table_name, model in SNAPSHOT_TABLES:
            rows = tables_payload.get(table_name) or []
            if not rows:
                continue

            restored_rows = []
            for row in rows:
                restored_row = {
                    column.name: _deserialize_value(column, row.get(column.name))
                    for column in model.__table__.columns
                    if column.name in row
                }
                restored_rows.append(restored_row)

            await session.execute(insert(model).values(restored_rows))

        await session.commit()

    return {
        "path": str(path),
        "reset_deleted_counts": reset_report["deleted_counts"],
        "restored_counts": {
            table_name: len(tables_payload.get(table_name) or []) for table_name, _ in SNAPSHOT_TABLES
        },
    }
