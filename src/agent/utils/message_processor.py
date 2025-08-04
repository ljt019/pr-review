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

logger = logging.getLogger(__name__)


@dataclass
class StreamingContext:
    """Maintains state during message streaming."""

    last_yielded_count: int = 0
    last_assistant_content: str = ""
    current_message_started: bool = False
    yielded_tool_calls: Set[int] = None

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

    def _extract_message_fields(self, msg: Union[Message, dict]) -> dict:
        """Extract fields from either Message object or dict."""
        return {
            "role": getattr(msg, "role", None) or msg.get("role"),
            "content": getattr(msg, "content", None) or msg.get("content"),
            "function_call": getattr(msg, "function_call", None)
            or msg.get("function_call"),
            "name": getattr(msg, "name", None) or msg.get("name"),
        }

    def _extract_function_call_fields(self, function_call) -> dict:
        """Extract fields from function_call object or dict."""
        if not function_call:
            return {"name": None, "arguments": None}
        return {
            "name": getattr(function_call, "name", None) or function_call.get("name"),
            "arguments": getattr(function_call, "arguments", None)
            or function_call.get("arguments"),
        }

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
            fields = self._extract_message_fields(msg)
            
            if fields["role"] == "assistant" and fields["function_call"]:
                fc_fields = self._extract_function_call_fields(fields["function_call"])
                
                logger.debug(
                    f"Message {i}: Tool={fc_fields['name']}, Args='{fc_fields['arguments']}'"
                )

                # Check if ready to yield
                if (
                    i not in context.yielded_tool_calls
                    and self._is_args_ready(fc_fields["arguments"])
                ):
                    # End current streaming message first
                    if context.current_message_started:
                        yield MessageEnd()
                        context.current_message_started = False
                        context.last_assistant_content = ""

                    logger.debug(
                        f"Yielding ToolCallMessage: {fc_fields['name']}({fc_fields['arguments']})"
                    )
                    yield ToolCallMessage(
                        tool_name=fc_fields["name"],
                        arguments=fc_fields["arguments"],
                        reasoning=fields["content"] if fields["content"] else None,
                        call_id=f"{fc_fields['name']}_{i}",
                    )
                    context.yielded_tool_calls.add(i)

    def _process_function_results(
        self, responses: List, context: StreamingContext
    ) -> Iterator[BotMessage]:
        """Process new function result messages."""
        new_messages = responses[context.last_yielded_count :]
        
        for msg in new_messages:
            fields = self._extract_message_fields(msg)
            
            if fields["role"] == "function":
                logger.debug(f"Function result: {fields['name']}")
                yield ToolResultMessage(
                    tool_name=fields["name"] or "unknown", 
                    result=fields["content"] or ""
                )

                # Check if this was a todo tool call
                if fields["name"] and fields["name"].startswith("todo_") and self.get_todo_state:
                    todo_state = self.get_todo_state()
                    yield TodoStateMessage(todos=todo_state)

    def _process_streaming_content(
        self, responses: List, context: StreamingContext
    ) -> Iterator[BotMessage]:
        """Process streaming assistant content."""
        if not responses:
            return

        last_msg = responses[-1]
        fields = self._extract_message_fields(last_msg)

        if (
            fields["role"] == "assistant"
            and not fields["function_call"]
            and fields["content"]
        ):
            if not context.current_message_started:
                # Start new streaming message
                yield MessageStart(message_type="analysis")
                context.current_message_started = True
                context.last_assistant_content = ""

            # Send new tokens
            if fields["content"] != context.last_assistant_content:
                new_content = fields["content"][len(context.last_assistant_content) :]
                if new_content:
                    yield MessageToken(token=new_content)
                    context.last_assistant_content = fields["content"]