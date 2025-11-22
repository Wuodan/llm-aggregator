from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
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
class BrainPromptsConfig:
    """Prompts used for the enrichment brain."""

    system: str
    user: str
    model_info_prefix_template: str = ""

    def __post_init__(self) -> None:
        if not self.system.strip():
            raise ValueError("brain_prompts.system must not be empty")
        if not self.user.strip():
            raise ValueError("brain_prompts.user must not be empty")


@dataclass(frozen=True)
class TimeConfig:
    # Values by default in seconds
    fetch_models_interval: int = 60
    fetch_models_timeout: int = 10
    enrich_models_timeout: int = 60
    enrich_idle_sleep: int = 5
    website_markdown_cache_ttl: int = 7 * 24 * 60 * 60


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for a single OpenAI-compatible provider."""

    base_url: str  # public/external URL exposed via API responses
    internal_base_url: str | None = field(default=None)
    api_key: str | None = field(default=None, repr=False, compare=True)
    files_size_gatherer: "FilesSizeGathererConfig | None" = field(default=None)

    def __post_init__(self):
        # If not explicitly set, default to base_url
        if self.internal_base_url is None:
            object.__setattr__(self, "internal_base_url", self.base_url)
        if self.files_size_gatherer is not None and not isinstance(
            self.files_size_gatherer, FilesSizeGathererConfig
        ):
            raise TypeError("files_size_gatherer must be a FilesSizeGathererConfig or None")

    @classmethod
    def from_api_dict(cls, raw: Dict[str, Any]) -> ProviderConfig | None:
        base_url = raw.get("base_url")
        internal_base_url = raw.get("internal_base_url")
        api_key = raw.get("api_key")

        if not isinstance(base_url, str):
            return None

        if internal_base_url is not None and not isinstance(internal_base_url, str):
            return None

        if api_key is not None and not isinstance(api_key, str):
            return None

        return cls(base_url=base_url, internal_base_url=internal_base_url, api_key=api_key)


@dataclass(frozen=True)
class ModelKey:
    """Stable identifier for a model in this system."""

    provider: ProviderConfig
    id: str

    def to_api_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "base_url": self.provider.base_url,
            "internal_base_url": self.provider.internal_base_url,
        }


@dataclass(frozen=True)
class ModelInfoSourceConfig:
    """Configuration for an external website that hosts model metadata."""

    name: str
    url_template: str


def _default_builtin_static_path() -> Path:
    return Path(__file__).resolve().parent / "static"


@dataclass(frozen=True)
class UIConfig:
    """Configuration for serving built-in or custom static assets."""

    static_enabled: bool = True
    custom_static_path: Path | None = None

    def __post_init__(self) -> None:
        custom_path = self._normalize_path(self.custom_static_path)
        object.__setattr__(self, "custom_static_path", custom_path)

    @property
    def builtin_static_path(self) -> Path:
        return _default_builtin_static_path()

    def resolve_static_root(self) -> Path:
        return self.custom_static_path or self.builtin_static_path

    @staticmethod
    def _normalize_path(value: Path | str | None) -> Path | None:
        if value is None:
            return None

        string_value = str(value).strip()
        if not string_value:
            return None

        return Path(string_value)


class ModelMeta(dict):
    """Metadata for a model, allowing arbitrary provider/enriched fields."""

    @property
    def base_url(self) -> str:
        return str(self.get("base_url") or "")


class Model(dict):
    """Model object mirroring provider /v1/models payload plus provider config."""

    def __init__(self, provider: ProviderConfig, payload: Dict[str, Any]) -> None:
        model_id = payload.get("id")
        if model_id is None:
            raise ValueError("Model payload must include id")

        super().__init__(payload)
        self.provider = provider
        self["id"] = str(model_id)

        raw_meta = payload.get("meta")
        meta: ModelMeta = ModelMeta(raw_meta) if isinstance(raw_meta, dict) else ModelMeta()
        meta["base_url"] = provider.base_url
        self["meta"] = meta

    @property
    def id(self) -> str:
        return str(self["id"])

    @property
    def meta(self) -> ModelMeta:
        return self["meta"]

    @meta.setter
    def meta(self, value: ModelMeta) -> None:
        self["meta"] = value

    def to_public_dict(self) -> Dict[str, Any]:
        """Return a shallow copy suitable for API/brain payloads."""
        return dict(self)


def make_model(provider: ProviderConfig, payload: Dict[str, Any]) -> Model:
    """Create a Model from a provider /v1/models payload."""
    return Model(provider, payload)


def model_key(model: Model) -> ModelKey:
    return ModelKey(provider=model.provider, id=model.id)


def public_model_dict(model: Model) -> Dict[str, Any]:
    """Return a shallow copy without provider for API/brain payloads."""
    return model.to_public_dict()


@dataclass(frozen=True)
class FilesSizeGathererConfig:
    """Configuration for model file size gathering."""

    path: str
    base_path: str
    timeout_seconds: int | None = None

    def __post_init__(self) -> None:
        path = (self.path or "").strip()
        if not path:
            raise ValueError("files_size_gatherer.path must be set")
        object.__setattr__(self, "path", path)

        base_path = (self.base_path or "").strip()
        if not base_path:
            raise ValueError("files_size_gatherer.base_path must be set")
        object.__setattr__(self, "base_path", base_path)

        timeout = self.timeout_seconds
        if timeout is None:
            object.__setattr__(self, "timeout_seconds", 15)
        elif timeout <= 0:
            raise ValueError("files_size_gatherer.timeout_seconds must be positive when set")
