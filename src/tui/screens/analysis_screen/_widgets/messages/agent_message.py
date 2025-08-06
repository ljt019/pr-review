"""Agent message widget"""

from textual.widgets import Static


class AgentMessage(Static):
    """Message from the agent"""

    def __init__(self, message: str):
        super().__init__(message, classes="agent-message")