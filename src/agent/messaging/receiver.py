"""Simple message receiver using queue.Queue internally."""

import queue
from typing import Iterator

from .types import AgentMessage


class MessageReceiver:
    """Receives messages using Python's built-in queue.Queue."""

    def __init__(self):
        """Initialize the message receiver."""
        self._queue = queue.Queue()

    def receive_message(self, message: AgentMessage) -> None:
        """Receive a message for processing."""
        self._queue.put(message)

    def get_message(self, timeout: float = None) -> AgentMessage:
        """Get a message from the queue. Blocks until available or timeout."""
        return self._queue.get(timeout=timeout)

    def get_message_nowait(self) -> AgentMessage:
        """Get a message without blocking. Raises queue.Empty if none available."""
        return self._queue.get_nowait()

    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()

    def qsize(self) -> int:
        """Get approximate queue size."""
        return self._queue.qsize()
