from __future__ import annotations

import os
from datetime import datetime, timezone
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

from .model_info_sources import build_sources_from_config
from .models import (
    ProviderConfig,
    BrainConfig,
    TimeConfig,
    ModelInfoSourceConfig,
    UIConfig,
)

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
    model_info_sources: List[ModelInfoSourceConfig]
    logger_overrides: Dict[str, str | int] = Field(
        default_factory=_default_logger_overrides
    )
    ui: UIConfig = Field(default_factory=UIConfig)

    try:
        version: str = pkg_version("llm_aggregator")
    except PackageNotFoundError:
        version: str = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')

    model_config = SettingsConfigDict(extra="forbid")

    def model_post_init(self, __context: Any) -> None:
        # Ensure logger_overrides always has a dict (even when YAML sets null)
        if self.logger_overrides is None:
            object.__setattr__(self, "logger_overrides", {})
        # Validate model_info_sources immediately so startup fails fast on bad config.
        build_sources_from_config(self.model_info_sources)
        _validate_ui_config(self.ui)

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


def _validate_ui_config(ui: UIConfig) -> None:
    if not ui.static_enabled:
        return

    static_root = ui.resolve_static_root()
    _ensure_readable_dir(static_root, "UI static directory")

    index_path = static_root / "index.html"
    _ensure_readable_file(index_path, "UI index.html")


def _ensure_readable_dir(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} {path} does not exist")
    if not path.is_dir():
        raise NotADirectoryError(f"{label} {path} is not a directory")
    if not os.access(path, os.R_OK):
        raise PermissionError(f"{label} {path} is not readable")


def _ensure_readable_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} {path} does not exist")
    if not path.is_file():
        raise FileNotFoundError(f"{label} {path} is not a file")
    if not os.access(path, os.R_OK):
        raise PermissionError(f"{label} {path} is not readable")
