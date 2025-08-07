"""Event bus for clean communication between agent and UI components."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EventType(Enum):
    """Types of events that can be published."""
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    MESSAGE_STREAM_STARTED = "message_stream_started"
    MESSAGE_TOKEN_RECEIVED = "message_token_received"
    MESSAGE_STREAM_ENDED = "message_stream_ended"
    TODO_STATE_UPDATED = "todo_state_updated"
    JSON_DETECTED = "json_detected"
    BUG_REPORT_READY = "bug_report_ready"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class Event:
    """Base event class."""
    type: EventType
    data: Dict[str, Any] = field(init=False)


@dataclass
class ToolCallEvent(Event):
    """Event for tool call operations."""
    tool_name: str
    arguments: str
    call_id: str
    type: EventType

    def __post_init__(self):
        self.data = {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "call_id": self.call_id,
        }


@dataclass
class MessageStreamEvent(Event):
    """Event for message streaming operations."""
    content: str
    message_type: Optional[str] = None
    type: EventType

    def __post_init__(self):
        self.data = {"content": self.content, "message_type": self.message_type}


@dataclass
class TodoStateEvent(Event):
    """Event for todo state updates."""
    todos: List[dict]
    type: EventType = EventType.TODO_STATE_UPDATED

    def __post_init__(self):
        self.data = {"todos": self.todos}


@dataclass
class BugReportEvent(Event):
    """Event for bug report completion."""
    json_content: str
    type: EventType = EventType.BUG_REPORT_READY

    def __post_init__(self):
        self.data = {"json_content": self.json_content}


@dataclass
class ErrorEvent(Event):
    """Event for errors."""
    error_message: str
    type: EventType = EventType.ERROR_OCCURRED

    def __post_init__(self):
        self.data = {"error_message": self.error_message}