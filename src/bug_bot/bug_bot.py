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


# Union type for all message types
BotMessage = Union[ToolCallMessage, ToolResultMessage, MessageStart, MessageToken, MessageEnd, TodoStateMessage]


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

    def _get_current_todo_state(self) -> list[dict]:
        """Get the current todo state from the tools."""
        try:
            # Import here to avoid circular imports
            from bug_bot.tools.todo import _todos
            
            # Convert internal format to UI format
            ui_todos = []
            for todo in _todos:
                ui_todo = {
                    "content": todo.get("content", ""),
                    "status": "completed" if todo.get("status") == "complete" else 
                             "pending" if todo.get("status") == "incomplete" else "pending",
                    "priority": "medium",  # Default priority
                    "id": todo.get("id", "")
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
            last_yielded_count = 0
            last_assistant_content = ""
            current_message_started = False
            yielded_tool_calls = set()  # Track yielded tool calls by message index
            
            print("[DEBUG] Starting agent.run() streaming...")
            for responses in self.agent.run(messages=self.messages):
                if not responses:
                    continue
                
                print(f"[DEBUG] Processing {len(responses)} total messages")
                
                # Check for tool calls in assistant messages
                for i, msg in enumerate(responses):
                    # Handle both Message objects and dicts
                    role = getattr(msg, 'role', None) or msg.get('role')
                    function_call = getattr(msg, 'function_call', None) or msg.get('function_call')
                    content = getattr(msg, 'content', None) or msg.get('content')
                    
                    if role == "assistant" and function_call:
                        # Handle function_call being an object or dict
                        fc_name = getattr(function_call, 'name', None) or function_call.get('name')
                        fc_args = getattr(function_call, 'arguments', None) or function_call.get('arguments')
                        
                        print(f"[DEBUG] Message {i}: Tool={fc_name}, Args='{fc_args}'")
                        
                        # Only yield if we haven't yielded this message position before and args look complete
                        # Wait for complete JSON or very substantial partial content
                        args_ready = fc_args and (
                            fc_args.strip().endswith('}') or  # Complete JSON
                            (len(fc_args) > 20 and (  # Substantial partial content
                                ('"filePath":' in fc_args and '"' in fc_args[fc_args.find('"filePath":')+11:]) or  # filePath with value
                                ('"directory":' in fc_args and '"' in fc_args[fc_args.find('"directory":')+12:]) or  # directory with value
                                ('"pattern":' in fc_args and '"' in fc_args[fc_args.find('"pattern":')+10:]) or  # pattern with value
                                ('"command":' in fc_args and '"' in fc_args[fc_args.find('"command":')+10:])  # command with value
                            ))
                        )
                        if i not in yielded_tool_calls and args_ready:
                            # End any current streaming message first
                            if current_message_started:
                                yield MessageEnd()
                                current_message_started = False
                                last_assistant_content = ""
                            
                            print(f"[DEBUG] Yielding ToolCallMessage: {fc_name}({fc_args})")
                            yield ToolCallMessage(
                                tool_name=fc_name,
                                arguments=fc_args,
                                reasoning=content if content else None,
                                call_id=f"{fc_name}_{i}"
                            )
                            yielded_tool_calls.add(i)

                # Check for new function result messages
                new_messages = responses[last_yielded_count:]
                for msg in new_messages:
                    role = getattr(msg, 'role', None) or msg.get('role')
                    name = getattr(msg, 'name', None) or msg.get('name')
                    content = getattr(msg, 'content', None) or msg.get('content')
                    
                    if role == "function":
                        print(f"[DEBUG] Function result: {name}")
                        yield ToolResultMessage(
                            tool_name=name or "unknown",
                            result=content or ""
                        )
                        
                        # Check if this was a todo tool call - emit state update
                        if name and name.startswith("todo_"):
                            todo_state = self._get_current_todo_state()
                            yield TodoStateMessage(todos=todo_state)
                
                # Check if the last assistant message is growing (streaming content)
                if responses:
                    last_msg = responses[-1]
                    role = getattr(last_msg, 'role', None) or last_msg.get('role')
                    function_call = getattr(last_msg, 'function_call', None) or last_msg.get('function_call')
                    content = getattr(last_msg, 'content', None) or last_msg.get('content')
                    
                    if (role == "assistant" and not function_call and content):
                        if not current_message_started:
                            # Start of new streaming message
                            yield MessageStart(message_type="analysis")
                            current_message_started = True
                            last_assistant_content = ""
                        
                        # Send new tokens
                        if content != last_assistant_content:
                            new_content = content[len(last_assistant_content):]
                            if new_content:
                                yield MessageToken(token=new_content)
                                last_assistant_content = content
                
                last_yielded_count = len(responses)
            
            # End the current streaming message
            if current_message_started:
                yield MessageEnd()
                        
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
