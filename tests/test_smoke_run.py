from types import SimpleNamespace

import scripts.smoke_run as smoke_run


class DummySession:
    pass


def _make_args(since_minutes=None):
    return SimpleNamespace(
        base_url="https://example.test",
        admin_api_key="secret",
        since_minutes=since_minutes,
    )


def test_run_smoke_success(monkeypatch, capsys):
    responses = {
        "https://example.test/healthz": (200, {"status": "ok"}),
        "https://example.test/readyz": (200, {"status": "ready"}),
        "https://example.test/admin/heartbeats": (200, {"items": [{}]}),
        "https://example.test/admin/logs": (200, {"items": [{}]}),
        "https://example.test/admin/bot-health-checks": (200, {"items": [{}]}),
    }

    monkeypatch.setattr(smoke_run.requests, "Session", lambda: DummySession())

    def fake_request_json(_session, _method, url, **_kwargs):
        return responses[url]

    monkeypatch.setattr(smoke_run, "_request_json", fake_request_json)

    rc = smoke_run.run_smoke(_make_args(since_minutes=30))

    assert rc == 0
    assert "Итог: smoke check пройден успешно." in capsys.readouterr().out


def test_run_smoke_fails_on_health(monkeypatch):
    responses = {
        "https://example.test/healthz": (500, {"status": "fail"}),
        "https://example.test/readyz": (404, {"detail": "Not found"}),
        "https://example.test/admin/heartbeats": (200, {"items": []}),
        "https://example.test/admin/logs": (200, {"items": []}),
        "https://example.test/admin/bot-health-checks": (200, {"items": []}),
    }

    monkeypatch.setattr(smoke_run.requests, "Session", lambda: DummySession())

    def fake_request_json(_session, _method, url, **_kwargs):
        return responses[url]

    monkeypatch.setattr(smoke_run, "_request_json", fake_request_json)

    rc = smoke_run.run_smoke(_make_args())

    assert rc == 1
