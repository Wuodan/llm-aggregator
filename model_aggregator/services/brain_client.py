from __future__ import annotations

import json
import logging
from typing import List

import aiohttp

from ..config import get_settings
from ..models import EnrichedModel, ModelInfo


ALLOWED_TYPES = {
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

    system_prompt = (
        "You are a strict JSON generator that analyzes a list of models and returns "
        "concise metadata.\n"
        "Only respond with a single JSON object, no markdown, no extra text."
    )

    system_prompt = (
        "You are a strict JSON generator that analyzes a list of models and returns "
        "concise metadata.\n"
        "Only respond with a single JSON object, no markdown, no extra text.\n\n"
        "## LLM Model Types"
        "For your knowledge here are LLM model types and what they mean:\n\n"
        "| Type          | Full Name / Meaning          | Input → Output                   | Typical Use Case                          |\n"
        "|---------------|------------------------------|----------------------------------|-------------------------------------------|\n"
        "| llm           | Large Language Model         | Text → Text                      | Chatbots, coding assistants, reasoning    |\n"
        "| vlm           | Vision-Language Model        | Image + Text → Text              | Visual Q&A, captioning, multimodal agents |\n"
        "| embedder      | Embedding Model              | Text → Vector (numeric array)    | Semantic search, retrieval, RAG           |\n"
        "| reranker      | Reranking Model              | Query + Candidates → Ranked list | Improving search or RAG results           |\n"
        "| tts           | Text-to-Speech               | Text → Audio                     | Generate spoken output, voice synthesis   |\n"
        "| asr           | Automatic Speech Recognition | Audio → Text                     | Transcribe recordings or live speech      |\n"
        "| diarize       | Speaker Diarization          | Audio → Speaker segments         | Detect who spoke when in audio            |\n"
        "| cv            | Computer Vision              | Image → Labels / Features        | Object detection, classification          |\n"
        "| image_gen     | Image Generation             | Text → Image                     | Generative art, visual assistants         |\n"
    )

    user_prompt = (
        "Given the following JSON array 'models', generate detailed metadata for each model.\n"
        "\n"
        "Return EXACTLY this JSON structure and nothing else:\n"
        "{\n"
        "  \"enriched\": [\n"
        "    {\n"
        "      \"model\": \"<exact id from input>\",\n"
        "      \"server_port\": <port from input>,\n"
        "      \"summary\": \"<very short description of this specific model>\",\n"
        "      \"types\": [\"llm\" | \"vlm\" | \"embedder\" | \"reranker\" | \"tts\" | \"asr\" | \"diarize\" | \"cv\" | \"image_gen\"],\n"
        "      \"recommended_use\": \"<1 concise sentence with recommended use cases>\",\n"
        "      \"priority\": <integer 1-10, higher means better default choice>\n"
        "    },\n"
        "    ... one entry per input model, in the same order ...\n"
        "  ]\n"
        "}\n"
        "Rules:\n"
        "- Include EVERY input model exactly once.\n"
        "- Use ONLY the allowed type tokens.\n"
        "- Keep summaries and recommended_use concise.\n"
        "- Never add extra top-level keys.\n"
        "- Never wrap your answer in markdown.\n"
        "\n"
        "Input 'models' follow (JSON array):"
    )

    # IMPORTANT: don't overwrite `models` (the list of ModelInfo)!
    models_json = json.dumps(input_models, ensure_ascii=False)

    url = f"{settings.marvin_host}:{enrich_cfg.port}/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
    }
    if enrich_cfg.use_bearer_model_id:
        # For this special brain backend: bearer token equals model id
        headers["Authorization"] = f"Bearer {enrich_cfg.model_id}"

    payload = {
        "model": enrich_cfg.model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "user", "content": models_json},
        ],
        "temperature": 0.2,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=60) as r:
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
        logging.error("Brain enrichment request error: %r", e)
        return []

    # Parse OpenAI-style response
    try:
        content = (
            response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        if not isinstance(content, str) or not content.strip():
            logging.error("Brain response missing content field: %r", response)
            return []
    except Exception as e:
        logging.error("Brain response parsing error: %r", e)
        return []

    # Extract JSON from content (robust against minor wrapping)
    enriched_obj = _extract_json_object(content)
    if not isinstance(enriched_obj, dict):
        logging.error("Brain did not return a JSON object: %r", content)
        return []

    enriched_list = enriched_obj.get("enriched")
    if not isinstance(enriched_list, list):
        logging.error("Brain JSON missing 'enriched' list: %r", enriched_obj)
        return []

    # Map by (model, server_port) for safety
    input_keys = {
        (m.key.model_id, m.key.server_port): m.key for m in models
    }

    result: List[EnrichedModel] = []
    for item in enriched_list:
        if not isinstance(item, dict):
            continue

        mid = item.get("model")
        port = item.get("server_port")
        if not isinstance(mid, str) or not isinstance(port, int):
            continue

        key_tuple = (mid, port)
        key = input_keys.get(key_tuple)
        if key is None:
            # Unknown model: ignore
            continue

        summary = str(item.get("summary") or "").strip()
        recommended_use = str(item.get("recommended_use") or "").strip()
        priority_raw = item.get("priority", 5)
        try:
            priority = int(priority_raw)
        except Exception:
            priority = 5
        if priority < 1:
            priority = 1
        if priority > 10:
            priority = 10

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
            if t_norm in ALLOWED_TYPES:
                types.append(t_norm)
        types = sorted(set(types))

        result.append(
            EnrichedModel(
                key=key,
                summary=summary,
                types=types,
                recommended_use=recommended_use,
                priority=priority,
            )
        )

    logging.info("Brain enrichment produced %d entries", len(result))
    return result


def _extract_json_object(text: str):
    """Best-effort extraction of a JSON object from a string.

    The brain *should* return a single JSON object, but in practice might wrap
    it in markdown fences or extra text. This attempts to find the first '{'
    and the last '}' and parse what's in between.
    """
    text = text.strip()
    if not text:
        return None

    # Fast path: maybe it's already pure JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except Exception:
        return None
