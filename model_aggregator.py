#!/usr/bin/env python3
import asyncio
import json
import logging
import time
import uuid

import aiohttp
import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

MARVIN_HOST = "http://10.7.2.100"
PORTS = [8080, 8090, 11434]
CACHE_TTL = 300  # seconds

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI()
cache = {"data": None, "ts": 0}


async def fetch_models(session, port: int):
    logging.info(f"Fetching models from port {port}")
    url = f"{MARVIN_HOST}:{port}/v1/models"
    try:
        async with session.get(url, timeout=10) as r:
            j = await r.json()
            models = j.get("data", j)
        logging.info(f"Successfully fetched {len(models)} models from port {port}")
    except Exception as e:
        logging.error(f"Failed to fetch models from port {port}: {e}")
        models = []

    if not isinstance(models, list):
        logging.error(f"Unexpected models format from port {port}: {type(models)}, using empty list")
        models = []
    for m in models:
        m["server_port"] = port
    return models


async def gather_models():
    async with aiohttp.ClientSession() as s:
        results = []
        for p in PORTS:
            result = await fetch_models(s, p)
            results.append(result)
    all_models = []
    for group in results:
        all_models.extend(group)
    logging.info(f"Gathered {len(all_models)} models from all ports")
    return all_models


async def enrich(models):
    """Use one local model to generate JSON with metadata & recommendations."""
    if not models:
        logging.info("No models to enrich")
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
                f"{MARVIN_HOST}:8090/v1/chat/completions",
                json={
                    "model": "NexaAI/gemma-3n-E2B-it-4bit-MLX",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                },
            )

        await asyncio.sleep(3)

        # Get body
        body_str = (await r.aread()).decode('utf-8', errors='ignore')

        # Log full response
        response_log = f"Status: {r.status_code}\nHeaders:\n{str(r.headers)}\n\nBody:\n{body_str}"
        filename = f"{uuid.uuid4()}_{int(time.time())}.txt"
        with open(filename, 'w') as f:
            f.write(response_log)
        logging.info(f"Logged enrich response to {filename}")

        if r.status_code != 200:
            logging.error(f"Enrichment failed with status {r.status_code}, see log file {filename}")
            return []

        j = json.loads(body_str)
        content = j["choices"][0]["message"]["content"]
        data = json.loads(content)
        if isinstance(data, list):
            logging.info(f"Successfully enriched {len(data)} models")
            return data
        else:
            logging.warning("Enrichment returned non-list data")
    except Exception as e:
        logging.error(f"Failed to enrich models: {e}")

    return []


async def refresh_cache():
    logging.info("Starting cache refresh")
    models = await gather_models()
    enriched = await enrich(models)
    cache["data"] = {"models": models, "enriched": enriched}
    cache["ts"] = time.time()
    logging.info(f"Cache refreshed with {len(models)} models and {len(enriched)} enriched entries")


@app.on_event("startup")
async def startup_event():
    logging.info("Application startup: starting background cache refresh loop")
    async def loop():
        while True:
            await refresh_cache()
            await asyncio.sleep(600)  # refresh every 10 minutes

    asyncio.create_task(loop())
    await refresh_cache()  # initial fill
    logging.info("Initial cache refresh completed on startup")


@app.get("/api/models")
async def api_models():
    elapsed = time.time() - cache["ts"] if cache["ts"] else float('inf')
    if cache["data"] and elapsed < CACHE_TTL:
        logging.info(f"Cache hit: serving data ({elapsed:.1f}s since refresh)")
        return JSONResponse(cache["data"])
    logging.info("Cache miss: refreshing cache")
    await refresh_cache()
    return JSONResponse(cache["data"])


app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8888)
