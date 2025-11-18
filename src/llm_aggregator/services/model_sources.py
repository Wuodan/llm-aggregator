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
    """Fetch model list from one provider endpoint, robustly.

    Returns a list of ModelInfo entries. On any error, logs and returns an empty list.
    """
    base = provider.internal_base_url.rstrip("/")
    url = f"{base}/models"
    settings = get_settings()

    try:
        async with session.get(url, timeout=settings.fetch_models_timeout) as r:
            if r.status >= 400:
                text = await r.text()
                logging.error(
                    "Provider %s returned HTTP %s for /models: %.200r",
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
                    "Non-JSON /models from %s: %.200r",
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
            "Unexpected /models type from %s: %r",
            url,
            type(payload),
        )
        models_raw = []

    result: List[ModelInfo] = []
    for m in models_raw:
        if isinstance(m, dict) and "id" in m:
            model_key = ModelKey(provider=provider, id=str(m["id"]))
            result.append(ModelInfo(key=model_key))

    logging.info("Fetched %d models from url %s", len(result), url)
    return result


async def gather_models() -> List[ModelInfo]:
    """Aggregate model lists from all configured providers.

    Uses settings.providers to know which base URLs to query.
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
                p.internal_base_url,
                res,
            )
            continue
        all_models.extend(res)

    # sort by provider base_url, then by model id
    all_models.sort(key=lambda m: (m.key.provider.base_url, m.key.id.lower()))
    logging.info("Gathered %d models total", len(all_models))
    return all_models
