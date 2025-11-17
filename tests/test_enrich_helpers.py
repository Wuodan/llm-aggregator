from __future__ import annotations

import asyncio

from llm_aggregator.models import ModelKey
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
        k1 = ModelKey(port=1, id="alpha")
        k2 = ModelKey(port=2, id="beta")
        keys = {
            (k1.id, k1.port): k1,
            (k2.id, k2.port): k2,
        }

        enriched_payload = [
            {"id": "alpha", "port": 1, "summary": "Alpha"},
            {"id": "beta", "port": 2, "summary": "Beta"},
            {"id": "missing", "port": 999},  # filtered: not in keys
            {"id": "beta", "port": "wrong"},  # filtered: wrong type
            "oops",
        ]

        result = await _map_enrich_result(keys, enriched_payload)
        assert [item.key for item in result] == [k1, k2]
        assert result[0].enriched["summary"] == "Alpha"
        assert result[0].enriched is not enriched_payload[0]

    asyncio.run(_run())
