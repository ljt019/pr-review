"""Shared file tracking utility for analyzing which files were examined."""

import json
from typing import Set, Optional

from agent.messages import ToolResultMessage, ToolCallMessage


class FileTracker:
    """Tracks files analyzed during agent execution."""
    
    def __init__(self):
        self.analyzed_files: Set[str] = set()
        self._pending_tool_calls: dict = {}  # Store tool calls by ID
    
    def track_tool_call(self, message: ToolCallMessage) -> None:
        """Track a tool call for later result matching."""
        if message.tool_name == "cat":
            # Store the call for later matching with result
            key = message.call_id or f"cat_{len(self._pending_tool_calls)}"
            self._pending_tool_calls[key] = message
    
    def track_tool_result(self, message: ToolResultMessage) -> None:
        """Track successful cat tool results to count analyzed files."""
        if message.tool_name == "cat" and not message.result.startswith("Error:"):
            # Try to find the corresponding tool call
            file_path = self._extract_file_path_from_result(message)
            if file_path:
                self.analyzed_files.add(file_path)
            else:
                # Fallback: Just count unique results as files, since we're seeing many cat calls
                # This is a simplified approach but better than 0
                result_hash = hash(message.result[:100])  # Use first 100 chars as identifier
                self.analyzed_files.add(f"file_{result_hash}")
    
    def _extract_file_path_from_result(self, message: ToolResultMessage) -> Optional[str]:
        """Extract file path from tool result message."""
        # Look for matching tool call first
        for call_id, tool_call in self._pending_tool_calls.items():
            if tool_call.tool_name == message.tool_name:
                # Parse the arguments to get file path
                try:
                    args = json.loads(tool_call.arguments)
                    file_path = args.get("filePath")
                    if file_path:
                        # Remove this call from pending since we matched it
                        del self._pending_tool_calls[call_id]
                        return file_path
                except (json.JSONDecodeError, KeyError):
                    pass
                break
        
        # Fallback: try to extract from result content
        # Cat results contain file content, we can try to infer from that
        # This is less reliable but better than nothing
        return None
    
    def get_analyzed_files(self) -> Set[str]:
        """Get set of all files that were successfully analyzed."""
        return self.analyzed_files.copy()
    
    def get_files_count(self) -> int:
        """Get count of analyzed files."""
        return len(self.analyzed_files)
    
    def reset(self) -> None:
        """Reset tracking state."""
        self.analyzed_files.clear()
        self._pending_tool_calls.clear()