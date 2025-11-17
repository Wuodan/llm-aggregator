from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from llm_aggregator import config as config_module
from llm_aggregator.config import CONFIG_ENV_VAR

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
