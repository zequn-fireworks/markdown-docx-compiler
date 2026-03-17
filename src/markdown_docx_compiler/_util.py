"""Shared coercion helpers for config parsing."""

from __future__ import annotations

from typing import Any


def as_str(value: Any) -> str | None:
    return str(value) if isinstance(value, (str, int, float)) and value != "" else None


def as_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def as_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.lower().strip()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return None


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_list_of_str(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    return [str(item) for item in value]
