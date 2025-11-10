from __future__ import annotations

import json
import logging
from typing import List

import aiohttp

from model_aggregator.config import get_settings
from model_aggregator.models import EnrichedModel, ModelInfo
from ._const import ENRICH_SYSTEM_PROMPT, ENRICH_USER_PROMPT
from ._map_enrich_result import _map_enrich_result
from ._parse_openai_response import _parse_openai_response


async def enrich_batch(models: List[ModelInfo]) -> List[EnrichedModel]:
    """Call the configured brain LLM to enrich metadata for a batch of models.

    Returns a list of EnrichedModel. On any error or malformed response,
    logs and returns an empty list.
    """
    if not models:
        return []

    settings = get_settings()
    enrich_cfg = settings.enrichment

    # Build prompt input: minimal but deterministic
    input_models = [
        {
            "id": m.key.model_id,
            "server_port": m.key.server_port,
        }
        for m in models
    ]

    # IMPORTANT: don't overwrite `models` (the list of ModelInfo)!
    models_json = json.dumps(input_models, ensure_ascii=False)

    url = f"{settings.brain_host}:{enrich_cfg.port}/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
    }
    if enrich_cfg.use_bearer_model_id:
        # For this special brain backend: bearer token equals model id
        headers["Authorization"] = f"Bearer {enrich_cfg.model_id}"

    payload = {
        "model": enrich_cfg.model_id,
        "messages": [
            {"role": "system", "content": ENRICH_SYSTEM_PROMPT},
            {"role": "user", "content": ENRICH_USER_PROMPT},
            {"role": "user", "content": models_json},
        ],
        "temperature": 0.2,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload,
                                    timeout=settings.timeout_enrich_models_seconds) as r:
                if r.status >= 400:
                    text = await r.text()
                    logging.error(
                        "Brain enrichment call failed with HTTP %s: %.200r",
                        r.status,
                        text,
                    )
                    return []

                try:
                    response = await r.json(content_type=None)
                except Exception:
                    text = await r.text()
                    logging.error("Brain returned non-JSON response: %.200r", text)
                    return []
    except Exception as e:
        if isinstance(e, TimeoutError):
            logging.warn("Brain enrichment timeout error: %r", e)
        else:
            logging.error("Brain enrichment request general error: %r", e)
        return []

    try:
        enriched_list = _parse_openai_response(response)

    except Exception as e:
        logging.error("Brain enrich error: %r", e)
        return []

    # Map by (model, server_port) for safety
    input_keys = {
        (m.key.model_id, m.key.server_port): m.key for m in models
    }

    result = await _map_enrich_result(input_keys, enriched_list)

    logging.info("Brain enrichment produced %d entries", len(result))
    return result
