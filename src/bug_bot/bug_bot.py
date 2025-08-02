import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Union, List

from dotenv import load_dotenv

# MUST modify settings BEFORE importing Assistant to avoid import-time binding
from qwen_agent import settings

# ruff: noqa: E402
settings.MAX_LLM_CALL_PER_RUN = 500

from qwen_agent.agents import Assistant
from qwen_agent.llm.schema import Message

from bug_bot.docker.bot_container import BotContainer
from bug_bot.response_saver import save_response_with_summary

# ruff: noqa: F401
from bug_bot.tools import cat, glob, grep, load_prompt, ls, run_in_container, todo
from paths import PROJECT_ROOT

load_dotenv()

logger = logging.getLogger(__name__)


class ModelOptions(Enum):
    QWEN3_480B_A35B_CODER = "qwen/qwen3-coder"
    QWEN3_235B_A22B_INSTRUCT = "qwen/qwen3-235b-a22b-2507"
    QWEN3_30B_A3B_INSTRUCT = "qwen/qwen3-30b-a3b-instruct-2507"


@dataclass
class ToolCallMessage:
    """Message representing a tool being called by the agent."""
    tool_name: str
    arguments: str
    reasoning: str | None = None  # Assistant's message before the tool call


@dataclass  
class ToolResultMessage:
    """Message representing the result of a tool execution."""
    tool_name: str
    result: str


@dataclass
class BugReportMessage:
    """Message containing the final bug report from the agent."""
    content: str
    is_final: bool = False  # True when this is the last message


# Union type for all message types
BotMessage = Union[ToolCallMessage, ToolResultMessage, BugReportMessage]


class BugBot:
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
        self.container = BotContainer(zipped_codebase)
        self.container.start()
        self._wait_for_workspace_ready()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._cleanup()

    def run(self, save_response: bool = False) -> str | None:
        self.messages.append({"role": "user", "content": load_prompt("starting_query")})

        last_assistant_content: str | None = None

        try:
            for responses in self.agent.run(messages=self.messages):
                if not responses:
                    continue
                content = self._extract_last_assistant_content(responses)
                if content:
                    last_assistant_content = content

            if save_response and last_assistant_content:
                saved_paths = save_response_with_summary(
                    last_assistant_content, PROJECT_ROOT
                )
                if saved_paths:
                    # replace with logger if you switched to logging
                    print(f"Response saved to: {saved_paths['response']}")
                    summary = saved_paths.get("summary")
                    if summary:
                        print(f"Summary saved to: {summary}")

            return last_assistant_content
        finally:
            # Ensure we don't accumulate messages across runs
            self.messages = []

    def run_streaming(self):
        """Run the agent and yield clean message types as they're generated.
        
        Yields:
            BotMessage: Either ToolCallMessage, ToolResultMessage, or BugReportMessage
        """
        self.messages.append({"role": "user", "content": load_prompt("starting_query")})
        
        try:
            last_yielded_count = 0
            
            for responses in self.agent.run(messages=self.messages):
                if not responses:
                    continue
                
                # Process only new messages since last yield
                new_messages = responses[last_yielded_count:]
                last_yielded_count = len(responses)
                
                for msg in new_messages:
                    bot_message = self._convert_to_bot_message(msg)
                    if bot_message:
                        yield bot_message
                        
        finally:
            self.messages = []
    
    def _convert_to_bot_message(self, msg: Message | dict) -> BotMessage | None:
        """Convert a qwen_agent Message to our clean message types."""
        # Get fields - handle both Message objects and dicts
        role = msg.role if hasattr(msg, 'role') else msg.get('role')
        content = msg.content if hasattr(msg, 'content') else msg.get('content')
        function_call = msg.function_call if hasattr(msg, 'function_call') else msg.get('function_call')
        name = msg.name if hasattr(msg, 'name') else msg.get('name')
        
        # Assistant role - check for function_call first
        if role == "assistant":
            if function_call:
                # Has function_call = ToolCallMessage
                fc_name = function_call.name if hasattr(function_call, 'name') else function_call.get('name')
                fc_args = function_call.arguments if hasattr(function_call, 'arguments') else function_call.get('arguments')
                return ToolCallMessage(
                    tool_name=fc_name,
                    arguments=fc_args,
                    reasoning=content if content else None
                )
            elif content:
                # No function_call but has content = BugReportMessage
                return BugReportMessage(content=content)
            else:
                # No function_call and no content = error
                raise ValueError(f"Assistant message with no function_call or content: {msg}")
        
        # Function role = ToolResultMessage
        elif role == "function":
            if not content:
                raise ValueError(f"Function message with no content: {msg}")
            return ToolResultMessage(
                tool_name=name or "unknown",
                result=content
            )
        
        # Ignore other roles (system, user)
        return None
    
    def _is_final_response(self, responses: List[Message | dict]) -> bool:
        """Check if the last message is the final response (no more tool calls)."""
        if not responses:
            return False
        last_msg = responses[-1]
        
        # Handle both Message objects and dicts
        role = last_msg.role if hasattr(last_msg, 'role') else last_msg.get('role')
        function_call = last_msg.function_call if hasattr(last_msg, 'function_call') else last_msg.get('function_call')
        content = last_msg.content if hasattr(last_msg, 'content') else last_msg.get('content')
        
        return (role == "assistant" and 
                not function_call and 
                bool(content))

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
