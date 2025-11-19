from __future__ import annotations

import pytest

from llm_aggregator.model_info_sources import build_sources_from_config
from llm_aggregator.models import ModelInfoSourceConfig


def test_build_sources_from_config_success():
    configs = [
        ModelInfoSourceConfig(name="Alpha Source", url_template="https://alpha/{model_id}"),
        ModelInfoSourceConfig(name="Beta Source", url_template="https://beta/{model_id}/info"),
    ]

    sources = build_sources_from_config(configs)
    assert len(sources) == 2
    assert sources[0].provider_label == "Alpha Source"
    assert sources[1].provider_label == "Beta Source"
    assert sources[0].build_url("model-one") == "https://alpha/model-one"
    assert sources[1].key != sources[0].key


def test_build_sources_requires_placeholder():
    configs = [ModelInfoSourceConfig(name="Broken", url_template="https://alpha/model")]

    with pytest.raises(ValueError):
        build_sources_from_config(configs)


def test_build_sources_rejects_duplicate_names():
    configs = [
        ModelInfoSourceConfig(name="Same Name", url_template="https://alpha/{model_id}"),
        ModelInfoSourceConfig(name="Same Name", url_template="https://beta/{model_id}"),
    ]

    with pytest.raises(ValueError):
        build_sources_from_config(configs)
