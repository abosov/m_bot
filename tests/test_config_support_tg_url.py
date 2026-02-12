import importlib


def test_support_tg_url_defaults_when_env_missing(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("SUPPORT_TG_URL", raising=False)

    import config

    importlib.reload(config)

    assert config.SUPPORT_TG_URL == "https://t.me/zumbot_support"


def test_support_tg_url_uses_env_value(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("SUPPORT_TG_URL", "https://t.me/custom_support")

    import config

    importlib.reload(config)

    assert config.SUPPORT_TG_URL == "https://t.me/custom_support"


def test_support_tg_url_defaults_in_prod_when_env_missing(monkeypatch):
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.delenv("SUPPORT_TG_URL", raising=False)

    import config

    importlib.reload(config)

    assert config.SUPPORT_TG_URL == "https://t.me/zumbot_support"
