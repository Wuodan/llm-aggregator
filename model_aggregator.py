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

MARVIN_HOST = "http://10.7.2.100"
PORTS = [8080, 8090, 11434]

CACHE_TTL = 300  # seconds for /api/models responses
ENRICH_MODEL_ID = "NexaAI/gemma-3n-E2B-it-4bit-MLX"
ENRICH_PORT = 8090
ENRICH_DELAY = 0.4  # delay between enrich calls to avoid 429

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI()

# Full payload cache for /api/models
cache: Dict[str, Any] = {"data": None, "ts": 0}
# Per-model enrichment cache so we never re-ask Gemma for same id
enriched_by_model: Dict[str, Dict[str, str]] = {}


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


def _strip_md(line: str) -> str:
    """Remove simple markdown chars."""
    return line.lstrip("#*- ").strip()


def parse_enrichment_text(model_id: str, content: str) -> Dict[str, str]:
    """
    Extract summary & recommendation from messy LLM output.
    Best-effort, never throws.
    """
    content = (content or "").strip()
    if not content:
        return {"summary": "", "recommended_use": ""}

    lines = [l.strip() for l in content.splitlines() if l.strip()]
    summary = ""
    recommended = ""

    # Prefer explicit markers
    for raw in lines:
        line = _strip_md(raw)
        lower = line.lower()

        if not summary and (lower.startswith("summary:") or lower.startswith("**summary:**")):
            summary = line.split(":", 1)[1].strip()
            continue

        if not recommended and (
            lower.startswith("recommended:")
            or lower.startswith("**recommended:**")
            or lower.startswith("use-case:")
            or lower.startswith("**use-case:**")
        ):
            recommended = line.split(":", 1)[1].strip()
            continue

        if not summary and lower.startswith("line 1:"):
            summary = line.split(":", 1)[1].strip()
            continue

        if not recommended and lower.startswith("line 2:"):
            recommended = line.split(":", 1)[1].strip()
            continue

    # Fallback: first and second sentence
    if not summary or not recommended:
        text = " ".join(_strip_md(l) for l in lines)
        parts = [p.strip() for p in text.replace("\n", " ").split(".") if p.strip()]
        if not summary and parts:
            summary = parts[0]
        if not recommended and len(parts) > 1:
            recommended = parts[1]

    if not summary and not recommended:
        logging.warning("Unparseable enrichment for %s: %.200r", model_id, content)
        return {"summary": "", "recommended_use": ""}

    return {"summary": summary, "recommended_use": recommended}


async def enrich_single(client: httpx.AsyncClient, model_id: str) -> Dict[str, str]:
    """Ask Gemma about one model id. Best-effort, safe."""
    prompt = (
        "You are a concise model catalog helper.\n"
        "For the given local model ID, briefly explain what it is and when to use it.\n"
        "Respond in 2-4 short sentences. Do NOT output JSON.\n\n"
        f"Model ID: {model_id}"
    )

    try:
        r = await client.post(
            f"{MARVIN_HOST}:{ENRICH_PORT}/v1/chat/completions",
            json={
                "model": ENRICH_MODEL_ID,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=20.0,
        )

        if r.status_code == 429:
            logging.warning("Rate limited while enriching %s (429).", model_id)
            return {"summary": "", "recommended_use": ""}

        r.raise_for_status()
        data = r.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return parse_enrichment_text(model_id, content)
    except Exception as e:
        logging.warning("Enrichment failed for %s: %s", model_id, e)
        return {"summary": "", "recommended_use": ""}


async def enrich(models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich ALL missing models once, sequentially with delay.
    Uses a cache so each model is only asked once.
    """
    if not models:
        return []

    missing_ids = [m["id"] for m in models if m["id"] not in enriched_by_model]

    if missing_ids:
        logging.info("Enriching %d new models this cycle", len(missing_ids))
        async with httpx.AsyncClient() as client:
            for mid in missing_ids:
                info = await enrich_single(client, mid)
                enriched_by_model[mid] = info
                await asyncio.sleep(ENRICH_DELAY)
    else:
        logging.info("No new models to enrich this cycle")

    # Build enriched list aligned with current models
    enriched_list: List[Dict[str, Any]] = []
    for m in models:
        mid = m["id"]
        info = enriched_by_model.get(mid, {"summary": "", "recommended_use": ""})
        enriched_list.append({
            "model": mid,
            "summary": info.get("summary", ""),
            "recommended_use": info.get("recommended_use", ""),
        })

    return enriched_list


async def refresh_cache() -> None:
    """Refresh cache with latest model list plus enrichment."""
    logging.info("Refreshing cache")
    models = await gather_models()
    enriched = await enrich(models)
    cache["data"] = {"models": models, "enriched": enriched}
    cache["ts"] = time.time()
    logging.info(
        "Cache updated: %d models, %d enriched entries",
        len(models),
        len(enriched),
    )


@app.on_event("startup")
async def startup_event() -> None:
    """Initial fill + background loop."""
    await refresh_cache()

    async def loop():
        while True:
            await asyncio.sleep(600)
            await refresh_cache()

    asyncio.create_task(loop())


@app.get("/api/models")
async def api_models():
    """Return cached model data or refresh if expired."""
    if cache["data"] and (time.time() - cache["ts"] < CACHE_TTL):
        return JSONResponse(cache["data"])
    await refresh_cache()
    return JSONResponse(cache["data"])


# Serve ./static (index.html) at /
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
