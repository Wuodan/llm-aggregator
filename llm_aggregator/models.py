from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class BrainConfig:
    """Configuration for the enrichment (brain) LLM endpoint."""

    base_url: str
    # The model-id
    id: str
    api_key: str | None = None
    max_batch_size: int = 1


@dataclass(frozen=True)
class TimeConfig:
    # Values by default in seconds
    fetch_models_interval: int = 60
    fetch_models_timeout: int = 10
    enrich_models_timeout: int = 60
    enrich_idle_sleep: int = 5


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for a single OpenAI-compatible provider."""

    base_url: str  # public/external URL exposed via API responses
    internal_base_url: str | None = field(default=None)

    def __post_init__(self):
        # If not explicitly set, default to base_url
        if self.internal_base_url is None:
            object.__setattr__(self, "internal_base_url", self.base_url)

    @classmethod
    def from_api_dict(cls, raw: Dict[str, Any]) -> ProviderConfig | None:
        base_url = raw.get("base_url")
        internal_base_url = raw.get("internal_base_url")

        if not isinstance(base_url, str) or not isinstance(internal_base_url, str):
            return None

        return cls(base_url=base_url, internal_base_url=internal_base_url)


@dataclass(frozen=True)
class ModelKey:
    """Stable identifier for a model in this system.

    We currently key by (base_url, model-id), which is sufficient as long as
    each base_url exposes a unique model ID namespace.
    """

    provider: ProviderConfig
    id: str

    def to_api_dict(self) -> Dict[str, Any]:
        """Return the shape expected in the public /api/models 'models' list."""
        return {
            "id": self.id,
            "base_url": self.provider.base_url,
            "internal_base_url": self.provider.internal_base_url,
        }

    @classmethod
    def from_api_dict(cls, raw: Dict[str, Any]) -> ModelKey | None:
        provider_config = ProviderConfig.from_api_dict(raw)
        model_id = raw.get("id")

        if not isinstance(provider_config, ProviderConfig) or not isinstance(model_id, str):
            return None

        return cls(
            provider=provider_config,
            id=model_id,
        )


@dataclass
class ModelInfo:
    """Represents a model discovered from a provider.

    Attributes:
        key:   Unique ModelKey (provider config + model id).
        raw:   Original /v1/models entry merged with provider information.
    """

    key: ModelKey
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_api_dict(self) -> Dict[str, Any]:
        base = self.key.to_api_dict()
        return {**self.raw, **base}


@dataclass
class EnrichedModel:
    """Enriched metadata for a model.

    This is produced by the brain LLM based on one or more ModelInfo entries.
    """

    key: ModelKey
    enriched: Dict[str, Any] | None = None

    def to_api_dict(self) -> Dict[str, Any]:
        base = self.key.to_api_dict()
        enriched = self.enriched or {}

        # First take enriched, then override with base on conflicts
        data = {**enriched, **base}

        # Drop a few internal keys
        filtered_keys = {"internal_base_url"}
        data = {k: v for k, v in data.items() if k not in filtered_keys}

        return data

