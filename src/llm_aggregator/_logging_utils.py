"""Helper utilities for keeping uvicorn's logging aligned with the app."""

from __future__ import annotations

import copy
import logging
from typing import Any

from uvicorn.config import LOGGING_CONFIG


def build_uvicorn_log_config(
    log_level: str | int,
    log_format: str | None,
    logger_overrides: dict[str, str | int],
) -> dict[str, Any]:
    """Return an uvicorn logging config aligned with the app settings."""

    log_config = copy.deepcopy(LOGGING_CONFIG)
    formatters = log_config.get("formatters", {})
    loggers = log_config.get("loggers", {})

    root_logger = log_config.get("root")
    if root_logger is not None:
        root_logger["level"] = log_level

    if log_format:
        for formatter_name in ("default", "access"):
            formatter = formatters.get(formatter_name)
            if formatter is not None:
                formatter["fmt"] = log_format

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = loggers.get(logger_name)
        if logger is not None:
            logger["level"] = log_level

    for logger_name, level in (logger_overrides or {}).items():
        logger_entry = loggers.setdefault(logger_name, {})
        logger_entry["level"] = level

    return log_config


def apply_logger_overrides(logger_overrides: dict[str, str | int]) -> None:
    """Directly apply override levels to named loggers.

    This makes sure dependency loggers are quiet even before uvicorn's dictConfig
    runs, and mirrors the overrides baked into the uvicorn logging config.
    """

    for logger_name, level in (logger_overrides or {}).items():
        logging.getLogger(logger_name).setLevel(level)
