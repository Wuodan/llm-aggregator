from __future__ import annotations

from llm_aggregator.models import EnrichedModel, ModelInfo, ModelKey


def test_model_key_api_helpers():
    key = ModelKey(port=42, id="test-model")
    assert key.api_model == "test-model"
    assert key.to_api_dict() == {"id": "test-model", "port": 42}


def test_enriched_model_to_api_dict_merges_fields():
    key = ModelKey(port=1, id="alpha")
    enriched = EnrichedModel(key=key, enriched={"summary": "desc"})
    data = enriched.to_api_dict()
    assert data["summary"] == "desc"
    assert data["id"] == "alpha"
    assert data["port"] == 1


def test_model_info_to_api_dict_fills_missing_fields():
    key = ModelKey(port=2, id="beta")
    info = ModelInfo(key=key, raw={"name": "Beta"})

    api_dict = info.to_api_dict()
    assert api_dict["id"] == "beta"
    assert api_dict["port"] == 2
    assert api_dict["name"] == "Beta"
