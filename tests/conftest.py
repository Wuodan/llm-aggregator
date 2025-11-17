from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

config_module = importlib.import_module("llm_aggregator.config")
CONFIG_ENV_VAR = config_module.CONFIG_ENV_VAR


DEFAULT_TEST_CONFIG = ROOT / "config.yaml"
os.environ.setdefault(CONFIG_ENV_VAR, str(DEFAULT_TEST_CONFIG))


@pytest.fixture(autouse=True)
def _reset_cached_settings(monkeypatch):
    """Provide isolated config state for every test."""
    monkeypatch.setenv(CONFIG_ENV_VAR, str(DEFAULT_TEST_CONFIG))
    config_module._settings = None
    try:
        yield
    finally:
        config_module._settings = None
