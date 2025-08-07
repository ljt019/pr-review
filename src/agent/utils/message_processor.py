"""Message processing pipeline for streaming agent responses."""

import logging
from dataclasses import dataclass
from typing import Iterator, List, Set, Union

from qwen_agent.llm.schema import Message

from agent.messages import (
    BotMessage,
    MessageEnd,
    MessageStart,
    MessageToken,
    TodoStateMessage,
    ToolCallMessage,
    ToolResultMessage,
)
from agent.utils.message_utils import to_message_data

logger = logging.getLogger(__name__)


@dataclass
class StreamingContext:
    """Maintains state during message streaming."""

    last_yielded_count: int = 0
    last_assistant_content: str = ""
    current_message_started: bool = False
    yielded_tool_calls: Set[int] | None = None

    def __post_init__(self):
        if self.yielded_tool_calls is None:
            self.yielded_tool_calls = set()


class MessageProcessor:
    """Handles the complex logic of processing streaming messages from the agent."""

    def __init__(self, get_todo_state_callback=None):
        """Initialize the processor.

        Args:
            get_todo_state_callback: Optional callback to get current todo state
        """
        self.get_todo_state = get_todo_state_callback

    def process_stream(
        self, agent_responses: Iterator[List[Union[Message, dict]]]
    ) -> Iterator[BotMessage]:
        """Process streaming responses from the agent and yield clean message events.

        Args:
            agent_responses: Iterator of response lists from the agent

        Yields:
            BotMessage events for tool calls, results, and streaming content
        """
        context = StreamingContext()

        for responses in agent_responses:
            if not responses:
                continue

            logger.debug(f"Processing {len(responses)} total messages")

            # Process tool calls
            yield from self._process_tool_calls(responses, context)

            # Process new function results
            yield from self._process_function_results(responses, context)

            # Process streaming content
            yield from self._process_streaming_content(responses, context)

            context.last_yielded_count = len(responses)

        # End any remaining streaming message
        if context.current_message_started:
            yield MessageEnd()

    def _is_args_ready(self, args: str) -> bool:
        """Check if function arguments are ready to be yielded."""
        if not args:
            return False

        # Complete JSON
        if args.strip().endswith("}"):
            return True

        # Substantial partial content with key fields
        if len(args) > 20:
            key_patterns = [
                ('"filePath":', 11),
                ('"directory":', 12),
                ('"pattern":', 10),
                ('"command":', 10),
            ]
            for pattern, offset in key_patterns:
                if pattern in args and '"' in args[args.find(pattern) + offset :]:
                    return True

        return False

    def _process_tool_calls(
        self, responses: List, context: StreamingContext
    ) -> Iterator[BotMessage]:
        """Process tool calls in the responses."""
        for i, msg in enumerate(responses):
            data = to_message_data(msg)

            if data.role == "assistant" and data.function_call:
                fc = data.function_call

                logger.debug(
                    f"Message {i}: Tool={fc.name}, Args='{fc.arguments}'"
                )

                # Check if ready to yield
                if (
                    i not in context.yielded_tool_calls
                    and self._is_args_ready(fc.arguments)
                ):
                    # End current streaming message first
                    if context.current_message_started:
                        yield MessageEnd()
                        context.current_message_started = False
                        context.last_assistant_content = ""

                    logger.debug(
                        f"Yielding ToolCallMessage: {fc.name}({fc.arguments})"
                    )
                    yield ToolCallMessage(
                        tool_name=fc.name,
                        arguments=fc.arguments,
                        reasoning=data.content if data.content else None,
                        call_id=f"{fc.name}_{i}",
                    )
                    context.yielded_tool_calls.add(i)

    def _process_function_results(
        self, responses: List, context: StreamingContext
    ) -> Iterator[BotMessage]:
        """Process new function result messages."""
        new_messages = responses[context.last_yielded_count :]

        for msg in new_messages:
            data = to_message_data(msg)

            if data.role == "function":
                logger.debug(f"Function result: {data.name}")
                yield ToolResultMessage(
                    tool_name=data.name or "unknown",
                    result=data.content or "",
                )

                # Check if this was a todo tool call
                if (
                    data.name
                    and data.name.startswith("todo_")
                    and self.get_todo_state
                ):
                    todo_state = self.get_todo_state()
                    yield TodoStateMessage(todos=todo_state)

    def _process_streaming_content(
        self, responses: List, context: StreamingContext
    ) -> Iterator[BotMessage]:
        """Process streaming assistant content."""
        if not responses:
            return

        last_msg = to_message_data(responses[-1])

        if (
            last_msg.role == "assistant"
            and not last_msg.function_call
            and last_msg.content
        ):
            if not context.current_message_started:
                # Start new streaming message
                yield MessageStart(message_type="analysis")
                context.current_message_started = True
                context.last_assistant_content = ""

            # Send new tokens
            if last_msg.content != context.last_assistant_content:
                new_content = last_msg.content[len(context.last_assistant_content) :]
                if new_content:
                    yield MessageToken(token=new_content)
                    context.last_assistant_content = last_msg.content

