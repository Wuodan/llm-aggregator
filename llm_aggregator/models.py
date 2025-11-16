from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class BrainConfig:
    """Configuration for the enrichment (brain) LLM endpoint."""

    host: str
    port: int
    # The model-id
    id: str
    api_key: str|None = None
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
    """Configuration for a single OpenAI-compatible provider.

    A provider is identified by its base URL and port. In the current setup
    all providers share the same host, but the dataclass does not assume this.
    """

    base_url: str
    port: int

    @property
    def base_endpoint(self) -> str:
        """Return the full base endpoint (e.g. "https://host:8080")."""
        return f"{self.base_url}:{self.port}"


@dataclass(frozen=True)
class ModelKey:
    """Stable identifier for a model in this system.

    We currently key by (port, model-id), which is sufficient as long as
    each port exposes a unique model ID namespace.
    """

    port: int
    # Model ID
    id: str

    @property
    def api_model(self) -> str:
        """Return the raw model id used in API payloads."""
        return self.id

    def to_api_dict(self) -> Dict[str, Any]:
        """Return the shape expected in the public /api/models 'models' list."""
        return {
            "id": self.id,
            "port": self.port,
        }


@dataclass
class ModelInfo:
    """Represents a model discovered from a provider.

    Attributes:
        key:   Unique ModelKey (port + model id).
        raw:   Original /v1/models entry merged with port information.
    """

    key: ModelKey
    raw: Dict[str, Any]

    def to_api_dict(self) -> Dict[str, Any]:
        """Return the shape expected in the public /api/models 'models' list.

        This keeps the external contract compatible with the existing frontend.
        """
        # Ensure id + port are present at top-level.
        data = dict(self.raw)
        data.setdefault("id", self.key.id)
        data.setdefault("port", self.key.port)
        return data


@dataclass
class EnrichedModel:
    """Enriched metadata for a model.

    This is produced by the brain LLM based on one or more ModelInfo entries.
    """

    key: ModelKey
    enriched: Dict[str, Any] | None = None

    def to_api_dict(self) -> Dict[str, Any]:
        """Return the shape expected in the public /api/models 'enriched' list."""
        base = self.key.to_api_dict()
        if self.enriched is not None:
                    base = {**base, **self.enriched}
        return base
