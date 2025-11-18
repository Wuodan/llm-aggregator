from __future__ import annotations

from llm_aggregator.models import ModelKey, EnrichedModel, ModelInfo

_ALLOWED_TYPES = {
    "llm",
    "vlm",
    "embedder",
    "reranker",
    "tts",
    "asr",
    "diarize",
    "cv",
    "image_gen",
}


async def _map_enrich_result(
    input_models: dict[ModelKey, ModelInfo],
    enriched_list: list,
) -> list[EnrichedModel]:
    result = []
    for item in enriched_list:
        if not isinstance(item, dict):
            continue

        enriched = dict(item)  # copy it so we don’t mutate input
        model_key = ModelKey.from_api_dict(enriched)

        if not isinstance(model_key, ModelKey):
            continue

        model_info = input_models.get(model_key)
        if not model_info:
            continue

        enriched.pop("internal_base_url", None)
        result.append(EnrichedModel(key=model_key, enriched=enriched))

    return result
