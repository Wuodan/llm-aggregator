from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .services.model_store import ModelStore
from .services.tasks import BackgroundTasksManager

# Initialize core components once at import time
settings = get_settings()
store = ModelStore()
tasks_manager = BackgroundTasksManager(store)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: start/stop background tasks around FastAPI."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logging.info("Starting LLM Aggregator app")
    await tasks_manager.start()
    try:
        yield
    finally:
        await tasks_manager.stop()
        logging.info("LLM Aggregator app stopped")


app = FastAPI(lifespan=lifespan)


@app.get("/api/models")
async def api_models():
    """Return current models + enrichment snapshot.

    This is a thin read-only view over the in-memory ModelStore.
    Background tasks keep the store up to date.
    """
    snapshot = await store.get_snapshot()
    return JSONResponse({"models": snapshot})


# Serve ./static (index.html etc.) at /
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
