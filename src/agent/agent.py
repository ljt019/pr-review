import asyncio
import logging
import os
from enum import Enum
from queue import Queue
from threading import Thread

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.messages import (
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ToolReturnPart,
)
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from agent.messages import (
    BotMessage,
    MessageEnd,
    MessageStart,
    MessageToken,
    TodoStateMessage,
    ToolCallMessage,
    ToolResultMessage,
)
from agent.sandbox import Sandbox
from agent.utils.response_saver import save_response_with_summary
from agent.tools import load_prompt, run_in_container
from agent.tools.bash import bash_tool
from agent.tools.cat import cat_tool
from agent.tools.glob import glob_tool
from agent.tools.grep import grep_tool
from agent.tools.ls import ls_tool
from agent.tools.todo import todo_read_tool, todo_write_tool
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
        provider = OpenRouterProvider(api_key=os.getenv("OPEN_ROUTER_API_KEY"))
        model = OpenAIModel(model_option.value, provider=provider)

        system_instruction = load_prompt("system_prompt")
        tools = [
            ls_tool,
            cat_tool,
            grep_tool,
            glob_tool,
            todo_write_tool,
            todo_read_tool,
            bash_tool,
        ]

        self.agent = Agent(model=model, instructions=system_instruction, tools=tools)
        self.container = Sandbox(zipped_codebase)

        from agent.utils.file_tracker import FileTracker

        self.file_tracker = FileTracker()
        self.container.start()
        self._wait_for_workspace_ready()
        self._last_assistant_content = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._cleanup()

    def __del__(self):
        self._cleanup()

    def run(self, save_response: bool = False) -> str | None:
        for _ in self.run_streaming():
            pass
        content = self._last_assistant_content
        if save_response and content:
            save_response_with_summary(content, PROJECT_ROOT)
        if content:
            content = self._inject_files_analyzed(content)
        return content

    def run_streaming(self):
        """Run the agent and yield streaming message events."""
        queue: "Queue[BotMessage | None]" = Queue()

        async def worker():
            try:
                async with self.agent.run_stream(
                    user_prompt=load_prompt("starting_query")
                ) as stream:
                    async for event in stream._stream_response:
                        if isinstance(event, FunctionToolCallEvent):
                            call = event.part
                            msg = ToolCallMessage(
                                tool_name=call.tool_name,
                                arguments=call.args_as_json_str(),
                                call_id=call.tool_call_id,
                            )
                            queue.put(msg)
                            if call.tool_name == "cat":
                                self.file_tracker.track_tool_call(msg)
                        elif isinstance(event, FunctionToolResultEvent):
                            result = event.result
                            if isinstance(result, ToolReturnPart):
                                msg = ToolResultMessage(
                                    tool_name=result.tool_name,
                                    result=str(result.content),
                                )
                                queue.put(msg)
                                if result.tool_name == "cat":
                                    self.file_tracker.track_tool_result(msg)
                                if result.tool_name.startswith("todo_"):
                                    queue.put(
                                        TodoStateMessage(
                                            todos=self._get_current_todo_state()
                                        )
                                    )
                        elif isinstance(event, PartStartEvent):
                            if isinstance(event.part, TextPart):
                                queue.put(MessageStart(message_type="analysis"))
                                self._last_assistant_content = ""
                        elif isinstance(event, PartDeltaEvent):
                            if isinstance(event.delta, TextPartDelta):
                                token = event.delta.content_delta or ""
                                if token:
                                    queue.put(MessageToken(token=token))
                                    self._last_assistant_content += token
                        elif isinstance(event, FinalResultEvent):
                            queue.put(MessageEnd())
            finally:
                queue.put(None)

        Thread(target=lambda: asyncio.run(worker()), daemon=True).start()

        while True:
            item = queue.get()
            if item is None:
                break
            yield item

    def _get_current_todo_state(self) -> list[dict]:
        """Get the current todo state from the tools."""
        try:
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

    def _inject_files_analyzed(self, content: str) -> str:
        """Inject files_analyzed count into JSON response."""
        try:
            import json
            import re

            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                data["files_analyzed"] = self.file_tracker.get_files_count()
                updated_json = json.dumps(data, indent=2, ensure_ascii=False)
                return content.replace(json_str, updated_json)
            else:
                data = json.loads(content)
                data["files_analyzed"] = self.file_tracker.get_files_count()
                return json.dumps(data, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            return content
