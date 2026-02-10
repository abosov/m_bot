#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import requests


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _iso_utc_now_minus(minutes: int) -> str:
    ts = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return ts.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _append_result(results: list[CheckResult], name: str, ok: bool, detail: str) -> None:
    mark = "✅" if ok else "❌"
    print(f"{mark} {name}: {detail}")
    results.append(CheckResult(name=name, ok=ok, detail=detail))


def _safe_json(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Некорректный JSON в ответе: {response.text[:200]}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Ожидался JSON-объект, получено: {type(payload).__name__}")
    return payload


def _request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> tuple[int, dict[str, Any]]:
    response = session.request(method, url, headers=headers, params=params, timeout=timeout)
    return response.status_code, _safe_json(response)


def run_smoke(args: argparse.Namespace) -> int:
    base_url = (args.base_url or os.getenv("BASE_URL", "")).strip().rstrip("/")
    admin_api_key = (args.admin_api_key or os.getenv("ADMIN_API_KEY", "")).strip()

    if not base_url:
        sys.stderr.write("BASE_URL не задан. Передайте --base-url или переменную окружения BASE_URL.\n")
        return 2

    if not admin_api_key:
        sys.stderr.write(
            "ADMIN_API_KEY не задан. Передайте --admin-api-key или переменную окружения ADMIN_API_KEY.\n"
        )
        return 2

    results: list[CheckResult] = []
    session = requests.Session()
    admin_headers = {"X-API-Key": admin_api_key}
    since_value = _iso_utc_now_minus(args.since_minutes) if args.since_minutes else None

    try:
        health_code, health_json = _request_json(session, "GET", f"{base_url}/healthz")
        health_ok = health_code == 200 and health_json.get("status") == "ok"
        _append_result(results, "GET /healthz", health_ok, f"code={health_code}, body={health_json}")
    except Exception as exc:
        _append_result(results, "GET /healthz", False, str(exc))

    try:
        ready_code, ready_json = _request_json(session, "GET", f"{base_url}/readyz")
        if ready_code == 404:
            _append_result(results, "GET /readyz", True, "эндпоинт отключён (404), это допустимо")
        else:
            ready_ok = ready_code == 200 and ready_json.get("status") == "ready"
            _append_result(results, "GET /readyz", ready_ok, f"code={ready_code}, body={ready_json}")
    except Exception as exc:
        _append_result(results, "GET /readyz", False, str(exc))

    admin_params: dict[str, Any] = {"limit": 5}
    if since_value:
        admin_params["since"] = since_value

    for endpoint in ("heartbeats", "logs", "bot-health-checks"):
        name = f"GET /admin/{endpoint}"
        try:
            code, payload = _request_json(
                session,
                "GET",
                f"{base_url}/admin/{endpoint}",
                headers=admin_headers,
                params=admin_params,
            )
            items = payload.get("items")
            count = len(items) if isinstance(items, list) else -1
            ok = code == 200 and isinstance(items, list)
            if ok and args.since_minutes:
                ok = count > 0
                detail = (
                    f"code={code}, записей={count}, since={since_value}"
                    if count > 0
                    else f"code={code}, за последние {args.since_minutes} мин записи не найдены"
                )
            else:
                detail = f"code={code}, записей={count}"
            _append_result(results, name, ok, detail)
        except Exception as exc:
            _append_result(results, name, False, str(exc))

    failed = [result for result in results if not result.ok]
    if failed:
        print(f"\nИтог: smoke check не пройден ({len(failed)} ошибок).")
        return 1

    print("\nИтог: smoke check пройден успешно.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Лёгкий smoke-runner для health/admin endpoints после деплоя.",
    )
    parser.add_argument("--base-url", help="Базовый URL сервиса, например https://example.com")
    parser.add_argument("--admin-api-key", help="Ключ X-API-Key для /admin/*")
    parser.add_argument(
        "--since-minutes",
        type=int,
        default=None,
        help=(
            "Проверять, что в /admin/* есть записи не старше N минут. "
            "Если указано, отсутствие свежих записей будет считаться ошибкой."
        ),
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return run_smoke(args)


if __name__ == "__main__":
    raise SystemExit(main())
