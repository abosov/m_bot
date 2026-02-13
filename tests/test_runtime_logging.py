import importlib
import logging
from pathlib import Path

from services.runtime_logging import SafeLogFilter


def _reset_logging_state() -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    for name in ("http", "handlers"):
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
        logger.propagate = True
        logger.setLevel(logging.NOTSET)
    if hasattr(root, "_zumbot_runtime_logging_configured"):
        delattr(root, "_zumbot_runtime_logging_configured")


def test_configure_runtime_logging_without_log_dir(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.delenv("LOG_DIR", raising=False)
    monkeypatch.delenv("LOG_FILE_PREFIX", raising=False)

    import config
    import services.runtime_logging as runtime_logging

    importlib.reload(config)
    importlib.reload(runtime_logging)
    _reset_logging_state()

    runtime_logging.configure_runtime_logging()

    root_handlers = logging.getLogger().handlers
    assert root_handlers
    assert any(isinstance(handler, logging.StreamHandler) for handler in root_handlers)
    assert not any(getattr(handler, "baseFilename", None) for handler in root_handlers)


def test_configure_runtime_logging_with_log_dir_writes_files(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_FILE_PREFIX", "zumbot")

    import config
    import services.runtime_logging as runtime_logging

    importlib.reload(config)
    importlib.reload(runtime_logging)
    _reset_logging_state()

    runtime_logging.configure_runtime_logging()

    logging.getLogger("http").info("http-test-entry")
    for handler in logging.getLogger().handlers:
        handler.flush()
    for handler in logging.getLogger("http").handlers:
        handler.flush()

    app_log = tmp_path / "zumbot.app.log"
    http_log = tmp_path / "zumbot.http.log"
    bot_log = tmp_path / "zumbot.bot.log"

    assert app_log.exists()
    assert http_log.exists()
    assert bot_log.exists()
    assert "http-test-entry" in http_log.read_text(encoding="utf-8")


def test_safe_log_filter_handles_bad_percent_formatting() -> None:
    log_filter = SafeLogFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="%d",
        args=("not-a-number",),
        exc_info=None,
    )

    assert log_filter.filter(record) is True
    assert record.args == ()
    assert "[UNFORMATTABLE LOG]" in str(record.msg)
    assert "%d" in str(record.msg) or "not-a-number" in str(record.msg)


def test_safe_log_filter_keeps_normal_formatting_behavior() -> None:
    log_filter = SafeLogFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="x=%d",
        args=(1,),
        exc_info=None,
    )

    assert log_filter.filter(record) is True
    assert record.getMessage() == "x=1"
