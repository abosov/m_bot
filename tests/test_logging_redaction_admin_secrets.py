import logging

from services.redaction import redact_text
from services.runtime_logging import SafeLogFilter


def test_redact_text_hides_admin_and_oauth_secrets() -> None:
    text = (
        "ADMIN_API_KEY=super-secret "
        "ADMIN_UI_PASSWORD:ui-pass "
        "Cookie: admin_session=signed.cookie.value; Path=/; "
        "access_token=oauth-access "
        "refresh_token=oauth-refresh "
        "oauth_token=oauth-token"
    )

    redacted = redact_text(text)

    assert "super-secret" not in redacted
    assert "ui-pass" not in redacted
    assert "signed.cookie.value" not in redacted
    assert "oauth-access" not in redacted
    assert "oauth-refresh" not in redacted
    assert "oauth-token" not in redacted
    assert "[REDACTED_SECRET]" in redacted
    assert "[REDACTED_COOKIE]" in redacted
    assert redacted.count("[REDACTED_TOKEN]") >= 3


def test_safe_log_filter_redacts_message_and_args() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="api=%s cookie=%s refresh_token=%s",
        args=("ADMIN_API_KEY=abc123", "admin_session=xyz", "refresh_token=qwerty"),
        exc_info=None,
    )

    assert SafeLogFilter().filter(record) is True

    message = record.getMessage()
    assert "abc123" not in message
    assert "admin_session=xyz" not in message
    assert "qwerty" not in message
    assert "[REDACTED_SECRET]" in message or "[REDACTED_TOKEN]" in message
    assert "[REDACTED_COOKIE]" in message
