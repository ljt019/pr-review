"""Small helpers for extracting arguments from ToolExecutionMessage.arguments."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Union


def as_dict(arguments: Union[str, Dict[str, Any], None]) -> Dict[str, Any]:
    """Normalize arguments to a dict, parsing JSON strings if needed."""
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            return json.loads(arguments)
        except Exception:
            return {}
    return {}


def get_arg(
    arguments: Union[str, Dict[str, Any], None], keys: Iterable[str], default: Any = ""
) -> Any:
    """Return the first present key from arguments, else default.

    Example: get_arg(msg.arguments, ["path", "directory", "dir"], ".")
    """
    data = as_dict(arguments)
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default
