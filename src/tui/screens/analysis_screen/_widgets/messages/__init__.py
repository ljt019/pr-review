"""Message widgets for the analysis screen"""

from ..todo_message_widget import TodoMessageWidget  # new unified todo widget
from .agent_message import AgentMessage
from .cat_tool_message import CatToolMessage
from .glob_tool_message import GlobToolMessage
from .grep_tool_message import GrepToolMessage
from .ls_tool_message import LsToolMessage

# Centralized registry of tool-name to widget class
TOOL_WIDGET_MAP = {
    "grep": GrepToolMessage,
    "cat": CatToolMessage,
    "ls": LsToolMessage,
    "glob": GlobToolMessage,
}

__all__ = [
    "AgentMessage",
    "GrepToolMessage",
    "GlobToolMessage",
    "LsToolMessage",
    "CatToolMessage",
    "TodoMessageWidget",
    "TOOL_WIDGET_MAP",
]
