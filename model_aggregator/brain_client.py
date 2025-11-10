import json
import logging
from typing import Any, Dict, List

import httpx

from .config import ENRICH_MODEL_ID, ENRICH_PORT, MARVIN_HOST, USE_BEARER_ON_ENRICH_PORT


async def _post_to_brain(payload: Dict[str, Any]) -> str:
    """Low-level helper: call the brain model and return raw content string."""
    headers: Dict[str, str] = {}
    if USE_BEARER_ON_ENRICH_PORT:
        # Only this port requires / cares about the Bearer; others ignore it.
        headers["Authorization"] = f"Bearer {ENRICH_MODEL_ID}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"{MARVIN_HOST}:{ENRICH_PORT}/v1/chat/completions",
            headers=headers,
            json=payload,
        )

    if r.status_code == 429:
        logging.warning("Brain rate-limited with 429")
        return ""

    r.raise_for_status()
    data = r.json()
    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    if not isinstance(content, str):
        return ""
    return content.strip()


async def enrich_models(models: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Call the brain ONCE to get enrichment JSON for all models.

    Input: list of model dicts (must include `id` and `server_port`).
    Output (best-effort):

    {
      "enriched": [
        {
          "model": "<id>",
          "summary": "<short text>",
          "types": ["llm", "vlm", ...],
          "recommended_use": "<short guidance>",
          "priority": 1-10
        },
        ...
      ]
    }

    If parsing fails, returns an empty structure.
    """
    if not models:
        return {"enriched": []}

    # Send only the minimal necessary context to keep prompts compact.
    minimal_models = [
        {
            "id": m.get("id"),
            "server_port": m.get("server_port"),
        }
        for m in models
        if m.get("id")
    ]

    system_prompt = (
        "You are a strict JSON generator for local LLM model metadata.\n"
        "You ALWAYS follow all instructions exactly.\n"
        "You know about common open-source models from Hugging Face etc., "
        "but if you are unsure, you guess conservatively.\n"
        "You never output markdown, backticks, or explanations.\n"
        "Your entire response MUST be a single valid JSON object."
    )

    # Build user prompt in a compile-safe way with proper escaping.
    user_prompt = (
        "Given the following JSON array 'models', generate detailed metadata for each model.\n"
        "Input 'models': "
        + json.dumps(minimal_models)
        + "\n"
        "Return EXACTLY this JSON structure and nothing else:\n"
        "{\n"
        "  \"enriched\": [\n"
        "    {\n"
        "      \"model\": \"<exact id from input>\",\n"
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
    )

    payload = {
        "model": ENRICH_MODEL_ID,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    raw = await _post_to_brain(payload)
    if not raw:
        logging.warning("Brain returned empty content")
        return {"enriched": []}

    # Try to robustly extract JSON
    text = raw.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        logging.warning(
            "Brain response did not contain JSON-looking content: %.200r",
            raw,
        )
        return {"enriched": []}

    json_str = text[start : end + 1]
    try:
        obj = json.loads(json_str)
    except Exception as e:
        logging.warning("Failed to parse brain JSON: %s; raw=%.200r", e, raw)
        return {"enriched": []}

    enriched = obj.get("enriched")
    if not isinstance(enriched, list):
        logging.warning("Brain JSON missing 'enriched' list: %.200r", obj)
        return {"enriched": []}

    # Normalize entries
    norm: List[Dict[str, Any]] = []
    allowed = {
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

    for e in enriched:
        if not isinstance(e, dict):
            continue
        mid = e.get("model")
        if not mid:
            continue
        summary = e.get("summary") or ""
        rec = e.get("recommended_use") or ""
        types = e.get("types") or []
        if not isinstance(types, list):
            types = []
        # keep only allowed tokens
        types = [
            t for t in types if isinstance(t, str) and t in allowed
        ]
        priority = e.get("priority")
        try:
            priority = int(priority)
        except Exception:
            priority = 5

        norm.append(
            {
                "model": mid,
                "summary": str(summary),
                "types": types,
                "recommended_use": str(rec),
                "priority": priority,
            }
        )

    return {"enriched": norm}
