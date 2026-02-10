#!/usr/bin/env python3

import argparse
import asyncio
import importlib.util
import os
import sys
import uuid
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


def _print_venv_hint() -> None:
    venv = os.getenv("VIRTUAL_ENV")
    if venv:
        return

    repo_venv = Path(__file__).resolve().parents[1] / ".venv"
    if repo_venv.exists():
        sys.stderr.write(
            "Hint: virtualenv is not activated. "
            f"If dependencies are missing, run: source {repo_venv}/bin/activate\n"
        )


def parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid UUID: {value}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export Zumbot logs to JSONL or CSV.",
        epilog=(
            "Example:\n"
            "  python scripts/export_logs.py --source message_logs "
            "--since 2026-01-01T00:00:00Z --limit 500 --redact "
            "--out /tmp/message_logs.jsonl"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source",
        choices=["message_logs", "service_heartbeats", "bot_health_checks"],
        default="message_logs",
        help="Log source table to export.",
    )
    parser.add_argument("--since", help="Start time (ISO8601, UTC).")
    parser.add_argument("--until", help="End time (ISO8601, UTC).")
    parser.add_argument("--limit", type=int, help="Max number of records.")
    parser.add_argument("--bot-id", type=int, help="Filter by bot_id.")
    parser.add_argument("--specialist-id", type=parse_uuid, help="Filter by specialist_id.")
    parser.add_argument("--tg-user-id", type=int, help="Filter by tg_user_id.")
    parser.add_argument("--direction", choices=["IN", "OUT"], help="IN or OUT.")
    parser.add_argument(
        "--is-error",
        action="store_true",
        help="Only records where is_error is true.",
    )
    parser.add_argument(
        "--format",
        choices=["jsonl", "csv"],
        default="jsonl",
        help="Output format.",
    )
    parser.add_argument("--out", help="Output file path. Defaults to stdout.")
    parser.add_argument(
        "--redact",
        action="store_true",
        help="Redact emails/phones and drop suspicious token-like strings.",
    )
    return parser


async def run_export(
    args: argparse.Namespace,
    log_direction_cls,
    collect_logs,
    parse_iso_datetime,
    render_jsonl,
    render_message_logs_csv,
) -> int:
    since = parse_iso_datetime(args.since) if args.since else None
    until = parse_iso_datetime(args.until) if args.until else None
    direction = log_direction_cls(args.direction) if args.direction else None
    is_error = True if args.is_error else None

    records = await collect_logs(
        source=args.source,
        since=since,
        until=until,
        limit=args.limit,
        bot_id=args.bot_id,
        specialist_id=args.specialist_id,
        tg_user_id=args.tg_user_id,
        direction=direction,
        is_error=is_error,
        redact=args.redact,
    )

    if args.format == "csv":
        if args.source != "message_logs":
            raise ValueError("CSV format is supported only for message_logs.")
        output = render_message_logs_csv(records)
    else:
        output = render_jsonl(records)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as file:
            file.write(output)
    else:
        sys.stdout.write(output)
    return 0


def main() -> int:
    _print_venv_hint()
    parser = build_parser()
    args = parser.parse_args()

    from database import LogDirection
    from services.log_exporter import (
        collect_logs,
        parse_iso_datetime,
        render_jsonl,
        render_message_logs_csv,
    )

    return asyncio.run(
        run_export(
            args=args,
            log_direction_cls=LogDirection,
            collect_logs=collect_logs,
            parse_iso_datetime=parse_iso_datetime,
            render_jsonl=render_jsonl,
            render_message_logs_csv=render_message_logs_csv,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
