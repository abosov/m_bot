from __future__ import annotations


def normalize_telegram_username(username: str | None) -> str | None:
    normalized = (username or "").strip().lstrip("@")
    return normalized or None


def format_client_display(*, display_name: str | None, tg_username: str | None) -> str:
    base_name = (display_name or "").strip() or "Клиент"
    normalized_username = normalize_telegram_username(tg_username)
    if normalized_username:
        return f"{base_name} (@{normalized_username})"
    return base_name
