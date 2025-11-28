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


def test_extract_json_object_handles_inline_and_json_fences():
    assert _extract_json_list("```{\"foo\": 1}```") == {"foo": 1}
    assert _extract_json_list("```json[{\"id\": \"facebook/detr-resnet-50\"}]```") == {
        "id": "facebook/detr-resnet-50"
    }
    wrapped_json = "```json\n[\n  {\"id\": \"facebook/detr-resnet-50\"}\n]\n```"
    assert _extract_json_list(wrapped_json) == {"id": "facebook/detr-resnet-50"}


def test_extract_json_object_rejects_missing_json():
    assert _extract_json_list("no json here") is None
    assert _extract_json_list("") is None
    assert _extract_json_list('{"broken": }') is None
