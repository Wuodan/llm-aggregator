from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from llm_aggregator import config as config_module
from llm_aggregator.config import CONFIG_ENV_VAR

# Ensure the project package (llm_aggregator) is importable when running tests

@pytest.fixture(autouse=True)
def _reset_cached_settings(monkeypatch):
    """Provide isolated config state for every test."""
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)
    config_module._settings = None
    try:
        yield
    finally:
        config_module._settings = None
