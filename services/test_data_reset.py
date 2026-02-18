from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import uuid

import yaml
from sqlalchemy import and_, delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database import (
    Appointment,
    BotHealthCheck,
    CalendarSyncState,
    Client,
    GoogleOAuth,
    MessageLog,
    OAuthState,
    Specialist,
    SpecialistAuthTelegram,
    SpecialistCalendarSettings,
    SpecialistProfile,
    SpecialistStatus,
    TelegramBot,
    WeeklyAvailability,
)

DEFAULT_REGISTRY_PATH = Path("config/test_accounts.yaml")
ALLOWED_SPECIALIST_STATUSES = {SpecialistStatus.onboarding, SpecialistStatus.active}
DEFAULT_MAX_CLIENTS = 30


class TestDataResetError(RuntimeError):
    pass


@dataclass(slots=True)
class RegistryAccount:
    name: str
    role: str
    tg_user_id: int


@dataclass(slots=True)
class CleanupTarget:
    specialist_id: uuid.UUID
    owner_tg_user_id: int | None
    specialist_status: SpecialistStatus | None
    client_ids_for_deletion: list[uuid.UUID]
    delete_specialist_scope: bool
    total_clients_for_specialist: int


def _load_registry(path: Path) -> tuple[list[RegistryAccount], str | None]:
    if not path.exists():
        raise FileNotFoundError(f"Registry file not found: {path}")

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise TestDataResetError("Registry root must be mapping object.")

    accounts_raw = payload.get("accounts")
    if not isinstance(accounts_raw, list):
        raise TestDataResetError("Registry field 'accounts' must be a list.")

    accounts: list[RegistryAccount] = []
    for item in accounts_raw:
        if not isinstance(item, dict):
            raise TestDataResetError("Each account in registry must be an object.")
        name = item.get("name")
        role = item.get("role")
        tg_user_id = item.get("tg_user_id")
        if not isinstance(name, str) or not name:
            raise TestDataResetError("Registry account.name must be a non-empty string.")
        if role not in {"specialist_owner", "client"}:
            raise TestDataResetError("Registry account.role must be one of: specialist_owner, client.")
        if not isinstance(tg_user_id, int):
            raise TestDataResetError("Registry account.tg_user_id must be an integer.")
        accounts.append(RegistryAccount(name=name, role=role, tg_user_id=tg_user_id))

    notes = payload.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise TestDataResetError("Registry field 'notes' must be a string when provided.")
    return accounts, notes


def _resolve_tg_user_ids(
    *,
    registry_accounts: list[RegistryAccount],
    names: list[str] | None,
    tg_user_ids: list[int] | None,
) -> tuple[set[int], list[str]]:
    account_by_name = {account.name: account for account in registry_accounts}

    selected_names: list[str] = []
    selected_ids: set[int] = set(tg_user_ids or [])

    if names:
        for name in names:
            account = account_by_name.get(name)
            if not account:
                raise TestDataResetError(f"Unknown account name in registry: {name}")
            selected_names.append(name)
            selected_ids.add(account.tg_user_id)

    if not names and not tg_user_ids:
        selected_names = [account.name for account in registry_accounts]
        selected_ids.update(account.tg_user_id for account in registry_accounts)

    return selected_ids, selected_names


async def _count_rows(session: AsyncSession, model, where_clause) -> int:
    value = await session.scalar(select(func.count()).select_from(model).where(where_clause))
    return int(value or 0)


