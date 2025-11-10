from __future__ import annotations

from typing import List

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


async def _map_enrich_result(input_keys: dict[tuple[str, int], ModelKey], enriched_list: list) -> list[EnrichedModel]:
    result: List[EnrichedModel] = []
    for item in enriched_list:
        if not isinstance(item, dict):
            continue

        model = item.get("model")
        port = item.get("server_port")
        if not isinstance(model, str) or not isinstance(port, int):
            continue

        key_tuple = (model, port)
        key = input_keys.get(key_tuple)
        if key is None:
            # Unknown model: ignore
            continue

        summary = str(item.get("summary") or "").strip()

        types_raw = item.get("types") or []
        if isinstance(types_raw, str):
            types_raw = [types_raw]
        if not isinstance(types_raw, list):
            types_raw = []

        types: List[str] = []
        for t in types_raw:
            if not isinstance(t, str):
                continue
            t_norm = t.strip().lower()
            if t_norm in _ALLOWED_TYPES:
                types.append(t_norm)
        types = sorted(set(types))

        result.append(
            EnrichedModel(
                key=key,
                summary=summary,
                types=types,
            )
        )
    return result
