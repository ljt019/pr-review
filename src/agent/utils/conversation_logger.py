"""Logger for raw LLM conversations to markdown files."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from qwen_agent.llm.schema import Message

logger = logging.getLogger(__name__)


class ConversationLogger:
    """Logs raw conversations with the LLM to timestamped markdown files."""
    
    def __init__(self, enabled: bool = False, logs_dir: str = "logs"):
        """Initialize the conversation logger.
        
        Args:
            enabled: Whether logging is enabled
            logs_dir: Directory to store log files in
        """
        self.enabled = enabled
        self.logs_dir = Path(logs_dir)
        self.log_file: Optional[Path] = None
        
        if self.enabled:
            self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Set up the logging directory and file."""
        # Create logs directory if it doesn't exist
        self.logs_dir.mkdir(exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.logs_dir / f"log_{timestamp}.md"
        
        # Write header
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(f"# Sniff Agent Conversation Log\n\n")
            f.write(f"**Started:** {datetime.now().isoformat()}\n\n")
            f.write("---\n\n")
    
    def log_raw_responses(self, responses: List[Union[Message, dict]], step: int) -> None:
        """Log raw responses from the agent.
        
        Args:
            responses: List of raw response messages
            step: Step number in the conversation
        """
        if not self.enabled or not self.log_file:
            return
            
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"## Step {step} - Raw Responses ({len(responses)} messages)\n\n")
                f.write(f"**Timestamp:** {datetime.now().isoformat()}\n\n")
                
                for i, response in enumerate(responses):
                    f.write(f"### Message {i + 1}\n\n")
                    
                    # Convert to dict for consistent logging
                    if hasattr(response, '__dict__'):
                        # Message object - extract relevant fields
                        msg_dict = {
                            "role": getattr(response, "role", None),
                            "content": getattr(response, "content", None),
                            "function_call": getattr(response, "function_call", None),
                            "name": getattr(response, "name", None),
                        }
                        # Remove None values
                        msg_dict = {k: v for k, v in msg_dict.items() if v is not None}
                    else:
                        # Already a dict
                        msg_dict = response
                    
                    # Format as JSON for readability
                    f.write("```json\n")
                    f.write(json.dumps(msg_dict, indent=2, ensure_ascii=False))
                    f.write("\n```\n\n")
                
                f.write("---\n\n")
                
        except Exception as e:
            logger.error(f"Failed to log raw responses: {e}")
    
    def log_tool_call(self, tool_name: str, arguments: str, reasoning: Optional[str] = None) -> None:
        """Log a tool call being made.
        
        Args:
            tool_name: Name of the tool being called
            arguments: Arguments passed to the tool
            reasoning: Optional reasoning from the agent
        """
        if not self.enabled or not self.log_file:
            return
            
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"### 🔧 Tool Call: {tool_name}\n\n")
                f.write(f"**Timestamp:** {datetime.now().isoformat()}\n\n")
                
                if reasoning:
                    f.write(f"**Reasoning:** {reasoning}\n\n")
                
                f.write("**Arguments:**\n```json\n")
                try:
                    # Try to format as pretty JSON
                    args_dict = json.loads(arguments)
                    f.write(json.dumps(args_dict, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    # Fall back to raw string if not valid JSON
                    f.write(arguments)
                f.write("\n```\n\n")
                
        except Exception as e:
            logger.error(f"Failed to log tool call: {e}")
    
    def log_tool_result(self, tool_name: str, result: str) -> None:
        """Log a tool result.
        
        Args:
            tool_name: Name of the tool that was executed
            result: Result returned by the tool
        """
        if not self.enabled or not self.log_file:
            return
            
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"### ✅ Tool Result: {tool_name}\n\n")
                f.write(f"**Timestamp:** {datetime.now().isoformat()}\n\n")
                
                # Truncate very long results for readability
                display_result = result
                if len(result) > 5000:
                    display_result = result[:5000] + f"\n\n... (truncated, full result was {len(result)} characters)"
                
                f.write("**Result:**\n```\n")
                f.write(display_result)
                f.write("\n```\n\n")
                
        except Exception as e:
            logger.error(f"Failed to log tool result: {e}")
    
    def log_streaming_content(self, content: str, is_complete: bool = False) -> None:
        """Log streaming assistant content.
        
        Args:
            content: The content being streamed
            is_complete: Whether this is the final content
        """
        if not self.enabled or not self.log_file:
            return
            
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                if is_complete:
                    f.write(f"### 💭 Final Assistant Response\n\n")
                    f.write(f"**Timestamp:** {datetime.now().isoformat()}\n\n")
                    f.write(f"**Content:**\n{content}\n\n")
                    f.write("---\n\n")
                
        except Exception as e:
            logger.error(f"Failed to log streaming content: {e}")
    
    def log_session_end(self) -> None:
        """Log the end of the conversation session."""
        if not self.enabled or not self.log_file:
            return
            
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"## Session Ended\n\n")
                f.write(f"**Timestamp:** {datetime.now().isoformat()}\n\n")
                
        except Exception as e:
            logger.error(f"Failed to log session end: {e}")