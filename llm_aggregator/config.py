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

from .models import ProviderConfig, BrainConfig, TimeConfig

CONFIG_ENV_VAR = "LLM_AGGREGATOR_CONFIG"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


class Settings(BaseSettings):
    brain: BrainConfig
    time: TimeConfig
    providers: List[ProviderConfig]

    model_config = SettingsConfigDict(extra="forbid")

    @property
    def fetch_models_interval(self) -> int:
        return self.time.fetch_models_interval

    @property
    def fetch_models_timeout(self) -> int:
        return self.time.fetch_models_timeout

    @property
    def enrich_models_timeout(self) -> int:
        return self.time.enrich_models_timeout

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
