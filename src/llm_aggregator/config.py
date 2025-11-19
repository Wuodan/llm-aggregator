from __future__ import annotations

import os
from datetime import datetime, UTC
from importlib.metadata import version as pkg_version, PackageNotFoundError
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)

from .models import ProviderConfig, BrainConfig, TimeConfig

CONFIG_ENV_VAR = "LLM_AGGREGATOR_CONFIG"


def _default_logger_overrides() -> Dict[str, str | int]:
    return {}


class Settings(BaseSettings):
    host: str
    port: int
    log_level: str = "INFO"
    log_format: str | None = None
    brain: BrainConfig
    time: TimeConfig
    providers: List[ProviderConfig]
    logger_overrides: Dict[str, str | int] = Field(
        default_factory=_default_logger_overrides
    )

    try:
        version: str = pkg_version("llm_aggregator")
    except PackageNotFoundError:
        version: str = datetime.now(UTC).strftime('%Y%m%d%H%M%S')

    model_config = SettingsConfigDict(extra="forbid")

    def model_post_init(self, __context: Any) -> None:
        # Ensure logger_overrides always has a dict (even when YAML sets null)
        if self.logger_overrides is None:
            object.__setattr__(self, "logger_overrides", {})

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
        yaml_path = _resolve_config_path()

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


def _resolve_config_path() -> Path:
    cfg_path_env = os.getenv(CONFIG_ENV_VAR)
    if not cfg_path_env:
        raise RuntimeError(
            f"{CONFIG_ENV_VAR} is not set. Please point it to your config.yaml file."
        )

    yaml_path = Path(cfg_path_env).expanduser()
    if not yaml_path.is_file():
        raise FileNotFoundError(f"Config file {yaml_path} does not exist")
    return yaml_path
