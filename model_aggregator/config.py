from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import os

import yaml

from .models import ProviderConfig, EnrichmentConfig


CONFIG_ENV_VAR = "LLM_AGGREGATOR_CONFIG"
# Default: project_root/config.yaml (project_root contains the model_aggregator package)
DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "config.yaml"
)


@dataclass
class Settings:
    """Typed application settings loaded from config.yaml.

    All runtime behavior (providers, TTLs, enrichment) should be driven from here.
    """

    marvin_host: str
    providers: List[ProviderConfig]
    cache_ttl_seconds: int
    refresh_interval_seconds: int
    enrichment: EnrichmentConfig
    timeout_fetch_models_seconds: int
    timeout_enrich_models_seconds: int


_settings: Optional[Settings] = None


def _load_yaml(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a mapping at top-level: {path}")
    return data


def _parse_settings(raw: dict) -> Settings:
    marvin_host = raw.get("marvin_host")
    if not marvin_host or not isinstance(marvin_host, str):
        raise ValueError("'marvin_host' must be set to a non-empty string in config.yaml")

    providers_cfg = raw.get("providers") or []
    if not isinstance(providers_cfg, list) or not providers_cfg:
        raise ValueError("'providers' must be a non-empty list in config.yaml")

    providers: List[ProviderConfig] = []
    for item in providers_cfg:
        if not isinstance(item, dict):
            raise ValueError("Each providers[] entry must be a mapping")
        port = item.get("port")
        if not isinstance(port, int):
            raise ValueError("Each providers[] entry must define an integer 'port'")
        providers.append(ProviderConfig(base_url=marvin_host, port=port))

    cache_ttl_seconds = raw.get("cache_ttl_seconds", 300)
    if not isinstance(cache_ttl_seconds, int) or cache_ttl_seconds <= 0:
        raise ValueError("'cache_ttl_seconds' must be a positive integer")

    refresh_cfg = raw.get("refresh") or {}
    if not isinstance(refresh_cfg, dict):
        raise ValueError("'refresh' must be a mapping if provided")
    refresh_interval_seconds = refresh_cfg.get("interval_seconds", 60)
    if not isinstance(refresh_interval_seconds, int) or refresh_interval_seconds <= 0:
        raise ValueError("'refresh.interval_seconds' must be a positive integer")

    enrich_cfg = raw.get("enrichment") or {}
    if not isinstance(enrich_cfg, dict):
        raise ValueError("'enrichment' must be a mapping in config.yaml")

    model_id = enrich_cfg.get("model_id")
    if not model_id or not isinstance(model_id, str):
        raise ValueError("'enrichment.model_id' must be set to a non-empty string")

    enrich_port = enrich_cfg.get("port")
    if not isinstance(enrich_port, int):
        raise ValueError("'enrichment.port' must be set to an integer port number")

    use_bearer = bool(enrich_cfg.get("use_bearer_model_id", True))
    max_batch_size = enrich_cfg.get("max_batch_size", 5)
    if not isinstance(max_batch_size, int) or max_batch_size <= 0:
        raise ValueError("'enrichment.max_batch_size' must be a positive integer")

    timeout_cfg = raw.get("timeout") or {}
    if not isinstance(timeout_cfg, dict):
        raise ValueError("'timeout' must be a mapping if provided")
    timeout_fetch_models_seconds = timeout_cfg.get("fetch_models_seconds", 10)
    if not isinstance(timeout_fetch_models_seconds, int) or timeout_fetch_models_seconds <= 0:
        raise ValueError("'timeout.fetch_models_seconds' must be a positive integer")
    timeout_enrich_models_seconds = timeout_cfg.get("enrich_models_seconds", 60)
    if not isinstance(timeout_enrich_models_seconds, int) or timeout_enrich_models_seconds <= 0:
        raise ValueError("'timeout.enrich_models_seconds' must be a positive integer")

    enrichment = EnrichmentConfig(
        model_id=model_id,
        port=enrich_port,
        use_bearer_model_id=use_bearer,
        max_batch_size=max_batch_size,
    )

    return Settings(
        marvin_host=marvin_host,
        providers=providers,
        cache_ttl_seconds=cache_ttl_seconds,
        refresh_interval_seconds=refresh_interval_seconds,
        enrichment=enrichment,
        timeout_fetch_models_seconds=timeout_fetch_models_seconds,
        timeout_enrich_models_seconds=timeout_enrich_models_seconds,
    )


def load_settings(path: Optional[Path] = None) -> Settings:
    """Load settings from YAML once.

    If LLM_AGGREGATOR_CONFIG is set, its path wins over the default.
    """
    global _settings
    if _settings is not None:
        return _settings

    cfg_path: Path
    if path is not None:
        cfg_path = path
    else:
        env_path = os.getenv(CONFIG_ENV_VAR)
        cfg_path = Path(env_path) if env_path else DEFAULT_CONFIG_PATH

    raw = _load_yaml(cfg_path)
    _settings = _parse_settings(raw)
    return _settings


def get_settings() -> Settings:
    """Public accessor for the singleton Settings instance."""
    return load_settings()
