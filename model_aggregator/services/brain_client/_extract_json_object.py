from __future__ import annotations

import json


def _extract_json_object(text: str):
    """Best-effort extraction of a JSON object from a string.

    The brain *should* return a single JSON object, but in practice might wrap
    it in markdown fences or extra text. This attempts to find the first '{'
    and the last '}' and parse what's in between.
    """
    text = text.strip()
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
