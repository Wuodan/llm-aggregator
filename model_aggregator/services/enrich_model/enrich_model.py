from __future__ import annotations

import json
import logging
from typing import List

from model_aggregator.models import ModelInfo, EnrichedModel
from model_aggregator.services.brain_client._const import ENRICH_SYSTEM_PROMPT, ENRICH_USER_PROMPT
from model_aggregator.services.brain_client._map_enrich_result import _map_enrich_result
from model_aggregator.services.brain_client.brain_client import chat_completions
from ._extract_json_object import _extract_json_object


async def enrich_batch(models: List[ModelInfo]) -> List[EnrichedModel]:
    """Call the configured brain LLM to enrich metadata for a batch of models.

    Returns a list of EnrichedModel. On any error or malformed response,
    logs and returns an empty list.
    """
    if not models:
        return []

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

    payload = {
        "messages": [
            {"role": "system", "content": ENRICH_SYSTEM_PROMPT},
            {"role": "user", "content": ENRICH_USER_PROMPT},
            {"role": "user", "content": models_json},
        ],
        "temperature": 0.2,
    }

    enriched_list = _get_enriched_list(payload)

    # Map by (model, server_port) for safety
    input_keys = {
        (m.key.model_id, m.key.server_port): m.key for m in models
    }

    result = await _map_enrich_result(input_keys, enriched_list)

    logging.info("Brain enrichment produced %d entries", len(result))
    return result


async def _get_enriched_list(payload: dict[str, str | list[dict[str, str]] | float]):
    completions: str | None = await chat_completions(payload)

    try:
        # Extract JSON from content (robust against minor wrapping)
        enriched_obj: dict | None = _extract_json_object(completions)
        if not isinstance(enriched_obj, dict):
            logging.error("Brain did not return a JSON object: %r", completions)
            raise

        enriched_list = enriched_obj.get("enriched")
        if not isinstance(enriched_list, list):
            logging.error("Brain JSON missing 'enriched' list: %r", enriched_obj)
            raise

    except Exception as e:
        logging.error("Brain enrich error: %r", e)
        return []
    return enriched_list
