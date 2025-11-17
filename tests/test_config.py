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
          host: "http://brain"
          port: 8088
          id: "brain-model"
          api_key: null
          max_batch_size: 2
        time:
          fetch_models_interval: 5
          fetch_models_timeout: 3
          enrich_models_timeout: 7
          enrich_idle_sleep: 1
        providers:
          - base_url: http://p1
            port: 9000
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
    assert settings.providers[0].base_endpoint == "http://p1:9000"

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
