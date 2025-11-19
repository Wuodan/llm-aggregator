from __future__ import annotations

import logging

import uvicorn

from llm_aggregator.config import get_settings
from llm_aggregator._logging_utils import (
    apply_logger_overrides,
    build_uvicorn_log_config,
)


def main() -> None:
    """Run the LLM Aggregator API server."""
    settings = get_settings()

    log_level = (
        settings.log_level.upper()
        if isinstance(settings.log_level, str)
        else settings.log_level
    )

    logging.getLogger().setLevel(log_level)

    # Basic logging config; detailed config is also applied in api.lifespan
    if settings.log_format:
        logging.basicConfig(level=log_level, format=settings.log_format)

    apply_logger_overrides(settings.logger_overrides)

    uvicorn_log_config = build_uvicorn_log_config(
        log_level, settings.log_format, settings.logger_overrides
    )

    uvicorn.run(
        "llm_aggregator.api:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        access_log=False,
        log_config=uvicorn_log_config,
    )
if __name__ == "__main__":
    main()
