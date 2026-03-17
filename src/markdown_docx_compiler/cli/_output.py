"""Structured output helpers for the mdc CLI.

All CLI output flows through this module so ``--json`` produces a consistent
envelope and human-readable mode stays clean.
"""

from __future__ import annotations

import json
import sys
from typing import Any

_json_mode: bool = False


def set_json_mode(enabled: bool) -> None:
    global _json_mode
    _json_mode = enabled


def is_json_mode() -> bool:
    return _json_mode


def emit_success(command: str, data: dict[str, Any], human: str = "") -> None:
    """Print a success result.

    In JSON mode, prints an ``{"ok": true, ...}`` envelope.
    Otherwise prints *human* text (or nothing if empty).
    """
    if _json_mode:
        payload: dict[str, Any] = {"ok": True, "command": command, "data": data}
        print(json.dumps(payload, indent=2))
    elif human:
        print(human)


def emit_error(
    command: str,
    code: str,
    message: str,
    hint: str,
    context: dict[str, Any] | None = None,
    exit_code: int = 1,
) -> None:
    """Print a structured error and raise SystemExit.

    In JSON mode, the error goes to stdout as an ``{"ok": false, ...}``
    envelope.  In human mode it goes to stderr with a hint line.
    """
    if _json_mode:
        error_obj: dict[str, Any] = {"code": code, "message": message, "hint": hint}
        if context:
            error_obj["context"] = context
        payload: dict[str, Any] = {"ok": False, "command": command, "error": error_obj}
        print(json.dumps(payload, indent=2))
    else:
        print(f"Error: {message}", file=sys.stderr)
        if hint:
            print(f"Hint: {hint}", file=sys.stderr)
    raise SystemExit(exit_code)
