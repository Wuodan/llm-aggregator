import asyncio
import logging
from typing import Any, Dict, List

import aiohttp

from model_aggregator.config import MARVIN_HOST, PORTS


async def fetch_models(session: aiohttp.ClientSession, port: int) -> List[Dict[str, Any]]:
    """Fetch model list from one LLM server port, robustly."""
    url = f"{MARVIN_HOST}:{port}/v1/models"
    try:
        async with session.get(url, timeout=10) as r:
            try:
                j = await r.json(content_type=None)
            except Exception:
                text = await r.text()
                logging.error("Non-JSON /v1/models from port %s: %.200r", port, text)
                return []
    except Exception as e:
        logging.error("Failed to fetch models from port %s: %s", port, e)
        return []

    models: List[Dict[str, Any]] = []

    if isinstance(j, dict):
        data = j.get("data")
        if isinstance(data, list):
            models = data
        elif isinstance(data, dict):
            models = [data]
        else:
            logging.error("Unexpected dict structure from port %s: %r", port, j)
    elif isinstance(j, list):
        models = j
    else:
        logging.error("Unexpected /v1/models type from port %s: %r", port, type(j))
        models = []

    clean: List[Dict[str, Any]] = []
    for m in models:
        if isinstance(m, dict) and "id" in m:
            m = dict(m)
            m["server_port"] = port
            clean.append(m)

    logging.info("Fetched %d models from port %s", len(clean), port)
    return clean


async def gather_models() -> List[Dict[str, Any]]:
    """Aggregate model lists from all configured ports."""
    async with aiohttp.ClientSession() as s:
        results = await asyncio.gather(*(fetch_models(s, p) for p in PORTS))
    all_models: List[Dict[str, Any]] = [m for group in results for m in group]
    logging.info("Gathered %d models total", len(all_models))
    # sort by port, then by model id (case-insensitive)
    all_models.sort(
        key=lambda m: (
            m.get("server_port", 0),
            str(m.get("id", "")).lower(),
        )
    )
    return all_models
