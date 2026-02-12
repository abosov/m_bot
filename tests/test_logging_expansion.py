import logging
import types

import pytest

import handlers.master_onboarding as onboarding
import services.google_oauth as google_oauth


class DummyState:
    def __init__(self):
        self.current = None

    async def get_state(self):
        return self.current

    async def set_state(self, state):
        self.current = state.state if hasattr(state, "state") else state


class DummyMessage:
    def __init__(self, text: str):
        self.text = text
        self.from_user = types.SimpleNamespace(id=101, username="spec", first_name="Spec", last_name="User")
        self.bot = types.SimpleNamespace(id=9001)
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


@pytest.mark.asyncio
async def test_onboarding_validation_error_logged(caplog, monkeypatch):
    message = DummyMessage("x")
    state = DummyState()
    await state.set_state(onboarding.OnboardingStates.waiting_for_public_name)

    async def fake_log_outbound(*args, **kwargs):
        return None

    monkeypatch.setattr(onboarding, "log_outbound_message", fake_log_outbound)

    with caplog.at_level(logging.INFO):
        await onboarding.process_public_name(message, state)

    assert "event=onboarding_validation_error" in caplog.text
    assert "stage=public_name" in caplog.text


@pytest.mark.asyncio
async def test_google_oauth_exception_does_not_leak_tokens(caplog, monkeypatch):
    def fake_exchange(_code: str):
        raise RuntimeError("access_token=SECRET refresh_token=SECRET")

    monkeypatch.setattr(google_oauth, "exchange_code_for_token", fake_exchange)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            await google_oauth.exchange_code_for_token_async("dummy-code", timeout=1)

    assert "access_token" not in caplog.text
    assert "refresh_token" not in caplog.text
