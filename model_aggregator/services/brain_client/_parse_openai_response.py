from __future__ import annotations

import logging

from model_aggregator.services.brain_client._extract_json_object import _extract_json_object


def _parse_openai_response(response) -> list:
    # Parse OpenAI-style response
    try:
        content = (
            response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        if not isinstance(content, str) or not content.strip():
            logging.error("Brain response missing content field: %r", response)
            raise
    except Exception as e:
        logging.error("Brain response parsing error: %r", e)
        raise

    # Extract JSON from content (robust against minor wrapping)
    enriched_obj = _extract_json_object(content)
    if not isinstance(enriched_obj, dict):
        logging.error("Brain did not return a JSON object: %r", content)
        raise

    enriched_list = enriched_obj.get("enriched")
    if not isinstance(enriched_list, list):
        logging.error("Brain JSON missing 'enriched' list: %r", enriched_obj)
        raise
    return enriched_list