async def _resolve_specialists(
    session: AsyncSession,
    selected_tg_user_ids: set[int],
) -> dict[uuid.UUID, dict[str, int | SpecialistStatus | None]]:
    specialists: dict[uuid.UUID, dict[str, int | SpecialistStatus | None]] = {}
    if not selected_tg_user_ids:
        return specialists

    profile_rows = (
        (
            await session.execute(
                select(SpecialistProfile.specialist_id, SpecialistProfile.owner_tg_user_id).where(
                    SpecialistProfile.owner_tg_user_id.in_(selected_tg_user_ids)
                )
            )
        )
        .all()
    )
    for specialist_id, owner_tg_user_id in profile_rows:
        specialists[specialist_id] = {
            "owner_tg_user_id": owner_tg_user_id,
            "status": None,
        }

    auth_rows = (
        (
            await session.execute(
                select(SpecialistAuthTelegram.specialist_id, SpecialistAuthTelegram.tg_user_id).where(
                    SpecialistAuthTelegram.tg_user_id.in_(selected_tg_user_ids)
                )
            )
        )
        .all()
    )
    for specialist_id, tg_user_id in auth_rows:
        specialists.setdefault(
            specialist_id,
            {
                "owner_tg_user_id": tg_user_id,
                "status": None,
            },
        )

    if not specialists:
        return specialists

    statuses = (
        (
            await session.execute(
                select(Specialist.specialist_id, Specialist.status).where(
                    Specialist.specialist_id.in_(list(specialists.keys()))
                )
            )
        )
        .all()
    )
    for specialist_id, status in statuses:
        specialists[specialist_id]["status"] = status

    return specialists


async def _table_exists(session: AsyncSession, table_name: str) -> bool:
    dialect = session.bind.dialect.name if session.bind else ""
    if dialect == "postgresql":
        value = await session.scalar(select(func.to_regclass(f"public.{table_name}")))
        return value is not None
    if dialect == "sqlite":
        value = await session.scalar(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
            {"name": table_name},
        )
        return value is not None
    return False


