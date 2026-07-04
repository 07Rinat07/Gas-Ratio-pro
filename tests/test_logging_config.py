from __future__ import annotations

from core.logging_config import DEFAULT_LOG_FILE, configure_logging, safe_log_value


def test_configure_logging_writes_to_file(tmp_path):
    logger = configure_logging(log_dir=tmp_path, reset_handlers=True)

    logger.info("test_event feature=logging")
    for handler in logger.handlers:
        handler.flush()

    log_path = tmp_path / DEFAULT_LOG_FILE
    assert log_path.exists()
    assert "test_event feature=logging" in log_path.read_text(encoding="utf-8")


def test_configure_logging_does_not_duplicate_handlers(tmp_path):
    logger = configure_logging(log_dir=tmp_path, reset_handlers=True)
    handler_count = len(logger.handlers)

    same_logger = configure_logging(log_dir=tmp_path)

    assert same_logger is logger
    assert len(same_logger.handlers) == handler_count


def test_safe_log_value_strips_newlines_and_truncates():
    value = safe_log_value("line 1\nline 2" + "x" * 200, max_length=20)

    assert "\n" not in value
    assert len(value) <= 23
    assert value.endswith("...")
