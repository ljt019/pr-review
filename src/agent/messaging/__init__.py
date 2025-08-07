"""Clean messaging system for agent communication."""

from .types import (
    AgentMessage,
    MessageType,
    ToolExecutionMessage,
    StreamStartMessage,
    StreamChunkMessage,
    StreamEndMessage,
    BugReportMessage,
)
from .sender import MessageSender
from .receiver import MessageReceiver

__all__ = [
    # Base types
    "AgentMessage",
    "MessageType",
    # Message types
    "ToolExecutionMessage",
    "StreamStartMessage",
    "StreamChunkMessage",
    "StreamEndMessage",
    "BugReportMessage",
    # Core classes
    "MessageSender",
    "MessageReceiver",
]