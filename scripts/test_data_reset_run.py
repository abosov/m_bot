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
EXAMPLE_REGISTRY_PATH = Path('config/test_accounts.example.yaml')


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(description='Запуск безопасного сброса тестовых данных одной командой.')
    parser.add_argument('--apply', action='store_true', help='Реально применить удаление.')
    parser.add_argument('--yes', action='store_true', help='Подтвердить apply без интерактивного вопроса.')
    parser.add_argument(
        '--i-know-what-i-am-doing',
        action='store_true',
        help='Второй safety-флаг, обязателен вместе с --apply.',
    )
    return parser.parse_known_args(argv)


def load_env_file(path: Path, env: dict[str, str]) -> None:
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

        env.setdefault(key, value)


def has_option(argv: list[str], option: str) -> bool:
    return option in argv or any(arg.startswith(f'{option}=') for arg in argv)


def resolve_registry_path(repo_root: Path) -> Path:
    default_registry_path = repo_root / 'config/test_accounts.yaml'

    if SYSTEM_REGISTRY_PATH.exists():
        return SYSTEM_REGISTRY_PATH

    if default_registry_path.exists():
        return default_registry_path

    raise FileNotFoundError(
        f'Registry not found. Expected either {SYSTEM_REGISTRY_PATH} or {default_registry_path}. '
        f'Create one from {repo_root / EXAMPLE_REGISTRY_PATH} or pass --registry PATH.'
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


def build_cli_command(python_executable: Path, script_path: Path, passthrough_args: list[str], registry_path: Path) -> list[str]:
    command = [str(python_executable), str(script_path), *passthrough_args]
    if not has_option(passthrough_args, '--registry'):
        command.extend(['--registry', str(registry_path)])
    if not has_option(passthrough_args, '--format'):
        command.extend(['--format', 'text'])
    return command


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    python_executable = repo_root / '.venv/bin/python3'
    script_path = repo_root / 'scripts/test_data_reset.py'
    args, passthrough_args = parse_args(sys.argv[1:])

    if not python_executable.exists():
        print(f'ERROR: venv python is missing: {python_executable}')
        return 2
    if not script_path.exists():
        print(f'ERROR: reset script is missing: {script_path}')
        return 2

    try:
        ensure_apply_guards(args)
        registry_path = resolve_registry_path(repo_root)
    except Exception as exc:
        print(f'ERROR: {exc}')
        return 2

    child_env = os.environ.copy()
    load_env_file(SYSTEM_ENV_FILE, child_env)

    if child_env.get('DATABASE_URL') and not child_env.get('DB_URL'):
        child_env['DB_URL'] = child_env['DATABASE_URL']

    if not child_env.get('DB_URL'):
        print(f'ERROR: DB_URL is not set. Ensure {SYSTEM_ENV_FILE} contains DB_URL or export it manually.')
        return 2

    command = build_cli_command(python_executable, script_path, passthrough_args, registry_path)
    print(f"Running: {' '.join(shlex.quote(item) for item in command)}")
    proc = subprocess.run(command, env=child_env)
    return int(proc.returncode)


if __name__ == '__main__':
    raise SystemExit(main())
