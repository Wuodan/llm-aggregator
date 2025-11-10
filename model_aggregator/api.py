import asyncio
import logging
import os
import time
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import CACHE_TTL
from .model_sources import gather_models
from .brain_client import enrich_models

app = FastAPI()

# Simple in-memory cache:
# {
#   "data": {
#       "models": [...],
#       "enriched": [...]
#   },
#   "ts": <epoch_seconds>
# }
cache: Dict[str, Any] = {"data": None, "ts": 0.0}


async def refresh_cache() -> None:
    """Refresh the full cache in one go (models + one brain call)."""
    logging.info("Refreshing /api/models cache (models + brain in one shot)")
    models = await gather_models()
    enriched = await enrich_models(models)

    # Map enriched info by model id for convenient merging
    enriched_by_id = {
        e.get("model"): e for e in enriched.get("enriched", []) if isinstance(e, dict)
    }

    merged_enriched: List[Dict[str, Any]] = []
    for m in models:
        mid = m.get("id")
        if not mid:
            continue
        extra = enriched_by_id.get(mid, {})
        merged_enriched.append(
            {
                "model": mid,
                "server_port": m.get("server_port"),
                "summary": extra.get("summary", ""),
                "types": extra.get("types", []),
                "recommended_use": extra.get("recommended_use", ""),
                "priority": extra.get("priority", 5),
            }
        )

    cache["data"] = {
        "models": models,
        "enriched": merged_enriched,
    }
    cache["ts"] = time.time()
    logging.info(
        "Cache updated: %d models, %d enriched",
        len(models),
        sum(1 for e in merged_enriched if e.get("summary") or e.get("recommended_use")),
    )


@app.on_event("startup")
async def on_startup() -> None:
    # Build an initial snapshot so first request is fast & meaningful.
    await refresh_cache()


@app.get("/api/models")
async def api_models():
    """Return cached model + enrichment data.

    - If TTL expired, refresh synchronously for now.
    - All brain logic is encapsulated and only called once per refresh.
    """
    if not cache["data"] or (time.time() - cache["ts"] > CACHE_TTL):
        await refresh_cache()
    return JSONResponse(cache["data"])


# Serve ./static (index.html etc.) at /
# Expect the static directory relative to this file's directory
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")
