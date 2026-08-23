"""Provider-neutral token usage parsing for JSONL worker output."""

from __future__ import annotations

import json
from typing import Any


def _optional_int(value: Any) -> int | None:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def extract_usage_jsonl(text: str) -> dict[str, int | None]:
    """Return the final terminal usage record, or explicit missing values."""
    candidates: list[dict[str, Any]] = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(event, dict)
            and event.get("type") == "turn.completed"
            and isinstance(event.get("usage"), dict)
        ):
            candidates.append(event["usage"])
    if not candidates:
        return {
            "input_tokens": None,
            "cached_input_tokens": None,
            "uncached_input_tokens": None,
            "output_tokens": None,
            "reasoning_tokens": None,
            "total_tokens": None,
            "uncached_input_plus_output": None,
        }
    usage = candidates[-1]
    input_tokens = _optional_int(usage.get("input_tokens"))
    output_tokens = _optional_int(usage.get("output_tokens"))
    total_tokens = _optional_int(usage.get("total_tokens"))
    details = usage.get("input_tokens_details") if isinstance(usage.get("input_tokens_details"), dict) else {}
    output_details = usage.get("output_tokens_details") if isinstance(usage.get("output_tokens_details"), dict) else {}
    cached = _optional_int(details.get("cached_tokens", usage.get("cached_input_tokens")))
    reasoning = _optional_int(
        output_details.get(
            "reasoning_tokens",
            usage.get("reasoning_output_tokens", usage.get("reasoning_tokens")),
        )
    )
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    uncached = input_tokens - cached if input_tokens is not None and cached is not None else None
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached,
        "uncached_input_tokens": uncached,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning,
        "total_tokens": total_tokens,
        "uncached_input_plus_output": uncached + output_tokens if uncached is not None and output_tokens is not None else None,
    }
