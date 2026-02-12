from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERSION_PATH = PROJECT_ROOT / 'VERSION'
BUILD_DATE_UTC = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _read_build_number() -> int | None:
    try:
        return int(VERSION_PATH.read_text(encoding='utf-8').strip())
    except (FileNotFoundError, ValueError):
        return None


def _read_git_commit_short() -> str:
    try:
        return (
            subprocess.check_output(
                ['git', '-C', str(PROJECT_ROOT), 'rev-parse', '--short', 'HEAD'],
                text=True,
            )
            .strip()
            or 'unknown'
        )
    except Exception:
        return 'unknown'


def get_build_info() -> dict[str, str | int | None]:
    build_number = _read_build_number()
    commit_sha = _read_git_commit_short()
    version = f"{build_number or 'na'}-{commit_sha}-{BUILD_DATE_UTC}"
    return {
        'version': version,
        'build_number': build_number,
        'commit_sha': commit_sha,
        'build_date_utc': BUILD_DATE_UTC,
    }
