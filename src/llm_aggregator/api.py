from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Awaitable, Callable

import psutil
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, get_settings
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


_RAM_TOTAL_BYTES = psutil.virtual_memory().total


@app.get("/v1/models")
async def list_models():
    """Return the OpenAI ListModelsResponse with aggregator metadata.

    Each entry follows the schema from doc/general/OpenAI-models-response.md and
    adds a ``meta`` object that mirrors provider and enrichment metadata.
    """

    snapshot = await store.get_snapshot()
    return JSONResponse({"object": "list", "data": snapshot})


@app.get("/api/stats")
def get_stats():
    return JSONResponse(list(stats_history))


@app.get("/api/ram")
def get_ram_total():
    return JSONResponse({"total_bytes": _RAM_TOTAL_BYTES})


@app.post("/api/clear")
async def clear_data():
    """Clear/wipe all model-related data (adapt to your ModelStore API)."""
    await tasks_manager.restart()
    return JSONResponse({"status": "cleared"})


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


def _configure_ui_routes(app: FastAPI, settings: Settings) -> None:
    ui = settings.ui
    if not ui.static_enabled:
        return

    static_root = ui.resolve_static_root()
    app.mount("/static", NoCacheStaticFiles(directory=static_root), name="static")

    cache_bust = ui.custom_static_path is None
    handler = _build_index_handler(static_root, cache_bust=cache_bust, version=settings.version)
    app.add_api_route("/", handler, response_class=HTMLResponse)


def _build_index_handler(
    static_root: Path, *, cache_bust: bool, version: str
) -> Callable[[Request], Awaitable[HTMLResponse]]:
    async def serve_index(request: Request) -> HTMLResponse:
        html_path = static_root / "index.html"
        html = html_path.read_text(encoding="utf-8")

        api_base = str(request.base_url).rstrip("/")
        html = html.replace(
            'id="apiBaseScript" data-api-base=""',
            f'id="apiBaseScript" data-api-base="{api_base}"',
            1,
        )

        # Cache-bust main.js based on settings.version
        if cache_bust:
            html = html.replace(
                'src="/static/main.js"',
                f'src="/static/main.js?v={version}"',
                1,
            )

        return HTMLResponse(html)

    return serve_index


_configure_ui_routes(app, settings)
