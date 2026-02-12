import types

import pytest

import handlers.master_onboarding as onboarding


class DummyMessage:
    def __init__(self):
        self.from_user = types.SimpleNamespace(id=42, username="spec", first_name="S", last_name="P")
        self.bot = object()
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


class _Session:
    async def execute(self, stmt):
        text = str(stmt)
        if "FROM specialist_auth_telegram" in text:
            return types.SimpleNamespace(scalar_one_or_none=lambda: types.SimpleNamespace(specialist_id="sp-1"))
        if "FROM telegram_bot" in text:
            bot = types.SimpleNamespace(bot_user_id=123, bot_username="mybot", bot_token_encrypted="enc")
            return types.SimpleNamespace(scalars=lambda: types.SimpleNamespace(first=lambda: bot))
        return types.SimpleNamespace(scalar_one_or_none=lambda: None)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_master_guard_blocks_status_when_full_onboarding_not_completed(monkeypatch):
    message = DummyMessage()
    called = {"status_check": False}

    async def fake_log(*args, **kwargs):
        return None

    async def fake_get_specialist(_tg_user_id):
        return types.SimpleNamespace(onboarding_master_completed_at="2026-02-12T00:00:00Z", onboarding_personal_completed_at=None)

    async def fake_check_bot_status(*args, **kwargs):
        called["status_check"] = True
        return "OK", types.SimpleNamespace(username="mybot", id=123)

    monkeypatch.setattr(onboarding, "async_session_factory", lambda: _Session())
    monkeypatch.setattr(onboarding, "log_outbound_message", fake_log)
    monkeypatch.setattr(onboarding, "get_specialist_by_tg_user_id", fake_get_specialist)
    monkeypatch.setattr(onboarding, "_check_bot_status", fake_check_bot_status)
    monkeypatch.setattr(onboarding, "decrypt_token", lambda _v: "token")

    await onboarding.cmd_status(message)

    assert called["status_check"] is False
    assert any("Онбординг ещё не завершён" in msg[0] for msg in message.answers)
