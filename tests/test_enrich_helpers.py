from __future__ import annotations

import asyncio

from llm_aggregator.models import ModelInfo, ModelKey, ProviderConfig
from llm_aggregator.services.enrich_model._extract_json_object import _extract_json_object
from llm_aggregator.services.enrich_model._map_enrich_result import _map_enrich_result


def test_extract_json_object_handles_wrapped_and_plain_json():
    wrapped = "```json\n{\"foo\": 1}\n```"
    assert _extract_json_object(wrapped) == {"foo": 1}

    plain = '{"bar": "baz"}'
    assert _extract_json_object(plain) == {"bar": "baz"}


def test_extract_json_object_rejects_missing_json():
    assert _extract_json_object("no json here") is None
    assert _extract_json_object("") is None
    assert _extract_json_object('{"broken": }') is None


def test_map_enrich_result_filters_invalid_entries_and_copies_payload():
    async def _run():
        p1 = ProviderConfig(base_url="https://p1.example/v1", internal_base_url="http://p1:8000/v1")
        p2 = ProviderConfig(base_url="https://p2.example/v1", internal_base_url="http://p2:8000/v1")
        k1 = ModelKey(provider=p1, id="alpha")
        k2 = ModelKey(provider=p2, id="beta")
        model_infos = {
            k1: ModelInfo(key=k1),
            k2: ModelInfo(key=k2),
        }

        enriched_payload = [
            {
                "id": "alpha",
                "base_url": p1.base_url,
                "internal_base_url": p1.internal_base_url,
                "summary": "Alpha",
            },
            {
                "id": "beta",
                "base_url": p2.base_url,
                "internal_base_url": p2.internal_base_url,
                "summary": "Beta",
            },
            {"id": "missing", "internal_base_url": "http://unknown"},  # filtered: not in keys
            {"id": "beta", "internal_base_url": 123},  # filtered: wrong type
            "oops",
        ]

        result = await _map_enrich_result(model_infos, enriched_payload)
        assert [item.key for item in result] == [k1, k2]
        assert result[0].enriched["summary"] == "Alpha"
        assert result[0].enriched is not enriched_payload[0]

    asyncio.run(_run())
