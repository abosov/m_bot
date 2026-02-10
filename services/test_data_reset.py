from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import uuid

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
    client_ids_for_deletion: list[uuid.UUID]
    delete_all_clients_for_specialist: bool
    total_clients_for_specialist: int
    specialist_status: SpecialistStatus | None


def _load_registry(path: Path) -> tuple[list[RegistryAccount], str | None]:
    if not path.exists():
        raise FileNotFoundError(f"Registry file not found: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TestDataResetError(
            f"Unable to parse registry file {path}. Use JSON-compatible YAML format."
        ) from exc

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
        if not isinstance(role, str) or not role:
            raise TestDataResetError("Registry account.role must be a non-empty string.")
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
) -> tuple[set[int], list[str], list[str]]:
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

    selected_client_ids = [
        account.name
        for account in registry_accounts
        if account.tg_user_id in selected_ids and account.role == "client"
    ]
    selected_owner_ids = [
        account.name
        for account in registry_accounts
        if account.tg_user_id in selected_ids and account.role == "specialist_owner"
    ]

    return selected_ids, selected_names, selected_client_ids + selected_owner_ids


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

    if not registry_exists and dry_run and not tg_user_ids:
        raise TestDataResetError(
            "Registry file is missing and no --tg-user-ids provided. "
            "For dry-run pass explicit tg ids or create config/test_accounts.yaml."
        )

    if not registry_exists and not dry_run and not tg_user_ids:
        raise TestDataResetError(
            "Refusing --apply without registry file or explicit --tg-user-ids."
        )

    selected_tg_user_ids, selected_names, selected_registry_names = _resolve_tg_user_ids(
        registry_accounts=registry_accounts,
        names=names,
        tg_user_ids=tg_user_ids,
    )

    counts: dict[str, int] = {
        "appointment": 0,
        "client": 0,
        "weekly_availability": 0,
        "specialist_calendar_settings": 0,
        "google_oauth": 0,
        "oauth_state": 0,
        "telegram_bot": 0,
        "specialist_profile": 0,
        "specialist_auth_telegram": 0,
        "specialist": 0,
        "message_logs": 0,
        "bot_health_checks": 0,
    }

    deleted_counts = {key: 0 for key in counts}
    warnings: list[str] = []
    specialist_reports: list[dict] = []

    async with session_factory() as session:
        specialists = await _resolve_specialists(session, selected_tg_user_ids)
        targets: list[CleanupTarget] = []

        selected_registry_clients = {
            account.tg_user_id
            for account in registry_accounts
            if account.role == "client" and account.tg_user_id in selected_tg_user_ids
        }

        for specialist_id, specialist_data in specialists.items():
            owner_tg_user_id = specialist_data.get("owner_tg_user_id")
            specialist_status = specialist_data.get("status")
            delete_all_clients = bool(owner_tg_user_id in selected_tg_user_ids)

            if specialist_status and specialist_status not in ALLOWED_SPECIALIST_STATUSES and not force:
                raise TestDataResetError(
                    "Refusing cleanup for specialist "
                    f"{specialist_id}: status={specialist_status.value}. Use --force to override."
                )

            client_filter = Client.specialist_id == specialist_id
            if not delete_all_clients:
                if selected_registry_clients:
                    client_filter = and_(
                        Client.specialist_id == specialist_id,
                        Client.tg_user_id.in_(selected_registry_clients),
                    )
                else:
                    client_filter = and_(Client.specialist_id == specialist_id, False)

            client_rows = (
                (await session.execute(select(Client.client_id).where(client_filter))).scalars().all()
            )
            total_clients = int(
                await session.scalar(
                    select(func.count()).select_from(Client).where(Client.specialist_id == specialist_id)
                )
                or 0
            )

            if total_clients > max_clients_threshold and not force:
                raise TestDataResetError(
                    "Refusing cleanup for specialist "
                    f"{specialist_id}: total clients {total_clients} > threshold {max_clients_threshold}. "
                    "Use --force to override."
                )

            targets.append(
                CleanupTarget(
                    specialist_id=specialist_id,
                    owner_tg_user_id=int(owner_tg_user_id) if owner_tg_user_id is not None else None,
                    client_ids_for_deletion=list(client_rows),
                    delete_all_clients_for_specialist=delete_all_clients,
                    total_clients_for_specialist=total_clients,
                    specialist_status=specialist_status,
                )
            )

        for target in targets:
            specialist_id = target.specialist_id

            appointment_clause = and_(
                Appointment.specialist_id == specialist_id,
                Appointment.client_id.in_(target.client_ids_for_deletion) if target.client_ids_for_deletion else False,
            )
            client_clause = and_(
                Client.specialist_id == specialist_id,
                Client.client_id.in_(target.client_ids_for_deletion) if target.client_ids_for_deletion else False,
            )

            counts["appointment"] += await _count_rows(session, Appointment, appointment_clause)
            counts["client"] += await _count_rows(session, Client, client_clause)
            counts["weekly_availability"] += await _count_rows(
                session,
                WeeklyAvailability,
                WeeklyAvailability.specialist_id == specialist_id,
            )
            counts["specialist_calendar_settings"] += await _count_rows(
                session,
                SpecialistCalendarSettings,
                SpecialistCalendarSettings.specialist_id == specialist_id,
            )
            counts["google_oauth"] += await _count_rows(
                session,
                GoogleOAuth,
                GoogleOAuth.specialist_id == specialist_id,
            )
            counts["oauth_state"] += await _count_rows(
                session,
                OAuthState,
                OAuthState.specialist_id == specialist_id,
            )
            counts["telegram_bot"] += await _count_rows(
                session,
                TelegramBot,
                TelegramBot.specialist_id == specialist_id,
            )
            counts["specialist_profile"] += await _count_rows(
                session,
                SpecialistProfile,
                SpecialistProfile.specialist_id == specialist_id,
            )
            counts["specialist_auth_telegram"] += await _count_rows(
                session,
                SpecialistAuthTelegram,
                SpecialistAuthTelegram.specialist_id == specialist_id,
            )
            counts["specialist"] += await _count_rows(
                session,
                Specialist,
                Specialist.specialist_id == specialist_id,
            )

            specialist_reports.append(
                {
                    "specialist_id": str(specialist_id),
                    "owner_tg_user_id": target.owner_tg_user_id,
                    "total_clients": target.total_clients_for_specialist,
                    "deleted_clients_scope": (
                        "all" if target.delete_all_clients_for_specialist else "registry_clients_only"
                    ),
                    "target_client_count": len(target.client_ids_for_deletion),
                    "status": target.specialist_status.value if target.specialist_status else None,
                }
            )

        specialist_ids = [target.specialist_id for target in targets]
        logs_clause_parts = []
        if selected_tg_user_ids:
            logs_clause_parts.append(MessageLog.tg_user_id.in_(selected_tg_user_ids))
        if specialist_ids:
            logs_clause_parts.append(MessageLog.specialist_id.in_(specialist_ids))
        logs_clause = or_(*logs_clause_parts) if logs_clause_parts else False

        bhc_clause_parts = []
        if specialist_ids:
            bhc_clause_parts.append(BotHealthCheck.specialist_id.in_(specialist_ids))
        bhc_clause = or_(*bhc_clause_parts) if bhc_clause_parts else False

        counts["message_logs"] = await _count_rows(session, MessageLog, logs_clause)
        counts["bot_health_checks"] = await _count_rows(session, BotHealthCheck, bhc_clause)

        if not dry_run:
            for target in targets:
                specialist_id = target.specialist_id
                if target.client_ids_for_deletion:
                    appointment_delete = await session.execute(
                        delete(Appointment).where(
                            Appointment.specialist_id == specialist_id,
                            Appointment.client_id.in_(target.client_ids_for_deletion),
                        )
                    )
                    deleted_counts["appointment"] += int(appointment_delete.rowcount or 0)

                    client_delete = await session.execute(
                        delete(Client).where(
                            Client.specialist_id == specialist_id,
                            Client.client_id.in_(target.client_ids_for_deletion),
                        )
                    )
                    deleted_counts["client"] += int(client_delete.rowcount or 0)

                for key, model, clause in (
                    ("weekly_availability", WeeklyAvailability, WeeklyAvailability.specialist_id == specialist_id),
                    (
                        "specialist_calendar_settings",
                        SpecialistCalendarSettings,
                        SpecialistCalendarSettings.specialist_id == specialist_id,
                    ),
                    ("google_oauth", GoogleOAuth, GoogleOAuth.specialist_id == specialist_id),
                    ("oauth_state", OAuthState, OAuthState.specialist_id == specialist_id),
                    ("telegram_bot", TelegramBot, TelegramBot.specialist_id == specialist_id),
                    (
                        "specialist_profile",
                        SpecialistProfile,
                        SpecialistProfile.specialist_id == specialist_id,
                    ),
                    (
                        "specialist_auth_telegram",
                        SpecialistAuthTelegram,
                        SpecialistAuthTelegram.specialist_id == specialist_id,
                    ),
                    ("specialist", Specialist, Specialist.specialist_id == specialist_id),
                ):
                    delete_result = await session.execute(delete(model).where(clause))
                    deleted_counts[key] += int(delete_result.rowcount or 0)

            if logs_clause_parts:
                logs_deleted = await session.execute(delete(MessageLog).where(logs_clause))
                deleted_counts["message_logs"] = int(logs_deleted.rowcount or 0)
            if bhc_clause_parts:
                health_deleted = await session.execute(delete(BotHealthCheck).where(bhc_clause))
                deleted_counts["bot_health_checks"] = int(health_deleted.rowcount or 0)

            await session.commit()

    if not specialists:
        warnings.append("No specialists matched selected tg_user_id list.")

    return {
        "dry_run": dry_run,
        "force": force,
        "max_clients_threshold": max_clients_threshold,
        "registry_path": str(registry_file),
        "registry_exists": registry_exists,
        "registry_notes": notes,
        "selected_names": selected_names,
        "selected_registry_names": selected_registry_names,
        "selected_tg_user_ids": sorted(selected_tg_user_ids),
        "specialists": specialist_reports,
        "counts": counts,
        "deleted_counts": deleted_counts,
        "warnings": warnings,
    }


def format_report(report: dict) -> str:
    mode = "DRY-RUN" if report.get("dry_run", True) else "APPLY"
    lines = [f"Mode: {mode}"]
    lines.append(f"Registry file: {report['registry_path']} (exists={report['registry_exists']})")
    lines.append(f"Selected tg_user_id: {', '.join(map(str, report['selected_tg_user_ids'])) or 'none'}")
    lines.append(f"Matched specialists: {len(report['specialists'])}")

    lines.append("Per-table counts:")
    for table_name, count in report["counts"].items():
        lines.append(f"  - {table_name}: {count}")

    if not report.get("dry_run", True):
        lines.append("Deleted rows:")
        for table_name, count in report["deleted_counts"].items():
            lines.append(f"  - {table_name}: {count}")

    warnings = report.get("warnings") or []
    if warnings:
        lines.append("Warnings:")
        for warning in warnings:
            lines.append(f"  - {warning}")

    return "\n".join(lines)
