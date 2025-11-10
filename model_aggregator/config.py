from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)

from .models import ProviderConfig, EnrichmentConfig

CONFIG_ENV_VAR = "LLM_AGGREGATOR_CONFIG"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


class RefreshConfig(BaseModel):
    interval_seconds: int = 60


class TimeoutConfig(BaseModel):
    fetch_models_seconds: int = 10
    enrich_models_seconds: int = 60


class Settings(BaseSettings):
    brain_host: str
    providers: List[ProviderConfig]
    cache_ttl_seconds: int = 300
    refresh: RefreshConfig = RefreshConfig()
    enrichment: EnrichmentConfig
    timeout: TimeoutConfig = TimeoutConfig()

    model_config = SettingsConfigDict(extra="forbid")

    @property
    def refresh_interval_seconds(self) -> int:
        return self.refresh.interval_seconds

    @property
    def timeout_fetch_models_seconds(self) -> int:
        return self.timeout.fetch_models_seconds

    @property
    def timeout_enrich_models_seconds(self) -> int:
        return self.timeout.enrich_models_seconds

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
            init_settings,
            env_settings,
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
