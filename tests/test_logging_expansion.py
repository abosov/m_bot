import logging
import types
import warnings

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


def test_google_oauth_scope_change_warning_is_ignored(monkeypatch):
    class _FakeFlow:
        def __init__(self):
            self.credentials = types.SimpleNamespace(refresh_token="r1", token="a1", scopes=["scope-a"])

        def fetch_token(self, code):
            warnings.warn(
                "Scope has changed from \"old\" to \"new\".",
                UserWarning,
            )

    monkeypatch.setattr(google_oauth, "_ensure_google_oauth_config", lambda: None)
    monkeypatch.setattr(
        google_oauth.Flow,
        "from_client_config",
        lambda *args, **kwargs: _FakeFlow(),
    )

    refresh_token, access_token, credentials = google_oauth.exchange_code_for_token("dummy-code")

    assert refresh_token == "r1"
    assert access_token == "a1"
    assert credentials.scopes == ["scope-a"]


def test_google_oauth_scope_change_warning_without_details_is_ignored(monkeypatch):
    class _FakeFlow:
        def __init__(self):
            self.credentials = types.SimpleNamespace(refresh_token="r2", token="a2", scopes=["scope-b"])

        def fetch_token(self, code):
            warnings.warn("Scope has changed", Warning)

    monkeypatch.setattr(google_oauth, "_ensure_google_oauth_config", lambda: None)
    monkeypatch.setattr(
        google_oauth.Flow,
        "from_client_config",
        lambda *args, **kwargs: _FakeFlow(),
    )

    refresh_token, access_token, credentials = google_oauth.exchange_code_for_token("dummy-code")

    assert refresh_token == "r2"
    assert access_token == "a2"
    assert credentials.scopes == ["scope-b"]
