from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from extract2md import fetch_to_markdown

from llm_aggregator.config import get_settings
from llm_aggregator.models import Model
from ._cache import WebsiteInfoCache
from ._sources import WebsiteSource, get_website_sources


_CACHE = WebsiteInfoCache(
    ttl_seconds=get_settings().time.website_markdown_cache_ttl
)


@dataclass(frozen=True)
class WebsiteMarkdown:
    source: WebsiteSource
    model_id: str
    markdown: str


async def fetch_model_markdown(model: Model) -> list[WebsiteMarkdown]:
    """Return markdown snippets from known websites for the given model."""
    normalized_id = _normalize_model_id(model.key.id)
    sources = get_website_sources()
    tasks = [
        _get_markdown_for_source(source, normalized_id)
        for source in sources
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    snippets: list[WebsiteMarkdown] = []
    for source, result in zip(sources, results):
        if isinstance(result, Exception):
            logging.error(
                "Website fetch raised unexpected exception for %s at %s: %r",
                normalized_id,
                source.provider_label,
                result,
            )
            continue
        if result:
            snippets.append(
                WebsiteMarkdown(
                    source=source,
                    model_id=normalized_id,
                    markdown=result,
                )
            )
    return snippets


def _normalize_model_id(model_id: str) -> str:
    if ":" not in model_id:
        return model_id
    return model_id.split(":", 1)[0]


async def _get_markdown_for_source(source: WebsiteSource, model_id: str) -> str | None:
    hit, cached_value = await _CACHE.get(source.key, model_id)
    if hit:
        return cached_value

    markdown = await _download_markdown(source, model_id)
    await _CACHE.set(source.key, model_id, markdown)
    return markdown


async def _download_markdown(source: WebsiteSource, model_id: str) -> str | None:
    url = source.build_url(model_id)
    try:
        return await asyncio.to_thread(fetch_to_markdown, url)
    except Exception as exc:
        logging.debug("extract2md failed for %s: %r", url, exc)
    return None
