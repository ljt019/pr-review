"""Message type definitions for agent-TUI communication."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import json
from abc import ABC, abstractmethod


class MessageType(Enum):
    """Enumeration of all message types."""
    TOOL_EXECUTION = "tool_execution"
    STREAM_START = "stream_start"
    STREAM_CHUNK = "stream_chunk"
    STREAM_END = "stream_end"
    BUG_REPORT = "bug_report"


@dataclass
class AgentMessage(ABC):
    """Base class for all agent messages."""
    
    message_id: str
    timestamp: float
    
    @property
    @abstractmethod
    def message_type(self) -> MessageType:
        """Return the message type."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize message to dictionary."""
        result = {
            "message_type": self.message_type.value,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
        }
        # Add all dataclass fields except message_type (handled above)
        for field_name in self.__dataclass_fields__:
            if field_name not in ("message_id", "timestamp"):
                result[field_name] = getattr(self, field_name)
        return result
    
    def to_json(self) -> str:
        """Serialize message to JSON string."""
        return json.dumps(self.to_dict())


@dataclass 
class ToolExecutionMessage(AgentMessage):
    """Message representing a complete tool execution (call + result)."""
    
    tool_name: str
    arguments: Dict[str, Any]
    reasoning: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    success: bool = True
    execution_time_ms: Optional[int] = None
    
    @property
    def message_type(self) -> MessageType:
        return MessageType.TOOL_EXECUTION


@dataclass
class StreamStartMessage(AgentMessage):
    """Indicates a new streaming message is starting."""
    
    content_type: str = "text"  # "text", "analysis", "report"
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def message_type(self) -> MessageType:
        return MessageType.STREAM_START


@dataclass
class StreamChunkMessage(AgentMessage):
    """A chunk of content in a streaming message."""
    
    content: str
    chunk_index: int = 0
    is_partial: bool = True
    
    @property
    def message_type(self) -> MessageType:
        return MessageType.STREAM_CHUNK


@dataclass
class StreamEndMessage(AgentMessage):
    """Indicates the current streaming message is complete."""
    
    total_chunks: int = 0
    final_content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def message_type(self) -> MessageType:
        return MessageType.STREAM_END






@dataclass
class BugReportMessage(AgentMessage):
    """Message containing a complete bug report in JSON format."""
    
    report_data: Dict[str, Any]
    files_analyzed: int = 0
    
    @property
    def message_type(self) -> MessageType:
        return MessageType.BUG_REPORT
    
    @property
    def summary(self) -> str:
        """Get the summary from the report data."""
        return self.report_data.get("summary", "Bug analysis complete")
    
    @property
    def bugs(self) -> List[Dict[str, Any]]:
        """Get the bugs list from the report data."""
        return self.report_data.get("bugs", [])
    
    @property
    def bug_count(self) -> int:
        """Get the total number of bugs found."""
        return len(self.bugs)


