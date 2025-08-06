import logging
import os
from enum import Enum
from typing import List

from dotenv import load_dotenv

# MUST modify settings BEFORE importing Assistant to avoid import-time binding
from qwen_agent import settings

# ruff: noqa: E402
settings.MAX_LLM_CALL_PER_RUN = 500

from qwen_agent.agents import Assistant
from qwen_agent.llm.schema import Message

from agent.messages import (
    BotMessage,
    BugReportMessage,
    MessageEnd,
    MessageStart,
    MessageToken,
    TodoStateMessage,
    ToolCallMessage,
    ToolResultMessage,
)
from agent.utils.message_processor import MessageProcessor
from agent.sandbox import Sandbox
from agent.utils.response_saver import save_response_with_summary

# ruff: noqa: F401
from agent.tools import cat, glob, grep, load_prompt, ls, run_in_container, todowrite, todoread
from paths import PROJECT_ROOT

load_dotenv()

logger = logging.getLogger(__name__)


class ModelOptions(Enum):
    QWEN3_480B_A35B_CODER = "qwen/qwen3-coder"
    QWEN3_235B_A22B_INSTRUCT = "qwen/qwen3-235b-a22b-2507"
    QWEN3_30B_A3B_INSTRUCT = "qwen/qwen3-30b-a3b-instruct-2507"


