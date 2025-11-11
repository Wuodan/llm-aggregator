from __future__ import annotations

from model_aggregator.models import ModelKey, EnrichedModel

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
        input_keys: dict[tuple[str, int], ModelKey],
        enriched_list: list,
) -> list[EnrichedModel]:
    result = []
    for item in enriched_list:
        if not isinstance(item, dict):
            continue

        enriched = dict(item)  # copy it so we don’t mutate input
        model_id = enriched.get("id")
        port = enriched.get("port")

        if not isinstance(model_id, str) or not isinstance(port, int):
            continue

        key = input_keys.get((model_id, port))
        if not key:
            continue
        
        result.append(EnrichedModel(key=key, enriched=enriched))

    return result
