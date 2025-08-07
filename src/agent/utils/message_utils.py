from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class FunctionCallData:
    """Normalized function call structure."""

    name: Optional[str] = None
    arguments: Optional[str] = None


@dataclass
class MessageData:
    """Normalized message structure to unify dicts and objects."""

    role: Optional[str] = None
    content: Optional[str] = None
    name: Optional[str] = None
    function_call: Optional[FunctionCallData] = None


def to_message_data(msg: Any) -> MessageData:
    """Convert a raw message (object or dict) into MessageData."""
    role = getattr(msg, "role", None) or (msg.get("role") if isinstance(msg, dict) else None)
    content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
    name = getattr(msg, "name", None) or (msg.get("name") if isinstance(msg, dict) else None)
    function_call = getattr(msg, "function_call", None) or (
        msg.get("function_call") if isinstance(msg, dict) else None
    )

    if function_call:
        fc = FunctionCallData(
            name=getattr(function_call, "name", None)
            or (function_call.get("name") if isinstance(function_call, dict) else None),
            arguments=getattr(function_call, "arguments", None)
            or (
                function_call.get("arguments")
                if isinstance(function_call, dict)
                else None
            ),
        )
    else:
        fc = None

    return MessageData(role=role, content=content, name=name, function_call=fc)

