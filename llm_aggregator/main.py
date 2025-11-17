from __future__ import annotations

import logging

import uvicorn

from llm_aggregator.config import get_settings


def main() -> None:
    """Run the LLM Aggregator API server.

    Uses the FastAPI app defined in ``llm_aggregator.api:app``.
    """
    settings = get_settings()

    log_level = (
        settings.log_level.upper()
        if isinstance(settings.log_level, str)
        else settings.log_level
    )

    # Basic logging config; detailed config is also applied in api.lifespan
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    )

    uvicorn.run(
        "llm_aggregator.api:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