async def execute_test_data_reset(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    dry_run: bool = True,
    names: list[str] | None = None,
    tg_user_ids: list[int] | None = None,
    registry_path: str | Path = DEFAULT_REGISTRY_PATH,
    force: bool = False,
    max_clients_threshold: int = DEFAULT_MAX_CLIENTS,
) -> dict:
    registry_file = Path(registry_path)
    registry_exists = registry_file.exists()

    registry_accounts: list[RegistryAccount] = []
    notes: str | None = None
    if registry_exists:
        registry_accounts, notes = _load_registry(registry_file)

    if not registry_exists and not tg_user_ids:
        raise TestDataResetError("Registry file is missing and no --tg-user-ids provided.")

    selected_tg_user_ids, selected_names = _resolve_tg_user_ids(
        registry_accounts=registry_accounts,
        names=names,
        tg_user_ids=tg_user_ids,
    )

    selected_client_tg_ids = {
        account.tg_user_id
        for account in registry_accounts
        if account.role == "client" and account.tg_user_id in selected_tg_user_ids
    }
    selected_owner_tg_ids = {
        account.tg_user_id
        for account in registry_accounts
        if account.role == "specialist_owner" and account.tg_user_id in selected_tg_user_ids
    }
    if not registry_accounts:
        selected_owner_tg_ids = set(selected_tg_user_ids)

    counts: dict[str, int] = {
        "appointment": 0,
        "weekly_availability": 0,
        "specialist_calendar_settings": 0,
        "specialist_calendar": 0,
        "calendar_sync_state": 0,
        "appointment_calendar_link": 0,
        "web_auth_session": 0,
        "web_connect_token": 0,
        "google_oauth": 0,
        "oauth_state": 0,
        "telegram_bot": 0,
        "bot_health_checks": 0,
        "message_logs": 0,
        "client": 0,
        "specialist_profile": 0,
        "specialist_auth_telegram": 0,
        "specialist": 0,
    }
    deleted_counts = {key: 0 for key in counts}
    warnings: list[str] = []

    async with session_factory() as session:
        specialists = await _resolve_specialists(session, selected_tg_user_ids)
        direct_client_rows = (
            await session.execute(
                select(Client.client_id, Client.specialist_id).where(Client.tg_user_id.in_(selected_tg_user_ids))
            )
        ).all()

        client_ids_by_specialist: dict[uuid.UUID, set[uuid.UUID]] = {}
        for client_id, specialist_id in direct_client_rows:
            client_ids_by_specialist.setdefault(specialist_id, set()).add(client_id)

        targets: list[CleanupTarget] = []
        specialist_ids = set(specialists.keys()) | set(client_ids_by_specialist.keys())
        for specialist_id in specialist_ids:
            specialist_data = specialists.get(specialist_id, {})
            owner_tg_user_id = specialist_data.get("owner_tg_user_id")
            specialist_status = specialist_data.get("status")

            delete_specialist_scope = bool(owner_tg_user_id in selected_owner_tg_ids)

            if delete_specialist_scope and specialist_status and specialist_status not in ALLOWED_SPECIALIST_STATUSES and not force:
                raise TestDataResetError(
                    f"Refusing specialist deletion for {specialist_id}: status={specialist_status.value}. Use --force."
                )

            total_clients = int(
                await session.scalar(
                    select(func.count()).select_from(Client).where(Client.specialist_id == specialist_id)
                )
                or 0
            )
            if delete_specialist_scope and total_clients > max_clients_threshold and not force:
                raise TestDataResetError(
                    f"Refusing specialist deletion for {specialist_id}: clients={total_clients} exceeds threshold={max_clients_threshold}. Use --force."
                )

            if delete_specialist_scope:
                if not force and total_clients > 0 and owner_tg_user_id not in selected_owner_tg_ids:
                    raise TestDataResetError(
                        f"Refusing mass client deletion for {specialist_id}: owner tg_user_id is not in specialist_owner registry list."
                    )
                client_ids = (
                    await session.execute(
                        select(Client.client_id).where(Client.specialist_id == specialist_id)
                    )
                ).scalars().all()
            else:
                candidate_ids = client_ids_by_specialist.get(specialist_id, set())
                if selected_client_tg_ids:
                    from_registry = (
                        await session.execute(
                            select(Client.client_id).where(
                                Client.specialist_id == specialist_id,
                                Client.tg_user_id.in_(selected_client_tg_ids),
                            )
                        )
                    ).scalars().all()
                    candidate_ids.update(from_registry)
                client_ids = list(candidate_ids)

            targets.append(
                CleanupTarget(
                    specialist_id=specialist_id,
                    owner_tg_user_id=int(owner_tg_user_id) if owner_tg_user_id is not None else None,
                    specialist_status=specialist_status,
                    client_ids_for_deletion=list(client_ids),
                    delete_specialist_scope=delete_specialist_scope,
                    total_clients_for_specialist=total_clients,
                )
            )

        if not targets:
            warnings.append("No matching specialists or clients found for selected tg_user_id values.")

        all_target_client_ids = [cid for target in targets for cid in target.client_ids_for_deletion]
        all_target_specialist_ids = [target.specialist_id for target in targets if target.delete_specialist_scope]

        counts["appointment"] = await _count_rows(
            session,
            Appointment,
            and_(
                Appointment.specialist_id.in_([target.specialist_id for target in targets]) if targets else False,
                Appointment.client_id.in_(all_target_client_ids) if all_target_client_ids else False,
            ),
        )
        counts["client"] = await _count_rows(
            session,
            Client,
            Client.client_id.in_(all_target_client_ids) if all_target_client_ids else False,
        )
        counts["message_logs"] = await _count_rows(
            session,
            MessageLog,
            or_(
                MessageLog.tg_user_id.in_(selected_tg_user_ids) if selected_tg_user_ids else False,
                MessageLog.specialist_id.in_(all_target_specialist_ids) if all_target_specialist_ids else False,
            ),
        )

        for target in targets:
            if not target.delete_specialist_scope:
                continue
            sid = target.specialist_id
            counts["weekly_availability"] += await _count_rows(session, WeeklyAvailability, WeeklyAvailability.specialist_id == sid)
            counts["specialist_calendar_settings"] += await _count_rows(session, SpecialistCalendarSettings, SpecialistCalendarSettings.specialist_id == sid)
            counts["google_oauth"] += await _count_rows(session, GoogleOAuth, GoogleOAuth.specialist_id == sid)
            counts["oauth_state"] += await _count_rows(session, OAuthState, OAuthState.specialist_id == sid)
            counts["telegram_bot"] += await _count_rows(session, TelegramBot, TelegramBot.specialist_id == sid)
            counts["bot_health_checks"] += await _count_rows(session, BotHealthCheck, BotHealthCheck.specialist_id == sid)
            counts["specialist_profile"] += await _count_rows(session, SpecialistProfile, SpecialistProfile.specialist_id == sid)
            counts["specialist_auth_telegram"] += await _count_rows(session, SpecialistAuthTelegram, SpecialistAuthTelegram.specialist_id == sid)
            counts["specialist"] += await _count_rows(session, Specialist, Specialist.specialist_id == sid)

        has_specialist_calendar = await _table_exists(session, "specialist_calendar")
        has_appointment_calendar_link = await _table_exists(session, "appointment_calendar_link")
        has_web_auth_session = await _table_exists(session, "web_auth_session")
        has_web_connect_token = await _table_exists(session, "web_connect_token")

        if has_specialist_calendar and all_target_specialist_ids:
            for sid in all_target_specialist_ids:
                value = await session.scalar(
                    text("SELECT COUNT(*) FROM specialist_calendar WHERE specialist_id = :sid"),
                    {"sid": str(sid)},
                )
                counts["specialist_calendar"] += int(value or 0)

        if has_appointment_calendar_link and all_target_specialist_ids:
            for sid in all_target_specialist_ids:
                value = await session.scalar(
                    text("SELECT COUNT(*) FROM appointment_calendar_link WHERE specialist_id = :sid"),
                    {"sid": str(sid)},
                )
                counts["appointment_calendar_link"] += int(value or 0)

        if has_web_auth_session and all_target_specialist_ids:
            for sid in all_target_specialist_ids:
                value = await session.scalar(
                    text("SELECT COUNT(*) FROM web_auth_session WHERE specialist_id = :sid"),
                    {"sid": str(sid)},
                )
                counts["web_auth_session"] += int(value or 0)

        if has_web_connect_token and all_target_specialist_ids:
            for sid in all_target_specialist_ids:
                value = await session.scalar(
                    text("SELECT COUNT(*) FROM web_connect_token WHERE specialist_id = :sid"),
                    {"sid": str(sid)},
                )
                counts["web_connect_token"] += int(value or 0)

        for target in targets:
            if not target.delete_specialist_scope:
                continue
            counts["calendar_sync_state"] += await _count_rows(
                session,
                CalendarSyncState,
                CalendarSyncState.specialist_id == target.specialist_id,
            )

        target_report = [
            {
                "specialist_id": str(target.specialist_id),
                "owner_tg_user_id": target.owner_tg_user_id,
                "status": target.specialist_status.value if target.specialist_status else None,
                "delete_specialist_scope": target.delete_specialist_scope,
                "total_clients_for_specialist": target.total_clients_for_specialist,
                "target_client_ids": [str(v) for v in target.client_ids_for_deletion],
            }
            for target in targets
        ]

        if not dry_run:
            if all_target_client_ids:
                deleted_counts["appointment"] = int(
                    (
                        await session.execute(
                            delete(Appointment).where(Appointment.client_id.in_(all_target_client_ids))
                        )
                    ).rowcount
                    or 0
                )

            if all_target_specialist_ids:
                for key, model in (
                    ("weekly_availability", WeeklyAvailability),
                    ("specialist_calendar_settings", SpecialistCalendarSettings),
                    ("google_oauth", GoogleOAuth),
                    ("oauth_state", OAuthState),
                    ("telegram_bot", TelegramBot),
                    ("bot_health_checks", BotHealthCheck),
                    ("specialist_profile", SpecialistProfile),
                    ("specialist_auth_telegram", SpecialistAuthTelegram),
                    ("calendar_sync_state", CalendarSyncState),
                ):
                    deleted_counts[key] = int(
                        (
                            await session.execute(
                                delete(model).where(model.specialist_id.in_(all_target_specialist_ids))
                            )
                        ).rowcount
                        or 0
                    )

                if has_specialist_calendar:
                    for sid in all_target_specialist_ids:
                        deleted_counts["specialist_calendar"] += int(
                            (
                                await session.execute(
                                    text("DELETE FROM specialist_calendar WHERE specialist_id = :sid"),
                                    {"sid": str(sid)},
                                )
                            ).rowcount
                            or 0
                        )

                if has_web_auth_session:
                    for sid in all_target_specialist_ids:
                        deleted_counts["web_auth_session"] += int(
                            (
                                await session.execute(
                                    text("DELETE FROM web_auth_session WHERE specialist_id = :sid"),
                                    {"sid": str(sid)},
                                )
                            ).rowcount
                            or 0
                        )

                if has_web_connect_token:
                    for sid in all_target_specialist_ids:
                        deleted_counts["web_connect_token"] += int(
                            (
                                await session.execute(
                                    text("DELETE FROM web_connect_token WHERE specialist_id = :sid"),
                                    {"sid": str(sid)},
                                )
                            ).rowcount
                            or 0
                        )

                if has_appointment_calendar_link:
                    for sid in all_target_specialist_ids:
                        deleted_counts["appointment_calendar_link"] += int(
                            (
                                await session.execute(
                                    text("DELETE FROM appointment_calendar_link WHERE specialist_id = :sid"),
                                    {"sid": str(sid)},
                                )
                            ).rowcount
                            or 0
                        )

            if selected_tg_user_ids or all_target_specialist_ids:
                deleted_counts["message_logs"] = int(
                    (
                        await session.execute(
                            delete(MessageLog).where(
                                or_(
                                    MessageLog.tg_user_id.in_(selected_tg_user_ids) if selected_tg_user_ids else False,
                                    MessageLog.specialist_id.in_(all_target_specialist_ids) if all_target_specialist_ids else False,
                                )
                            )
                        )
                    ).rowcount
                    or 0
                )

            if all_target_client_ids:
                deleted_counts["client"] = int(
                    (
                        await session.execute(delete(Client).where(Client.client_id.in_(all_target_client_ids)))
                    ).rowcount
                    or 0
                )

            if all_target_specialist_ids:
                deleted_counts["specialist"] = int(
                    (
                        await session.execute(
                            delete(Specialist).where(Specialist.specialist_id.in_(all_target_specialist_ids))
                        )
                    ).rowcount
                    or 0
                )

            await session.commit()
    return {
        "ok": True,
        "dry_run": dry_run,
        "force": force,
        "max_clients_threshold": max_clients_threshold,
        "registry_path": str(registry_file),
        "registry_exists": registry_exists,
        "registry_notes": notes,
        "selected_names": selected_names,
        "selected_tg_user_ids": sorted(selected_tg_user_ids),
        "specialist_ids": sorted({item["specialist_id"] for item in target_report}),
        "client_ids": sorted({client_id for item in target_report for client_id in item["target_client_ids"]}),
        "targets": target_report,
        "counts": counts,
        "deleted_counts": deleted_counts,
        "warnings": warnings,
    }


