from __future__ import annotations

from llm_aggregator.services.enrich_model._extract_json_object import _extract_json_list


def test_extract_json_object_handles_wrapped_and_plain_json():
    wrapped = "```\n{\"foo\": 1}\n```"
    assert _extract_json_list(wrapped) == {"foo": 1}

    plain = '{"bar": "baz"}'
    assert _extract_json_list(plain) == {"bar": "baz"}


def test_extract_json_object_handles_wrapped_list():
    wrapped_list = "```\n{\n  \"id\": \"deepseek\",\n  \"provider\": \"Ollama\"\n}\n```"
    assert _extract_json_list(wrapped_list) == {
        "id": "deepseek",
        "provider": "Ollama",
    }


def test_extract_json_object_rejects_missing_json():
    assert _extract_json_list("no json here") is None
    assert _extract_json_list("") is None
    assert _extract_json_list('{"broken": }') is None
