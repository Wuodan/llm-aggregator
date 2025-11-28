from __future__ import annotations

import json


def _strip_markdown_fence(text: str) -> str:
    """Remove simple markdown fences like ```json ... ``` if present."""
    if len(text) >= 6 and text.startswith("```") and text.rstrip().endswith("```"):
        return text[3:-3].strip()

    if len(text) >= 10 and text.startswith("```json") and text.rstrip().endswith("```"):
        return text[7:-3].strip()

    return text.strip()


def _extract_json_list(text: str) -> list | None:
    """Best-effort extraction of a JSON object from a string.

    The brain *should* return a single JSON object, but in practice might wrap
    it in markdown fences or extra text. This attempts to find the first '{'
    and the last '}' and parse what's in between.
    """
    text = _strip_markdown_fence(text) if text is not None else ""
    if not text:
        return None

    # Fast path: maybe it's already pure JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except Exception:
        return None
