from __future__ import annotations

import logging

import aiohttp
from aiohttp import ClientResponseError, ClientError

from llm_aggregator.config import get_settings


async def chat_completions(payload: dict[str, str | list[dict[str, str]] | float]) -> str|None:
    settings = get_settings()

    url = f"{settings.brain.base_url}/chat/completions"

    headers:dict[str, str] = {
        "Content-Type": "application/json",
    }
    if settings.brain.api_key:
        # For brain backend: bearer token equals model id
        headers["Authorization"] = f"Bearer {settings.brain.api_key}"

    payload["model"] = settings.brain.id

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload,
                                    timeout=settings.enrich_models_timeout) as r:
                if r.status >= 400:
                    r.raise_for_status()
                    return ""

                try:
                    response = await r.json(content_type=None)
                except ClientError:
                    text = await r.text()
                    logging.error("Brain returned non-JSON response: %.200r", text)
                    return ""
    except ClientResponseError as e:
        logging.error(
            "Brain call failed with HTTP %s: %.200r",
            e.status,
            e.message,
        )
        return ""
    except TimeoutError as e:
        logging.warning("Brain request timeout error: %r", e)
        return ""
    except Exception as e:
        logging.error("Brain request general error: %r", e)
        return ""

    # Parse OpenAI-style response
    try:
        content = (
            response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        if not isinstance(content, str) or not content.strip():
            logging.error("Brain response missing content field: %r", response)
            return ""

        return content

    except Exception as e:
        logging.error("Brain response parsing error: %r", e)
        return ""
