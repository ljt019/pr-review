"""Cat tool message widget"""

import json
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Markdown, Static

from agent.messaging import ToolExecutionMessage


class CatToolMessage(Static):
    """Tool call made by the agent to *cat* files using Markdown code fencing"""

    file_content: str = """import os
import shutil
import time

def cleanup_tmp():
    # Bug: Deletes entire /tmp subdirs without filtering (security/resource_management)
    base = "/tmp"
    for name in os.listdir(base):
        path = os.path.join(base, name)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except Exception:
            # Bug: Swallowing exceptions hides failures (error_handling)
            pass

def rotate_logs():
    # Bug: Inefficient rotation copies entire file repeatedly (performance)
    log = "/tmp/app.log"
    if not os.path.exists(log):
        return
    ts = int(time.time())
    shutil.copy(log, f"/tmp/app.{ts}.log")"""

    def __init__(self, tool_message: ToolExecutionMessage, file_content=None):
        super().__init__("", classes="agent-tool-message")
        self.tool_message = tool_message
        if file_content is not None:
            self.file_content = file_content
        elif tool_message.result and tool_message.success:
            self.file_content = tool_message.result

    def compose(self) -> ComposeResult:
        try:
            args = self.tool_message.arguments if isinstance(self.tool_message.arguments, dict) else json.loads(str(self.tool_message.arguments))
            file_path = args.get("filePath", args.get("file_path", args.get("file", args.get("path", ""))))
        except (json.JSONDecodeError, AttributeError, TypeError):
            file_path = ""
        
        # If still empty, try to extract from tool_message directly  
        if not file_path and hasattr(self.tool_message, 'arguments'):
            file_path = str(self.tool_message.arguments)[:50] + "..." if len(str(self.tool_message.arguments)) > 50 else str(self.tool_message.arguments)
        file_ext = file_path.split(".")[-1] if "." in file_path else "text"

        # Let Markdown handle the line numbers and syntax highlighting
        markdown_content = f"```{file_ext}\n{self.file_content}\n```"

        markdown_widget = Markdown(markdown_content, classes="code-markdown")
        markdown_widget.code_dark_theme = "catppuccin-mocha"

        yield Vertical(
            Horizontal(
                Label("⚯ Cat", classes="tool-title"),
                Label(
                    f" {file_path or 'unknown'}", classes="tool-content"
                ),
                classes="tool-horizontal",
            ),
            markdown_widget,
        )