#!/usr/bin/env python3
import asyncio
import json
import time

import aiohttp
import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

MARVIN_HOST = "http://10.7.2.100"
PORTS = [8080, 8090, 11434]
CACHE_TTL = 300  # seconds

app = FastAPI()
cache = {"data": None, "ts": 0}


async def fetch_models(session, port: int):
    url = f"{MARVIN_HOST}:{port}/v1/models"
    try:
        async with session.get(url, timeout=10) as r:
            j = await r.json()
            models = j.get("data", j)
    except Exception:
        models = []
    for m in models:
        m["server_port"] = port
    return models


async def gather_models():
    async with aiohttp.ClientSession() as s:
        results = await asyncio.gather(*[fetch_models(s, p) for p in PORTS])
    all_models = []
    for group in results:
        all_models.extend(group)
    return all_models


async def enrich(models):
    """Use one local model to generate JSON with metadata & recommendations."""
    if not models:
        return []

    model_ids = [m["id"] for m in models]
    prompt = (
        "You are a model catalog assistant.\n"
        "For each of these model IDs, infer or look up (e.g. via Hugging Face) "
        "their type and best use. Return ONLY a JSON list, no text around it.\n"
        "Each entry: {\"model\":\"id\",\"summary\":\"one-line description\","
        "\"recommended_use\":\"short suggestion\"}.\n\n"
        f"Models: {json.dumps(model_ids)}"
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as c:
            r = await c.post(
                f"{MARVIN_HOST}:8080/v1/chat/completions",
                json={
                    "model": "NexaAI/gemma-3n-E2B-it-4bit-MLX",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                },
            )
        content = r.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        if isinstance(data, list):
            return data
    except Exception:
        pass

    return []


async def refresh_cache():
    models = await gather_models()
    enriched = await enrich(models)
    cache["data"] = {"models": models, "enriched": enriched}
    cache["ts"] = time.time()


@app.on_event("startup")
async def startup_event():
    async def loop():
        while True:
            await refresh_cache()
            await asyncio.sleep(600)  # refresh every 10 minutes

    asyncio.create_task(loop())
    await refresh_cache()  # initial fill


@app.get("/api/models")
async def api_models():
    if cache["data"] and time.time() - cache["ts"] < CACHE_TTL:
        return JSONResponse(cache["data"])
    await refresh_cache()
    return JSONResponse(cache["data"])


app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8888)
