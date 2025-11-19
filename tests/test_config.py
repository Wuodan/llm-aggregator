from __future__ import annotations

import textwrap

import pytest

from llm_aggregator import config as config_module
from llm_aggregator.config import CONFIG_ENV_VAR


def test_settings_load_from_custom_yaml(tmp_path, monkeypatch):
    cfg = textwrap.dedent(
        """
        host: "1.2.3.4"
        port: 1234
        brain:
          base_url: "http://brain:8088/v1"
          id: "brain-model"
          api_key: null
          max_batch_size: 2
        time:
          fetch_models_interval: 5
          fetch_models_timeout: 3
          enrich_models_timeout: 7
          enrich_idle_sleep: 1
        providers:
          - base_url: https://public-p1.example/v1
            internal_base_url: http://p1:9000/v1
          - base_url: https://public-p2.example/v1
        """
    ).strip()
    path = tmp_path / "test-config.yaml"
    path.write_text(cfg)

    monkeypatch.setenv(CONFIG_ENV_VAR, str(path))
    config_module._settings = None

    settings = config_module.get_settings()
    assert settings.host == "1.2.3.4"
    assert settings.fetch_models_interval == 5
    assert settings.fetch_models_timeout == 3
    assert settings.enrich_models_timeout == 7
    assert settings.brain.base_url == "http://brain:8088/v1"
    assert settings.brain.id == "brain-model"
    assert settings.brain.api_key is None
    assert settings.log_level == "INFO"
    assert settings.log_format is None
    assert settings.providers[0].base_url == "https://public-p1.example/v1"
    assert settings.providers[0].internal_base_url == "http://p1:9000/v1"
    # Defaults to base_url when not provided
    assert settings.providers[1].base_url == "https://public-p2.example/v1"
    assert settings.providers[1].internal_base_url == "https://public-p2.example/v1"

    # Cached object is reused to avoid re-parsing.
    assert config_module.get_settings() is settings


def test_missing_config_env_var_raises(monkeypatch):
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)
    config_module._settings = None
    try:
        with pytest.raises(RuntimeError):
            config_module.get_settings()
    finally:
        config_module._settings = None


def test_missing_config_file_raises(monkeypatch):
    monkeypatch.setenv(CONFIG_ENV_VAR, "/tmp/does-not-exist-config.yaml")
    config_module._settings = None
    try:
        with pytest.raises(FileNotFoundError):
            config_module.get_settings()
    finally:
        config_module._settings = None
