import uuid

from services.web_session import sign_session_cookie, verify_session_cookie


def test_sign_and_verify_session_cookie(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", "test-signing-key")

    specialist_id = uuid.uuid4()
    tg_user_id = 123456789

    cookie = sign_session_cookie(specialist_id, tg_user_id, ttl_minutes=10)

    assert "." in cookie
    verified = verify_session_cookie(cookie)
    assert verified == (specialist_id, tg_user_id)


def test_verify_session_cookie_rejects_expired(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", "test-signing-key")

    specialist_id = uuid.uuid4()
    tg_user_id = 111

    monkeypatch.setattr("services.web_session.time.time", lambda: 1_000)
    cookie = sign_session_cookie(specialist_id, tg_user_id, ttl_minutes=1)

    monkeypatch.setattr("services.web_session.time.time", lambda: 1_061)
    assert verify_session_cookie(cookie) is None


def test_verify_session_cookie_rejects_tampered_signature(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", "test-signing-key")

    specialist_id = uuid.uuid4()
    cookie = sign_session_cookie(specialist_id, 42)

    payload, signature = cookie.split(".", 1)
    tampered_cookie = f"{payload}.{signature[:-1]}x"

    assert verify_session_cookie(tampered_cookie) is None
