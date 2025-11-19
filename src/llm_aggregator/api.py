from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .services.model_store import ModelStore
from .services.stats_collector import stats_history
from .services.tasks import BackgroundTasksManager

# Initialize core components once at import time
settings = get_settings()
store = ModelStore()
tasks_manager = BackgroundTasksManager(store)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Application lifespan: start/stop background tasks around FastAPI."""
    logging.info("Starting LLM Aggregator app")
    await tasks_manager.start()
    try:
        yield
    finally:
        await tasks_manager.stop()
        logging.info("LLM Aggregator app stopped")


app = FastAPI(lifespan=lifespan)


@app.get("/v1/models")
async def list_models():
    """Return the OpenAI ListModelsResponse with aggregator metadata.

    Each entry follows the schema from doc/general/OpenAI-models-response.md and
    adds an ``llm_aggregator`` object that mirrors our enrichment snapshot.
    """

    snapshot = await store.get_snapshot()
    return JSONResponse({"object": "list", "data": snapshot})


@app.get("/api/stats")
def get_stats():
    return JSONResponse(list(stats_history))


@app.post("/api/clear")
async def clear_data():
    """Clear/wipe all model-related data (adapt to your ModelStore API)."""
    await tasks_manager.restart()
    return JSONResponse({"status": "cleared"})


# ---- Static frontend ----

static_dir = Path(os.path.dirname(__file__)) / "static"


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


# Serve assets at /static (main.js, css, etc.) with no-cache
app.mount("/static", NoCacheStaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Serve index.html and inject dynamic API base URL for the frontend JS."""
    html_path = static_dir / "index.html"
    html = html_path.read_text(encoding="utf-8")

    api_base = str(request.base_url).rstrip("/")

    html = html.replace(
        'id="apiBaseScript" data-api-base=""',
        f'id="apiBaseScript" data-api-base="{api_base}"',
        1,
    )

    # Cache-bust main.js based on settings.version
    html = html.replace(
        'src="/static/main.js"',
        f'src="/static/main.js?v={settings.version}"',
        1,
    )

    return HTMLResponse(html)
