from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)

from .models import ProviderConfig, EnrichmentConfig


CONFIG_ENV_VAR = "LLM_AGGREGATOR_CONFIG"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


class Settings(BaseSettings):
    """Typed application settings loaded from YAML + env.

    Behavior:
    - If $LLM_AGGREGATOR_CONFIG is set → use that YAML file.
    - Else use project_root/config.yaml.
    - Env vars can override fields (standard pydantic-settings behavior).
    """

    marvin_host: str
    providers: List[ProviderConfig]
    cache_ttl_seconds: int = 300
    refresh_interval_seconds: int = 60
    enrichment: EnrichmentConfig
    timeout_fetch_models_seconds: int = 10
    timeout_enrich_models_seconds: int = 60

    model_config = SettingsConfigDict(extra="forbid")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type["Settings"],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        cfg_path_env = os.getenv(CONFIG_ENV_VAR)
        yaml_path = Path(cfg_path_env) if cfg_path_env else DEFAULT_CONFIG_PATH

        return (
            init_settings,  # kwargs passed when instantiating Settings(...)
            env_settings,   # environment variables
            YamlConfigSettingsSource(settings_cls, yaml_file=yaml_path),
            dotenv_settings,
            file_secret_settings,
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
