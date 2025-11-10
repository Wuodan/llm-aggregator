#!/usr/bin/env python3
import asyncio
import logging
import time
from typing import Any, Dict, List

import aiohttp
import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# ---------- Config ----------

MARVIN_HOST = "http://10.7.2.100"
PORTS = [8080, 8090, 11434]

CACHE_TTL = 300  # seconds for /api/models responses

ENRICH_MODEL_ID = "unsloth/GLM-4.6-GGUF:UD-IQ2_XXS"
ENRICH_PORT = 8080
ENRICH_DELAY = 0.5  # delay between brain calls
ENRICH_LOOP_INTERVAL = 60  # how often the background loop tries to fill missing entries

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI()

# Full payload cache for /api/models
cache: Dict[str, Any] = {"data": None, "ts": 0}
# Per-model enrichment cache so we never re-ask brain for same id
# model_id -> {"summary": str, "recommended_use": str}
enriched_by_model: Dict[str, Dict[str, str]] = {}


# ---------- Model fetching ----------

async def fetch_models(session: aiohttp.ClientSession, port: int) -> List[Dict[str, Any]]:
    """Fetch model list from one LLM server port, robustly."""
    url = f"{MARVIN_HOST}:{port}/v1/models"
    try:
        async with session.get(url, timeout=10) as r:
            try:
                j = await r.json(content_type=None)
            except Exception:
                text = await r.text()
                logging.warning("Non-JSON /v1/models from port %s: %.200r", port, text)
                return []
    except Exception as e:
        logging.warning("Failed to fetch models from port %s: %s", port, e)
        return []

    models: List[Dict[str, Any]] = []

    if isinstance(j, dict):
        data = j.get("data")
        if isinstance(data, list):
            models = data
        elif isinstance(data, dict):
            models = [data]
        else:
            logging.warning("Unexpected dict structure from port %s: %r", port, j)
    elif isinstance(j, list):
        models = j
    else:
        logging.warning("Unexpected /v1/models type from port %s: %r", port, type(j))
        models = []

    clean: List[Dict[str, Any]] = []
    for m in models:
        if isinstance(m, dict) and "id" in m:
            m["server_port"] = port
            clean.append(m)

    logging.info("Fetched %d models from port %s", len(clean), port)
    return clean


async def gather_models() -> List[Dict[str, Any]]:
    """Aggregate model lists from all configured ports."""
    async with aiohttp.ClientSession() as s:
        results = await asyncio.gather(*(fetch_models(s, p) for p in PORTS))
    all_models: List[Dict[str, Any]] = [m for group in results for m in group]
    logging.info("Gathered %d models total", len(all_models))
    return all_models


# ---------- Enrichment helpers (two separate calls per model) ----------

async def brain_call(prompt: str, system_prompt: str) -> str:
    """Low-level helper to call brain and return stripped text."""
    try:
        headers = {}
        # Add Bearer API key only for port 8080 (others ignore it)
        if ENRICH_PORT == 8080:
            headers["Authorization"] = f"Bearer {ENRICH_MODEL_ID}"

        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                f"{MARVIN_HOST}:{ENRICH_PORT}/v1/chat/completions",
                headers=headers,
                json={
                    "model": ENRICH_MODEL_ID,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                },
            )

        if r.status_code == 429:
            logging.warning("brain rate limit (429) on prompt: %.120r", prompt)
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

        # Return first non-empty line for brevity
        for line in content.splitlines():
            line = line.strip()
            if line:
                return line
        return ""
    except Exception as e:
        logging.warning("Brain call failed: %s", e)
        return ""


async def get_summary(model_id: str) -> str:
    system_prompt = (
        "You are a concise, reliable assistant. "
        "Always follow the instructions exactly."
    )
    prompt = (
        f"Model ID: {model_id}\n"
        "In a few keywords (no bullets, no markdown) summarizing what this model is.\n"
        "Do not mention that you are an AI or assistant."
    )
    return await brain_call(prompt, system_prompt)


