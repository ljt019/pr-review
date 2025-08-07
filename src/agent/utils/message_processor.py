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
message_logger = logging.getLogger("sniff.messages")


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

    def __init__(self, get_todo_state_callback=None, conversation_logger=None):
        """Initialize the processor.

        Args:
            get_todo_state_callback: Optional callback to get current todo state
            conversation_logger: Optional conversation logger for raw logging
        """
        self.get_todo_state = get_todo_state_callback
        self.conversation_logger = conversation_logger
        self._step_counter = 0
        self._last_logged_response_count = 0  # Track responses to avoid duplication

    def _log_message_event(self, message: BotMessage) -> None:
        """Log detailed message events to file for debugging."""
        try:
            # Debug: Test if message logger is working
            message_logger.info("DEBUG: _log_message_event called!")
            if isinstance(message, ToolCallMessage):
                message_logger.info(f"🔧 TOOL_CALL: {message.tool_name}")
                message_logger.info(f"   Arguments: {message.arguments}")
                if message.reasoning:
                    message_logger.info(f"   Reasoning: {message.reasoning}")
            elif isinstance(message, ToolResultMessage):
                message_logger.info(f"✅ TOOL_RESULT: {message.tool_name}")
                # Log full result for debugging, but truncate extremely long ones
                result = message.result
                if len(result) > 1500:
                    result = (
                        result[:1500]
                        + f"\n... (truncated, full result was {len(message.result)} characters)"
                    )
                message_logger.info(f"   Result: {result}")
            elif isinstance(message, MessageStart):
                message_logger.info(f"💭 MESSAGE_START: {message.message_type}")
            elif isinstance(message, MessageToken):
                # Don't log individual tokens - too verbose
                pass
            elif isinstance(message, MessageEnd):
                message_logger.info("✨ MESSAGE_END")
            elif isinstance(message, TodoStateMessage):
                completed = sum(
                    1 for todo in message.todos if todo.get("status") == "completed"
                )
                total = len(message.todos)
                message_logger.info(f"📋 TODO_STATE: {completed}/{total} completed")
                # Only log todos that changed status, not all of them
                for i, todo in enumerate(message.todos):
                    status = todo.get("status", "unknown")
                    if status == "completed":
                        content = todo.get("content", "no content")
                        message_logger.info(f"   ✓ Todo {i + 1}: {content}")
            else:
                message_logger.info(f"📨 MESSAGE: {type(message).__name__}")
        except Exception as e:
            message_logger.error(f"Failed to log message event: {e}")

    def _log_raw_responses(self, responses) -> None:
        """Log raw LLM responses for debugging - but only new ones to avoid duplication."""
        try:
            # Skip if we only have one response and it's already been logged
            if len(responses) <= self._last_logged_response_count:
                return

            # Only log new responses
            new_responses = responses[self._last_logged_response_count :]

            for i, response in enumerate(
                new_responses, start=self._last_logged_response_count + 1
            ):
                if hasattr(response, "__dict__"):
                    # Message object - extract relevant fields
                    role = getattr(response, "role", None)
                    content = getattr(response, "content", None)
                    function_call = getattr(response, "function_call", None)
                    name = getattr(response, "name", None)
                else:
                    # Already a dict
                    role = response.get("role")
                    content = response.get("content")
                    function_call = response.get("function_call")
                    name = response.get("name")

                # Log concisely based on message type
                if role == "assistant" and function_call:
                    message_logger.info(
                        f"🤖 LLM wants to call: {function_call.get('name', 'unknown')}"
                    )
                elif role == "function":
                    message_logger.info(
                        f"🔧 Tool '{name}' returned {len(str(content))} chars"
                    )
                elif role == "assistant" and content:
                    message_logger.info(f"🤖 LLM streaming: {len(str(content))} chars")

            self._last_logged_response_count = len(responses)
        except Exception as e:
            message_logger.error(f"Failed to log raw responses: {e}")

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

            # Log raw responses if logger is enabled
            if self.conversation_logger and self.conversation_logger.enabled:
                self._step_counter += 1
                self.conversation_logger.log_raw_responses(
                    responses, self._step_counter
                )

            # Also log raw responses to our debug log
            self._log_raw_responses(responses)

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
            # Log final streaming content if logger is enabled
            if self.conversation_logger and context.last_assistant_content:
                self.conversation_logger.log_streaming_content(
                    context.last_assistant_content, is_complete=True
                )

            # Log the complete final response for debugging
            if context.last_assistant_content:
                message_logger.info("📝 FINAL_RESPONSE:")
                # Truncate very long responses but show more than individual tokens
                content = context.last_assistant_content
                if len(content) > 2000:
                    content = (
                        content[:2000]
                        + f"\n... (truncated, full response was {len(context.last_assistant_content)} characters)"
                    )
                message_logger.info(f"   {content}")

            msg = MessageEnd()
            self._log_message_event(msg)
            yield msg

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
                if i not in context.yielded_tool_calls and self._is_args_ready(
                    fc_fields["arguments"]
                ):
                    # End current streaming message first
                    if context.current_message_started:
                        msg = MessageEnd()
                        self._log_message_event(msg)
                        yield msg
                        context.current_message_started = False
                        context.last_assistant_content = ""

                    logger.debug(
                        f"Yielding ToolCallMessage: {fc_fields['name']}({fc_fields['arguments']})"
                    )

                    # Log tool call if logger is enabled
                    if self.conversation_logger and self.conversation_logger.enabled:
                        self.conversation_logger.log_tool_call(
                            fc_fields["name"],
                            fc_fields["arguments"],
                            fields["content"] if fields["content"] else None,
                        )

                    msg = ToolCallMessage(
                        tool_name=fc_fields["name"],
                        arguments=fc_fields["arguments"],
                        reasoning=fields["content"] if fields["content"] else None,
                        call_id=f"{fc_fields['name']}_{i}",
                    )
                    self._log_message_event(msg)
                    yield msg
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

                # Log tool result if logger is enabled
                if self.conversation_logger:
                    self.conversation_logger.log_tool_result(
                        fields["name"] or "unknown", fields["content"] or ""
                    )

                msg = ToolResultMessage(
                    tool_name=fields["name"] or "unknown",
                    result=fields["content"] or "",
                )
                self._log_message_event(msg)
                yield msg

                # Check if this was a todo tool call
                if (
                    fields["name"]
                    and fields["name"].startswith("todo_")
                    and self.get_todo_state
                ):
                    todo_state = self.get_todo_state()
                    msg = TodoStateMessage(todos=todo_state)
                    self._log_message_event(msg)
                    yield msg

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
                msg = MessageStart(message_type="analysis")
                self._log_message_event(msg)
                yield msg
                context.current_message_started = True
                context.last_assistant_content = ""

            # Send new tokens
            if fields["content"] != context.last_assistant_content:
                new_content = fields["content"][len(context.last_assistant_content) :]
                if new_content:
                    msg = MessageToken(token=new_content)
                    self._log_message_event(msg)
                    yield msg
                    context.last_assistant_content = fields["content"]
