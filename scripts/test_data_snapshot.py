#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import importlib.util
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
    parser = argparse.ArgumentParser(description="Сохранение/восстановление baseline тестовых данных специалиста.")
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument("--save", metavar="BASELINE_NAME", help="Сохранить snapshot в baseline.")
    action_group.add_argument("--restore", metavar="BASELINE_NAME", help="Восстановить данные из baseline.")
    parser.add_argument(
        "--registry-path",
        default="config/test_accounts.yaml",
        help="Путь к локальному реестру тестовых аккаунтов.",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    from database import async_session_factory
    from services.test_data_snapshot import create_test_data_snapshot, restore_test_data_snapshot

    if args.save:
        report = await create_test_data_snapshot(
            session_factory=async_session_factory,
            baseline_name=args.save,
            registry_path=args.registry_path,
        )
        print(f"Snapshot сохранён: {report['path']}")
        print(f"Специалистов: {report['specialist_count']}")
        for table_name, count in report["table_counts"].items():
            print(f"  - {table_name}: {count}")
        return 0

    report = await restore_test_data_snapshot(
        session_factory=async_session_factory,
        baseline_name=args.restore,
        registry_path=args.registry_path,
    )
    print(f"Snapshot восстановлен: {report['path']}")
    print("Удалено reset-процедурой:")
    for table_name, count in report["reset_deleted_counts"].items():
        print(f"  - {table_name}: {count}")
    print("Восстановлено строк:")
    for table_name, count in report["restored_counts"].items():
        print(f"  - {table_name}: {count}")
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