class SniffAgent:
    def __init__(
        self,
        zipped_codebase: str,
        model_option: ModelOptions = ModelOptions.QWEN3_30B_A3B_INSTRUCT,
    ):
        llm_cfg = {
            "model": model_option.value,
            "model_server": "https://openrouter.ai/api/v1",
            "api_key": os.getenv("OPEN_ROUTER_API_KEY"),
            "generate_cfg": {"max_input_tokens": 100000},
        }

        system_instruction = load_prompt("system_prompt")
        tools = ["ls", "cat", "grep", "glob", "todo_write", "todo_read"]

        self.agent = Assistant(
            llm=llm_cfg,
            system_message=system_instruction,
            function_list=tools,
        )

        self.messages: list[dict] = []
        self.container = Sandbox(zipped_codebase)
        
        # Import file tracker
        from agent.utils.file_tracker import FileTracker
        self.file_tracker = FileTracker()
        self.container.start()
        self._wait_for_workspace_ready()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._cleanup()

    def __del__(self):
        """Ensure cleanup even if context manager isn't used."""
        self._cleanup()

    def run(self, save_response: bool = False) -> str | None:
        self.messages.append({"role": "user", "content": load_prompt("starting_query")})

        last_assistant_content: str | None = None

        try:
            for responses in self.agent.run(messages=self.messages):
                if not responses:
                    continue
                
                # Track tool calls and results for file counting
                self._track_tools_in_responses(responses)
                
                content = self._extract_last_assistant_content(responses)
                if content:
                    last_assistant_content = content

            if save_response and last_assistant_content:
                saved_paths = save_response_with_summary(
                    last_assistant_content, PROJECT_ROOT
                )
                if saved_paths:
                    # Response and summary saved successfully
                    pass

            # Inject files_analyzed count into JSON response if it's valid JSON
            if last_assistant_content:
                last_assistant_content = self._inject_files_analyzed(last_assistant_content)
            
            return last_assistant_content
        finally:
            # Ensure we don't accumulate messages across runs
            self.messages = []

    def _get_current_todo_state(self) -> list[dict]:
        """Get the current todo state from the tools."""
        try:
            # Import here to avoid circular imports
            from agent.utils.todo_manager import get_todo_manager
            
            todo_manager = get_todo_manager()
            todos = todo_manager.get_all_todos()

            ui_todos = []
            for todo in todos:
                ui_todo = {
                    "content": todo.content,
                    "status": todo.status,
                    "priority": "medium",  # Default priority
                    "id": todo.id,
                }
                ui_todos.append(ui_todo)

            return ui_todos
        except Exception as e:
            logger.warning(f"Failed to get todo state: {e}")
            return []

    def run_streaming(self):
        """Run the agent and yield streaming message events.

        Yields:
            BotMessage: Stream events for tool calls, message starts/tokens/ends
        """
        self.messages.append({"role": "user", "content": load_prompt("starting_query")})

        try:
            # Create message processor with todo callback
            processor = MessageProcessor(get_todo_state_callback=self._get_current_todo_state)
            
            logger.info("Starting agent.run() streaming...")
            
            # Delegate all processing to the message processor
            yield from processor.process_stream(self.agent.run(messages=self.messages))

        finally:
            self.messages = []

    def _convert_to_bot_message(self, msg: Message | dict) -> BotMessage | None:
        """Convert a qwen_agent Message to our clean message types."""
        # Get fields - handle both Message objects and dicts
        role = msg.role if hasattr(msg, "role") else msg.get("role")
        content = msg.content if hasattr(msg, "content") else msg.get("content")
        function_call = (
            msg.function_call
            if hasattr(msg, "function_call")
            else msg.get("function_call")
        )
        name = msg.name if hasattr(msg, "name") else msg.get("name")

        # Assistant role - check for function_call first
        if role == "assistant":
            if function_call:
                # Has function_call = ToolCallMessage
                fc_name = (
                    function_call.name
                    if hasattr(function_call, "name")
                    else function_call.get("name")
                )
                fc_args = (
                    function_call.arguments
                    if hasattr(function_call, "arguments")
                    else function_call.get("arguments")
                )
                return ToolCallMessage(
                    tool_name=fc_name,
                    arguments=fc_args,
                    reasoning=content if content else None,
                )
            elif content:
                # No function_call but has content = BugReportMessage
                return BugReportMessage(content=content)
            else:
                # No function_call and no content = error
                raise ValueError(
                    f"Assistant message with no function_call or content: {msg}"
                )

        # Function role = ToolResultMessage
        elif role == "function":
            if not content:
                raise ValueError(f"Function message with no content: {msg}")
            return ToolResultMessage(tool_name=name or "unknown", result=content)

        # Ignore other roles (system, user)
        return None

    def _is_final_response(self, responses: List[Message | dict]) -> bool:
        """Check if the last message is the final response (no more tool calls)."""
        if not responses:
            return False
        last_msg = responses[-1]

        # Handle both Message objects and dicts
        role = last_msg.role if hasattr(last_msg, "role") else last_msg.get("role")
        function_call = (
            last_msg.function_call
            if hasattr(last_msg, "function_call")
            else last_msg.get("function_call")
        )
        content = (
            last_msg.content
            if hasattr(last_msg, "content")
            else last_msg.get("content")
        )

        return role == "assistant" and not function_call and bool(content)

    def _cleanup(self):
        """Clean up resources, specifically the container"""
        if hasattr(self, "container"):
            try:
                self.container.stop()
            except Exception as exc:
                logger.warning("Failed to stop container: %s", exc)

    def _wait_for_workspace_ready(self, timeout: int = 15):
        """Block until the /workspace directory has at least one file."""
        from time import sleep
        from time import time as now

        start = now()
        while True:
            count_cmd = "find /workspace -maxdepth 2 -type f | head -1"
            result = run_in_container(count_cmd)
            if result and not result.startswith("Error:"):
                return
            if now() - start > timeout:
                logger.warning(
                    "Workspace still empty after %ss; continuing anyway", timeout
                )
                return
            sleep(0.5)

    def _extract_last_assistant_content(self, responses) -> str | None:
        if not responses:
            return None
        if not isinstance(responses, list):
            responses = [responses]

        last = responses[-1]
        if not isinstance(last, dict):
            return None
        if last.get("role") != "assistant":
            return None

        content = last.get("content")
        return content or None
    
    def _track_tools_in_responses(self, responses) -> None:
        """Track tool calls and results for file counting."""
        if not isinstance(responses, list):
            responses = [responses]
        
        for response in responses:
            if not isinstance(response, dict):
                continue
                
            role = response.get("role")
            
            # Track tool calls
            if role == "assistant":
                tool_calls = response.get("tool_calls", [])
                for tool_call in tool_calls:
                    if tool_call.get("function", {}).get("name") == "cat":
                        # Create a simple tool call message for tracking
                        from agent.messages import ToolCallMessage
                        call_msg = ToolCallMessage(
                            tool_name="cat",
                            arguments=tool_call.get("function", {}).get("arguments", ""),
                            call_id=tool_call.get("id")
                        )
                        self.file_tracker.track_tool_call(call_msg)
            
            # Track tool results
            elif role == "function":
                tool_name = response.get("name")
                content = response.get("content", "")
                if tool_name == "cat":
                    from agent.messages import ToolResultMessage
                    result_msg = ToolResultMessage(
                        tool_name=tool_name,
                        result=content
                    )
                    self.file_tracker.track_tool_result(result_msg)
    
    def _inject_files_analyzed(self, content: str) -> str:
        """Inject files_analyzed count into JSON response."""
        try:
            import json
            import re
            
            # Try to find JSON in the response (may be mixed with text)
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                data["files_analyzed"] = self.file_tracker.get_files_count()
                
                # Replace the JSON part in the original content
                updated_json = json.dumps(data, indent=2, ensure_ascii=False)
                return content.replace(json_str, updated_json)
            else:
                # Try parsing the entire content as JSON
                data = json.loads(content)
                data["files_analyzed"] = self.file_tracker.get_files_count()
                return json.dumps(data, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            # If it's not valid JSON, return as-is
            return content
