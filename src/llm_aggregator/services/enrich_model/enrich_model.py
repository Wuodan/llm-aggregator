from __future__ import annotations

import json
import logging
from typing import List

from llm_aggregator.config import get_settings
from llm_aggregator.models import Model, public_model_dict
from llm_aggregator.services.brain_client.brain_client import chat_completions
from llm_aggregator.services.files_size import FILES_SIZE_FIELD, gather_files_size
from llm_aggregator.services.model_info import fetch_model_markdown
from ._extract_json_object import _extract_json_list


async def enrich_batch(models: List[Model]) -> List[Model]:
    """Call the configured brain LLM to enrich metadata for a batch of models."""
    if not models:
        return []

    settings = get_settings()
    prompts_config = settings.brain_prompts
    enriched_models: List[Model] = []
    for model in models:
        meta = model.meta
        has_files_size = FILES_SIZE_FIELD in meta
        if not has_files_size:
            files_size_bytes = await gather_files_size(model)
            if files_size_bytes is not None:
                meta.setdefault(FILES_SIZE_FIELD, files_size_bytes)
                model.meta = meta

        api_models = [public_model_dict(model)]
        models_json = json.dumps(api_models, ensure_ascii=False)
        info_messages = await _build_info_messages(
            model,
            prompts_config.model_info_prefix_template,
        )

        messages = [
            {"role": "system", "content": prompts_config.system},
            {"role": "user", "content": prompts_config.user},
            *info_messages,
            {"role": "user", "content": models_json},
        ]

        payload = {
            "messages": messages,
            "temperature": 0.2,
        }

        enriched_list = await _get_enriched_list(payload)
        _merge_enrichment(model, enriched_list)
        enriched_models.append(model)

    logging.info("Brain enrichment produced %d entries", len(enriched_models))
    return enriched_models


async def _build_info_messages(
    model: Model,
    snippet_prefix_template: str,
) -> list[dict[str, str]]:
    snippets = await fetch_model_markdown(model)
    messages: list[dict[str, str]] = []
    for snippet in snippets:
        prefix = _render_snippet_prefix(
            snippet_prefix_template,
            snippet.model_id,
            snippet.source.provider_label,
        )
        markdown = snippet.markdown.strip()
        content = f"{prefix}\n\n{markdown}" if prefix else markdown
        messages.append({"role": "user", "content": content})
    return messages


def _render_snippet_prefix(
    template: str,
    model_id: str,
    provider_label: str,
) -> str:
    normalized_template = template or ""
    if not normalized_template.strip():
        return ""

    try:
        return normalized_template.format(
            model_id=model_id,
            provider_label=provider_label,
        )
    except KeyError as exc:
        logging.error(
            "brain_prompts.model_info_prefix_template has unknown placeholder: %s",
            exc,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logging.error(
            "brain_prompts.model_info_prefix_template formatting failed: %r",
            exc,
        )
    return normalized_template


async def _get_enriched_list(payload: dict[str, str | list[dict[str, str]] | float]) -> list:
    completions: str | None = await chat_completions(payload)

    try:
        # Extract JSON from content
        enriched_list = _extract_json_list(completions)
        if not isinstance(enriched_list, list):
            logging.error("Brain did not return a JSON list: %r", completions)
            return []

        return enriched_list

    except Exception as e:
        logging.error("Brain enrich error: %r", e)
        return []


def _merge_enrichment(model: Model, enriched_list: list) -> None:

    meta = model.meta

    for item in enriched_list:
        if not isinstance(item, dict):
            continue

        enriched_id = item.get("id")
        if model.id != enriched_id:
            continue

        enriched_base = item.get("base_url")
        if meta.base_url != enriched_base:
            continue

        # Merge into meta without overwriting existing keys
        for key, value in item.items():
            if key == "id":
                continue
            meta.setdefault(key, value)
        break
