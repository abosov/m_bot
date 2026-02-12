#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

SYSTEM_ENV_FILE = Path('/etc/zumbot/backend.env')
SYSTEM_REGISTRY_PATH = Path('/etc/zumbot/test_accounts.yaml')
DEFAULT_REGISTRY_PATH = Path('config/test_accounts.yaml')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Запуск безопасного сброса тестовых данных одной командой.')
    parser.add_argument('--registry', help='Явный путь к registry-файлу (перекрывает авто-выбор).')
    parser.add_argument('--apply', action='store_true', help='Реально применить удаление.')
    parser.add_argument('--yes', action='store_true', help='Подтвердить apply без интерактивного вопроса.')
    parser.add_argument(
        '--i-know-what-i-am-doing',
        action='store_true',
        help='Второй safety-флаг, обязателен вместе с --apply.',
    )
    parser.add_argument('--names', nargs='+', help='Имена аккаунтов из реестра.')
    parser.add_argument('--tg-user-ids', nargs='+', type=int, help='Список tg_user_id без реестра.')
    parser.add_argument('--force', action='store_true', help='Отключить safety guards в Python CLI.')
    parser.add_argument('--max-clients-threshold', type=int, help='Порог клиентов для safety guard.')
    parser.add_argument('--format', choices=['json', 'text'], help='Формат отчёта.')
    return parser.parse_args()


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[len('export ') :].strip()
        if '=' not in line:
            continue

        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        else:
            value = shlex.split(value)[0] if value else ''

        os.environ.setdefault(key, value)


def resolve_registry_path(explicit_registry: str | None) -> Path:
    if explicit_registry:
        resolved = Path(explicit_registry)
        if not resolved.exists():
            raise FileNotFoundError(f'Registry file not found: {resolved}')
        return resolved

    if SYSTEM_REGISTRY_PATH.exists():
        return SYSTEM_REGISTRY_PATH

    if DEFAULT_REGISTRY_PATH.exists():
        return DEFAULT_REGISTRY_PATH

    raise FileNotFoundError(
        f'Registry not found. Expected either {SYSTEM_REGISTRY_PATH} or {DEFAULT_REGISTRY_PATH}. '
        'Create one of them or pass --registry PATH.'
    )


def ensure_apply_guards(args: argparse.Namespace) -> None:
    if not args.apply:
        return

    if not args.i_know_what_i_am_doing:
        raise RuntimeError('Refusing --apply without --i-know-what-i-am-doing safety flag.')

    if args.yes:
        return

    if not sys.stdin.isatty():
        raise RuntimeError('Refusing --apply in non-interactive mode without --yes.')

    answer = input("Type 'yes' to continue applying deletions: ").strip().lower()
    if answer != 'yes':
        raise RuntimeError('Apply cancelled by user.')


def build_cli_command(args: argparse.Namespace, registry_path: Path) -> list[str]:
    command = [sys.executable, 'scripts/test_data_reset.py', '--registry', str(registry_path)]

    if args.apply:
        command.append('--apply')

    if args.names:
        command.extend(['--names', *args.names])
    if args.tg_user_ids:
        command.extend(['--tg-user-ids', *[str(value) for value in args.tg_user_ids]])
    if args.force:
        command.append('--force')
    if args.max_clients_threshold is not None:
        command.extend(['--max-clients-threshold', str(args.max_clients_threshold)])
    if args.format:
        command.extend(['--format', args.format])

    return command


def main() -> int:
    args = parse_args()

    try:
        load_env_file(SYSTEM_ENV_FILE)
        ensure_apply_guards(args)
        registry_path = resolve_registry_path(args.registry)
    except Exception as exc:
        print(f'ERROR: {exc}')
        return 2

    if os.getenv('DATABASE_URL') and not os.getenv('DB_URL'):
        os.environ['DB_URL'] = os.environ['DATABASE_URL']

    if not os.getenv('DB_URL'):
        print(f'ERROR: DB_URL is not set. Ensure {SYSTEM_ENV_FILE} contains DB_URL or export it manually.')
        return 2

    command = build_cli_command(args, registry_path)
    print(f"Running: {' '.join(shlex.quote(item) for item in command)}")
    proc = subprocess.run(command, env=os.environ.copy())
    return int(proc.returncode)


if __name__ == '__main__':
    raise SystemExit(main())
