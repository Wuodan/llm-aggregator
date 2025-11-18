from __future__ import annotations

from llm_aggregator.models import EnrichedModel, ModelInfo, ModelKey, ProviderConfig


def test_enriched_model_to_api_dict_merges_fields():
    provider = ProviderConfig(
        base_url="https://public-a.example/v1",
        internal_base_url="http://provider-a:8000/v1",
    )
    key = ModelKey(provider=provider, id="alpha")
    enriched = EnrichedModel(key=key, enriched={"summary": "desc"})
    data = enriched.to_api_dict()
    assert data["summary"] == "desc"
    assert data["id"] == "alpha"
    assert data["base_url"] == "https://public-a.example/v1"
    assert "internal_base_url" not in data


def test_model_info_to_api_dict_fills_missing_fields():
    provider = ProviderConfig(base_url="https://public-b.example/v1")
    key = ModelKey(provider=provider, id="beta")
    info = ModelInfo(key=key, raw={"name": "Beta"})

    api_dict = info.to_api_dict()
    assert api_dict["id"] == "beta"
    assert api_dict["base_url"] == "https://public-b.example/v1"
    assert api_dict["internal_base_url"] == "https://public-b.example/v1"
    assert api_dict["name"] == "Beta"
