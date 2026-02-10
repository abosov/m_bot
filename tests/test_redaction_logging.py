from logging_middleware import _redact_logged_content
from services.redaction import redact_text


def test_redact_telegram_bot_token():
    token = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi-12345"
    text = f"received token {token} from user"

    redacted = redact_text(text)

    assert token not in redacted
    assert "[REDACTED_TELEGRAM_BOT_TOKEN]" in redacted


def test_redact_bearer_or_refresh_token():
    source = (
        "Authorization: Bearer abcdefghijklmnopqrstuvwxyz12345 "
        "refresh_token=my-refresh-token"
    )

    redacted = redact_text(source)

    assert "Bearer abcdefghijklmnopqrstuvwxyz12345" not in redacted
    assert "Bearer [REDACTED_BEARER_TOKEN]" in redacted
    assert "refresh_token=[REDACTED_TOKEN]" in redacted


def test_fsm_waiting_for_bot_token_suppresses_content():
    content = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghi-12345"

    redacted = _redact_logged_content(content, "MasterOnboarding:waiting_for_bot_token")

    assert redacted == "[REDACTED_BOT_TOKEN]"
