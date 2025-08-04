"""Event bus for clean communication between agent and UI components."""

from dataclasses import dataclass
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
    data: Dict[str, Any]


@dataclass 
class ToolCallEvent(Event):
    """Event for tool call operations."""
    tool_name: str
    arguments: str
    call_id: str
    
    def __init__(self, event_type: EventType, tool_name: str, arguments: str, call_id: str):
        super().__init__(
            type=event_type,
            data={"tool_name": tool_name, "arguments": arguments, "call_id": call_id}
        )
        self.tool_name = tool_name
        self.arguments = arguments
        self.call_id = call_id


@dataclass
class MessageStreamEvent(Event):
    """Event for message streaming operations."""
    content: str
    message_type: Optional[str] = None
    
    def __init__(self, event_type: EventType, content: str, message_type: Optional[str] = None):
        super().__init__(
            type=event_type,
            data={"content": content, "message_type": message_type}
        )
        self.content = content
        self.message_type = message_type


@dataclass
class TodoStateEvent(Event):
    """Event for todo state updates."""
    todos: List[dict]
    
    def __init__(self, todos: List[dict]):
        super().__init__(
            type=EventType.TODO_STATE_UPDATED,
            data={"todos": todos}
        )
        self.todos = todos


@dataclass
class BugReportEvent(Event):
    """Event for bug report completion."""
    json_content: str
    
    def __init__(self, json_content: str):
        super().__init__(
            type=EventType.BUG_REPORT_READY,
            data={"json_content": json_content}
        )
        self.json_content = json_content


@dataclass
class ErrorEvent(Event):
    """Event for errors."""
    error_message: str
    
    def __init__(self, error_message: str):
        super().__init__(
            type=EventType.ERROR_OCCURRED,
            data={"error_message": error_message}
        )
        self.error_message = error_message