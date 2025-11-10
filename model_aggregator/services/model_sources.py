from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

import aiohttp

from ..config import get_settings
from ..models import ModelKey, ModelInfo, ProviderConfig


async def _fetch_models_for_provider(
    session: aiohttp.ClientSession,
    provider: ProviderConfig,
) -> List[ModelInfo]:
    """Fetch model list from one provider (one port), robustly.

    Returns a list of ModelInfo entries. On any error, logs and returns an empty list.
    """
    url = f"{provider.base_endpoint}/v1/models"
    port = provider.port
    settings = get_settings()

    try:
        async with session.get(url, timeout=settings.timeout_fetch_models_seconds) as r:
            if r.status >= 400:
                text = await r.text()
                logging.error(
                    "Provider %s returned HTTP %s for /v1/models: %.200r",
                    url,
                    r.status,
                    text,
                )
                return []
            try:
                payload = await r.json(content_type=None)
            except Exception:
                text = await r.text()
                logging.error(
                    "Non-JSON /v1/models from %s: %.200r",
                    url,
                    text,
                )
                return []
    except Exception as e:
        # Treat provider as down; its models will be removed on next refresh.
        logging.error("Failed to fetch models from %s: %s", url, e)
        return []

    models_raw: List[Dict[str, Any]] = []

    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            models_raw = data
        elif isinstance(data, dict):
            models_raw = [data]
        else:
            logging.error(
                "Unexpected dict structure from %s: %r",
                url,
                payload,
            )
    elif isinstance(payload, list):
        models_raw = payload
    else:
        logging.error(
            "Unexpected /v1/models type from %s: %r",
            url,
            type(payload),
        )
        models_raw = []

    result: List[ModelInfo] = []
    for m in models_raw:
        if isinstance(m, dict) and "id" in m:
            model_id = str(m["id"])
            key = ModelKey(server_port=port, model_id=model_id)
            raw = dict(m)
            raw["server_port"] = port
            result.append(ModelInfo(key=key, raw=raw))

    logging.info("Fetched %d models from port %s", len(result), port)
    return result


async def gather_models() -> List[ModelInfo]:
    """Aggregate model lists from all configured providers.

    Uses settings.providers to know which ports/base URLs to query.
    """
    settings = get_settings()
    providers = settings.providers

    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            *(_fetch_models_for_provider(session, p) for p in providers),
            return_exceptions=True,
        )

    all_models: List[ModelInfo] = []
    for idx, res in enumerate(results):
        if isinstance(res, Exception):
            p = providers[idx]
            logging.error(
                "Unhandled error while fetching models from %s: %s",
                p.base_endpoint,
                res,
            )
            continue
        all_models.extend(res)

    # sort by port, then by model id
    all_models.sort(key=lambda m: (m.key.server_port, m.key.model_id.lower()))
    logging.info("Gathered %d models total", len(all_models))
    return all_models

