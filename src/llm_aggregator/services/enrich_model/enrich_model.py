from __future__ import annotations

import json
import logging
from typing import List

from llm_aggregator.models import EnrichedModel, ModelInfo
from llm_aggregator.services.brain_client.brain_client import chat_completions
from llm_aggregator.services.enrich_model._const import ENRICH_SYSTEM_PROMPT, ENRICH_USER_PROMPT
from llm_aggregator.services.enrich_model._map_enrich_result import _map_enrich_result
from llm_aggregator.services.model_info import fetch_model_markdown
from ._extract_json_object import _extract_json_object


async def enrich_batch(model_infos: List[ModelInfo]) -> List[EnrichedModel]:
    """Call the configured brain LLM to enrich metadata for a batch of models.

    Returns a list of EnrichedModel. On any error or malformed response,
    logs and returns an empty list.
    """
    if not model_infos:
        return []

    aggregated: List[EnrichedModel] = []
    for model in model_infos:
        input_models = {model.key: model}
        api_model_infos = [model.to_api_dict()]
        models_json = json.dumps(api_model_infos, ensure_ascii=False)

        info_messages = await _build_info_messages(model)
        messages = [
            {"role": "system", "content": ENRICH_SYSTEM_PROMPT},
            {"role": "user", "content": ENRICH_USER_PROMPT},
            *info_messages,
            {"role": "user", "content": models_json},
        ]

        payload = {
            "messages": messages,
            "temperature": 0.2,
        }

        enriched_list = await _get_enriched_list(payload)
        enriched_models = await _map_enrich_result(input_models, enriched_list)
        aggregated.extend(enriched_models)

    logging.info("Brain enrichment produced %d entries", len(aggregated))
    return aggregated


async def _build_info_messages(model: ModelInfo) -> list[dict[str, str]]:
    snippets = await fetch_model_markdown(model)
    messages: list[dict[str, str]] = []
    for snippet in snippets:
        prefix = f"Model-Info for {snippet.model_id} from {snippet.source.provider_label}:"
        content = f"{prefix}\n\n{snippet.markdown.strip()}"
        messages.append({"role": "user", "content": content})
    return messages


async def _get_enriched_list(payload: dict[str, str | list[dict[str, str]] | float]) -> list:
    completions: str | None = await chat_completions(payload)

    try:
        # Extract JSON from content (robust against minor wrapping)
        enriched_obj: dict | None = _extract_json_object(completions)
        if not isinstance(enriched_obj, dict):
            logging.error("Brain did not return a JSON object: %r", completions)
            return []

        enriched_list = enriched_obj.get("enriched")
        if not isinstance(enriched_list, list):
            logging.error("Brain JSON missing 'enriched' list: %r", enriched_obj)
            return []

        return enriched_list

    except Exception as e:
        logging.error("Brain enrich error: %r", e)
        return []