async def get_types(model_id: str) -> str:
    system_prompt = (
        "## Model Types\n\n"
        "Here are the model types and what they mean:\n\n"
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
    prompt = (
        f"Model ID: {model_id}\n"
        "You are a classifier that outputs only valid model type tokens.\n"
        "Allowed tokens are only the model types from the model table.\n"
        "Return a single JSON object: {\"types\": [\"space\", \"type1\", \"type2\", ...]}."
    )
    return await brain_call(prompt, system_prompt)


async def enrich_missing_once() -> None:
    """
    Enrich missing models once (non-blocking style):

    - Looks at the current cache's model list.
    - For each model without summary/recommended_use in enriched_by_model:
      call brain twice (summary + recommended), with a small delay.
    - Updates enriched_by_model and cache incrementally.
    """
    data = cache.get("data") or {}
    models = data.get("models") or []
    if not models:
        logging.info("No models in cache yet, skipping enrichment cycle")
        return

    # Find models that still need enrichment
    missing_ids: List[str] = []
    for m in models:
        mid = m.get("id")
        if not mid:
            continue
        info = enriched_by_model.get(mid)
        if not info or (not info.get("summary") or not info.get("recommended_use")):
            missing_ids.append(mid)

    if not missing_ids:
        logging.info("No missing enrichment entries this cycle")
        return

    logging.info("Enriching %d models this cycle", len(missing_ids))

    for mid in missing_ids:
        # Double-check in case another loop filled it
        current = enriched_by_model.get(mid, {})
        if current.get("summary") and current.get("recommended_use"):
            continue

        summary = current.get("summary") or await get_summary(mid)
        await asyncio.sleep(ENRICH_DELAY)
        recommended = current.get("recommended_use") or await get_types(mid)
        await asyncio.sleep(ENRICH_DELAY)

        enriched_by_model[mid] = {
            "summary": summary or "",
            "recommended_use": recommended or "",
        }

        # Update cache.enriched incrementally so /api/models shows progress
        cached = cache.get("data")
        if cached:
            enriched_list: List[Dict[str, Any]] = []
            for m in cached.get("models", []):
                mid2 = m.get("id")
                if not mid2:
                    continue
                info2 = enriched_by_model.get(mid2, {"summary": "", "recommended_use": ""})
                enriched_list.append(
                    {
                        "model": mid2,
                        "summary": info2.get("summary", ""),
                        "recommended_use": info2.get("recommended_use", ""),
                    }
                )
            cached["enriched"] = enriched_list
            # no ts bump needed; it's still "current snapshot"
    logging.info("Enrichment cycle completed")


# ---------- Cache management ----------

def build_enriched_snapshot(models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build enriched list from current cache; blanks where unknown."""
    enriched_list: List[Dict[str, Any]] = []
    for m in models:
        mid = m.get("id")
        if not mid:
            continue
        info = enriched_by_model.get(mid, {"summary": "", "recommended_use": ""})
        enriched_list.append(
            {
                "model": mid,
                "summary": info.get("summary", ""),
                "recommended_use": info.get("recommended_use", ""),
            }
        )
    return enriched_list


async def refresh_cache_models_only() -> None:
    """
    Refresh only the model list and expose whatever enrichment we already have.

    This is fast and ensures /api/models always returns immediately with:
    - full live model list
    - summaries/uses for models we already processed
    - blanks for the rest
    """
    logging.info("Refreshing models list (models-only)")
    models = await gather_models()
    # sort by port, then by model id
    models.sort(
        key=lambda m: (
            m.get("server_port", 0),
            str(m.get("id", "")).lower(),
        )
    )
    enriched_snapshot = build_enriched_snapshot(models)
    cache["data"] = {"models": models, "enriched": enriched_snapshot}
    cache["ts"] = time.time()
    logging.info(
        "Models-only cache updated: %d models, %d enriched entries present",
        len(models),
        sum(1 for e in enriched_snapshot if e.get("summary") or e.get("recommended_use")),
    )


# ---------- FastAPI lifecycle & endpoints ----------

@app.on_event("startup")
async def startup_event() -> None:
    """
    On startup:
    - Fetch models & build initial snapshot (no waiting for brain).
    - Start background task that periodically fills missing enrichment.
    """
    await refresh_cache_models_only()

    async def enrich_loop():
        while True:
            try:
                await enrich_missing_once()
            except Exception as e:
                logging.warning("Enrichment loop error: %s", e)
            await asyncio.sleep(ENRICH_LOOP_INTERVAL)

    asyncio.create_task(enrich_loop())


@app.get("/api/models")
async def api_models():
    """
    Return cached model data.

    If TTL expired, refresh models list quickly (no blocking on brain).
    Enrichment continues in the background and is reflected progressively.
    """
    if not cache["data"] or (time.time() - cache["ts"] > CACHE_TTL):
        await refresh_cache_models_only()
    return JSONResponse(cache["data"])


# Serve ./static (index.html) at /
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8888)
