from __future__ import annotations

import logging

import aiohttp

from model_aggregator.config import get_settings


async def chat_completions(payload: dict[str, str | list[dict[str, str]] | float]) -> str|None:
    settings = get_settings()

    url = f"{settings.brain.host}:{settings.brain.port}/v1/chat/completions"

    headers:dict[str, str] = {
        "Content-Type": "application/json",
    }
    if settings.brain.use_bearer_model:
        # For brain backend: bearer token equals model id
        headers["Authorization"] = f"Bearer {settings.brain.id}"

    payload["model"] = settings.brain.id

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload,
                                    timeout=settings.timeout_enrich_models_seconds) as r:
                if r.status >= 400:
                    text = await r.text()
                    logging.error(
                        "Brain call failed with HTTP %s: %.200r",
                        r.status,
                        text,
                    )
                    return None

                try:
                    response = await r.json(content_type=None)
                except Exception:
                    text = await r.text()
                    logging.error("Brain returned non-JSON response: %.200r", text)
                    return None
    except Exception as e:
        if isinstance(e, TimeoutError):
            logging.warn("Brain request timeout error: %r", e)
        else:
            logging.error("Brain request general error: %r", e)
        return None

    # Parse OpenAI-style response
    try:
        content = (
            response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        if not isinstance(content, str) or not content.strip():
            logging.error("Brain response missing content field: %r", response)
            return None

        return content

    except Exception as e:
        logging.error("Brain response parsing error: %r", e)
        return None