def format_report(report: dict) -> str:
    mode = "DRY-RUN" if report.get("dry_run", True) else "APPLY"
    lines = [f"Result: {'OK' if report.get('ok') else 'FAIL'}", f"Mode: {mode}"]
    lines.append(f"Registry file: {report['registry_path']} (exists={report['registry_exists']})")
    lines.append(f"Selected tg_user_id: {', '.join(map(str, report['selected_tg_user_ids'])) or 'none'}")
    lines.append(f"Target specialists: {', '.join(report.get('specialist_ids', [])) or 'none'}")
    lines.append(f"Target clients: {', '.join(report.get('client_ids', [])) or 'none'}")

    lines.append("Planned rows per table:")
    for table_name, count in report["counts"].items():
        lines.append(f"  - {table_name}: {count}")

    if not report.get("dry_run", True):
        lines.append("Deleted rows per table:")
        for table_name, count in report["deleted_counts"].items():
            lines.append(f"  - {table_name}: {count}")

    for target in report.get("targets", []):
        lines.append(
            "Target "
            f"specialist_id={target['specialist_id']} "
            f"owner_tg_user_id={target['owner_tg_user_id']} "
            f"delete_specialist_scope={target['delete_specialist_scope']} "
            f"clients={len(target['target_client_ids'])}"
        )

    warnings = report.get("warnings") or []
    if warnings:
        lines.append("Warnings:")
        for warning in warnings:
            lines.append(f"  - {warning}")

    return "\n".join(lines)
