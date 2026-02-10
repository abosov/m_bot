#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
from pathlib import Path

if __package__ in {None, ""}:
    bootstrap_path = Path(__file__).with_name("_bootstrap.py")
    bootstrap_spec = importlib.util.spec_from_file_location("scripts._bootstrap", bootstrap_path)
    if bootstrap_spec is None or bootstrap_spec.loader is None:
        raise RuntimeError(f"Unable to load bootstrap module from {bootstrap_path}")
    bootstrap_module = importlib.util.module_from_spec(bootstrap_spec)
    bootstrap_spec.loader.exec_module(bootstrap_module)
    add_project_root_to_syspath = bootstrap_module.add_project_root_to_syspath
else:
    from ._bootstrap import add_project_root_to_syspath

add_project_root_to_syspath()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Безопасный сброс тестовых данных smoke-аккаунтов.")
    parser.add_argument("--list", action="store_true", help="Показать аккаунты из реестра и выйти.")
    parser.add_argument("--dry-run", action="store_true", help="Явный dry-run режим (по умолчанию).")
    parser.add_argument("--apply", action="store_true", help="Применить удаление.")
    parser.add_argument("--force", action="store_true", help="Отключить safety guard по статусу/порогу клиентов.")
    parser.add_argument("--names", nargs="+", help="Имена аккаунтов из реестра.")
    parser.add_argument("--tg-user-ids", nargs="+", type=int, help="Явный список tg_user_id.")
    parser.add_argument(
        "--registry-path",
        default="config/test_accounts.yaml",
        help="Путь к локальному реестру тестовых аккаунтов.",
    )
    parser.add_argument(
        "--max-clients-threshold",
        type=int,
        default=30,
        help="Порог количества клиентов на специалиста для safety guard.",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    dry_run = not args.apply

    if args.list:
        registry_file = Path(args.registry_path)
        if not registry_file.exists():
            raise RuntimeError(f"Файл реестра не найден: {registry_file}")
        payload = json.loads(registry_file.read_text(encoding="utf-8"))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    from database import async_session_factory
    from services.test_data_reset import execute_test_data_reset, format_report

    report = await execute_test_data_reset(
        session_factory=async_session_factory,
        dry_run=dry_run,
        names=args.names,
        tg_user_ids=args.tg_user_ids,
        registry_path=args.registry_path,
        force=args.force,
        max_clients_threshold=args.max_clients_threshold,
    )
    print(format_report(report))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return asyncio.run(_run(args))
    except Exception as exc:
        print(f"Ошибка: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
