"""Agent message widget"""

from textual.widgets import Static


class AgentMessage(Static):
    """Message from the agent with streaming-friendly APIs."""

    def __init__(self, message: str):
        super().__init__(message, classes="agent-message")
        self._content: str = message or ""

    def append_chunk(self, chunk: str) -> None:
        """Append a chunk to the current content and update the renderable."""
        if not chunk:
            return
        self._content += chunk
        self.update(self._content)

    def set_content(self, content: str) -> None:
        """Replace the entire content and update the renderable."""
        self._content = content or ""
        self.update(self._content)

    def get_content(self) -> str:
        """Return the current content string."""
        return self._content
