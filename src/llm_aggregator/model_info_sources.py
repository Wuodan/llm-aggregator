from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from .models import ModelInfoSourceConfig


@dataclass(frozen=True)
class WebsiteSource:
    key: str
    provider_label: str
    url_template: str

    def build_url(self, model_id: str) -> str:
        return self.url_template.format(model_id=model_id)


def build_sources_from_config(
    configs: Sequence[ModelInfoSourceConfig] | None,
) -> tuple[WebsiteSource, ...]:
    if not configs:
        return ()

    sources: list[WebsiteSource] = []
    seen_keys: set[str] = set()

    for cfg in configs:
        label = (cfg.name or "").strip()
        template = (cfg.url_template or "").strip()

        if not label:
            raise ValueError("model_info_sources entry missing 'name'")
        if not template:
            raise ValueError(f"model_info_sources entry '{label}' missing 'url_template'")
        if "{model_id}" not in template:
            raise ValueError(f"'url_template' for '{label}' must include '{{model_id}}'")
        try:
            template.format(model_id="example-model")
        except KeyError as exc:
            raise ValueError(
                f"'url_template' for '{label}' has unsupported placeholder: {exc}"
            ) from exc

        key = _slugify(label)
        if key in seen_keys:
            raise ValueError(
                f"Duplicate model_info source key '{key}'. Provide unique names."
            )
        seen_keys.add(key)

        sources.append(
            WebsiteSource(
                key=key,
                provider_label=label,
                url_template=template,
            )
        )

    return tuple(sources)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise ValueError("model_info_sources name must contain alphanumeric characters")
    return slug


__all__ = ["WebsiteSource", "build_sources_from_config"]
