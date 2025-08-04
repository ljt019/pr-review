from dataclasses import dataclass
from typing import Union


@dataclass
class ToolCallMessage:
    """Message representing a tool being called by the agent."""

    tool_name: str
    arguments: str
    reasoning: str | None = None
    call_id: str | None = None  # Unique identifier for this tool call


@dataclass
class ToolResultMessage:
    """Message representing the result of a tool execution."""

    tool_name: str
    result: str


@dataclass
class MessageStart:
    """Indicates a new message is starting."""

    message_type: str  # "analysis" or "final_report"


@dataclass
class MessageToken:
    """A token/chunk being added to the current streaming message."""

    token: str


@dataclass
class MessageEnd:
    """Indicates the current streaming message is complete."""

    pass


@dataclass
class TodoStateMessage:
    """Message containing the current todo state from the bot."""

    todos: list[dict]  # List of todo items with content, status, priority, id


@dataclass
class BugReportMessage:
    """Message containing the bug analysis report from the assistant."""

    content: str


# Union type for all message types
BotMessage = Union[
    ToolCallMessage,
    ToolResultMessage,
    MessageStart,
    MessageToken,
    MessageEnd,
    TodoStateMessage,
    BugReportMessage,
]