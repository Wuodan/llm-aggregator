from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


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
        """Return the full base endpoint (e.g. "http://host:8080")."""
        return f"{self.base_url}:{self.port}"


@dataclass(frozen=True)
class EnrichmentConfig:
    """Configuration for the enrichment (brain) LLM endpoint."""

    model_id: str
    port: int
    use_bearer_model_id: bool = True
    max_batch_size: int = 15


@dataclass(frozen=True)
class ModelKey:
    """Stable identifier for a model in this system.

    We currently key by (server_port, model_id), which is sufficient as long as
    each port exposes a unique model ID namespace.
    """

    server_port: int
    model_id: str

    @property
    def api_model(self) -> str:
        """Return the raw model id used in API payloads."""
        return self.model_id


@dataclass
class ModelInfo:
    """Represents a model discovered from a provider.

    Attributes:
        key:   Unique ModelKey (port + model id).
        raw:   Original /v1/models entry merged with server_port information.
    """

    key: ModelKey
    raw: Dict[str, Any]

    def to_api_dict(self) -> Dict[str, Any]:
        """Return the shape expected in the public /api/models 'models' list.

        This keeps the external contract compatible with the existing frontend.
        """
        # Ensure id + server_port are present at top-level.
        data = dict(self.raw)
        data.setdefault("id", self.key.model_id)
        data.setdefault("server_port", self.key.server_port)
        return data


@dataclass
class EnrichedModel:
    """Enriched metadata for a model.

    This is produced by the brain LLM based on one or more ModelInfo entries.
    """

    key: ModelKey
    summary: str = ""
    types: List[str] = field(default_factory=list)
    recommended_use: str = ""
    priority: int = 5

    def to_api_dict(self) -> Dict[str, Any]:
        """Return the shape expected in the public /api/models 'enriched' list."""
        return {
            "model": self.key.model_id,
            "server_port": self.key.server_port,
            "summary": self.summary,
            "types": list(self.types),
            "recommended_use": self.recommended_use,
            "priority": int(self.priority),
        }
