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
    """Return current models + enrichment snapshot."""
    snapshot = await store.get_snapshot()
    return JSONResponse({"models": snapshot})


@app.get("/api/stats")
def get_stats():
    return JSONResponse(list(stats_history))


@app.post("/api/clear")
async def clear_data():
    """Clear/wipe all model-related data (adapt to your ModelStore API)."""
    # Implement this in your ModelStore (e.g. reset caches, enrichment, etc.)
    if hasattr(store, "clear"):
        await store.clear()  # make clear() async; or remove await if sync
    return JSONResponse({"status": "cleared"})


# ---- Static frontend ----

static_dir = Path(os.path.dirname(__file__)) / "static"

# Serve assets at /static (main.js, css, etc.)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Serve index.html and inject dynamic API base URL for the frontend JS."""
    html_path = static_dir / "index.html"
    html = html_path.read_text(encoding="utf-8")

    # 1) If you add `api_base_url` to your config, that wins.
    api_base = getattr(settings, "api_base_url", None)

    # 2) Otherwise: build it from the incoming request (works behind proxy if Host is set)
    if not api_base:
        scheme = request.url.scheme
        host = request.headers.get("host") or f"{request.client.host}"
        api_base = f"{scheme}://{host}"

    # Fill the placeholder in index.html
    html = html.replace(
        'id="apiBaseScript" data-api-base=""',
        f'id="apiBaseScript" data-api-base="{api_base}"',
        1,
    )
    return HTMLResponse(html)
