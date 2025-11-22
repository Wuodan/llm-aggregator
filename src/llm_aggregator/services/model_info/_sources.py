from __future__ import annotations

from llm_aggregator.config import get_settings
from llm_aggregator.model_info_sources import (
    WebsiteSource,
    build_sources_from_config,
)


def get_website_sources() -> tuple[WebsiteSource, ...]:
    settings = get_settings()
    return build_sources_from_config(settings.model_info_sources)
