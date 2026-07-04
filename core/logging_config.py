from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOGGER_NAME = "gas_ratio"
DEFAULT_LOG_FILE = "app.log"
DEFAULT_MAX_BYTES = 1_000_000
DEFAULT_BACKUP_COUNT = 5


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_log_dir() -> Path:
    return project_root() / "logs"


def _remove_owned_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        if getattr(handler, "_gas_ratio_handler", False):
            logger.removeHandler(handler)
            handler.close()


def configure_logging(
    log_dir: str | Path | None = None,
    level: int = logging.INFO,
    reset_handlers: bool = False,
) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    if reset_handlers:
        _remove_owned_handlers(logger)

    resolved_log_dir = Path(log_dir) if log_dir is not None else default_log_dir()
    resolved_log_dir.mkdir(parents=True, exist_ok=True)
    log_path = resolved_log_dir / DEFAULT_LOG_FILE

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not any(getattr(handler, "_gas_ratio_file_handler", False) for handler in logger.handlers):
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=DEFAULT_MAX_BYTES,
            backupCount=DEFAULT_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        file_handler._gas_ratio_handler = True
        file_handler._gas_ratio_file_handler = True
        logger.addHandler(file_handler)

    if not any(getattr(handler, "_gas_ratio_stream_handler", False) for handler in logger.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(level)
        stream_handler._gas_ratio_handler = True
        stream_handler._gas_ratio_stream_handler = True
        logger.addHandler(stream_handler)

    return logger


def safe_log_value(value: object, max_length: int = 120) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r", " ").replace("\n", " ").strip()
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}..."