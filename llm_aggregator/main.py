from __future__ import annotations

import logging

import uvicorn


def main() -> None:
    """Run the LLM Aggregator API server.

    Uses the FastAPI app defined in ``llm_aggregator.api:app``.
    """
    # Basic logging config; detailed config is also applied in api.lifespan
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    uvicorn.run(
        "llm_aggregator.api:app",
        host="0.0.0.0",
        port=8888,
        reload=False,
    )


if __name__ == "__main__":
    main()
