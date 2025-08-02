"""Minimal tool call indicator widget."""

import json
from typing import Any, Dict, List, Optional

from rich.text import Text
from textual.widget import Widget


class ToolIndicator(Widget):
    """A minimal widget to show tool calls without taking up much space."""

    def __init__(self, tool_name: str, arguments: str = "", **kwargs):
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.arguments = arguments
        self.completed = False
        self.todo_data: Optional[List[Dict[str, Any]]] = None
        print(
            f"[DEBUG] ToolIndicator created: tool_name='{tool_name}', arguments='{arguments}'"
        )
        self.display_text = self._create_display_text()

    def update_arguments(self, arguments: str) -> None:
        """Update the arguments and refresh the display."""
        self.arguments = arguments
        self.display_text = self._create_display_text()
        self.refresh()

    def set_todo_data(self, todos: List[Dict[str, Any]]) -> None:
        """Set todo data for todo_read/todo_write tools."""
        self.todo_data = todos
        self.refresh()

    def _create_display_text(self) -> str:
        """Create a user-friendly display text for the tool call."""
        print(
            f"[DEBUG] _create_display_text: tool_name='{self.tool_name}', arguments='{self.arguments}'"
        )

        # Symbol mapping based on tool_plans.md
        # Using U+2064 invisible plus (forces text) as a workaround
        tool_symbols = {
            "cat": "⚯",  # Eye with invisible plus forces text rendering
            "glob": "⌕\ufe0e",
            "grep": "⌕\ufe0e",
            "ls": "☰",  # Directory path
            "todo_read": "⚯",  # Eye with invisible plus
            "todo_write": "✎\ufe0e",
        }

        symbol = tool_symbols.get(self.tool_name, "")

        # Try to parse complete JSON first
        try:
            if self.arguments and self.arguments.strip().endswith("}"):
                args = json.loads(self.arguments)
                print(f"[DEBUG] Parsed complete JSON args: {args}")

                # Create descriptive text based on tool name and arguments
                if self.tool_name == "cat":
                    file_path = args.get("filePath", "")
                    return f"{symbol} cat {file_path}" if file_path else f"{symbol} cat"
                elif self.tool_name == "ls":
                    directory = args.get("directory", ".")
                    return f"{symbol} ls {directory}"
                elif self.tool_name == "glob":
                    pattern = args.get("pattern", "")
                    return f"{symbol} glob '{pattern}'" if pattern else f"{symbol} glob"
                elif self.tool_name == "grep":
                    pattern = args.get("pattern", "")
                    return f"{symbol} grep '{pattern}'" if pattern else f"{symbol} grep"
                elif self.tool_name == "run_in_container":
                    command = args.get("command", "")
                    if len(command) > 30:
                        command = command[:27] + "..."
                    return f"run '{command}'" if command else "run"
                elif self.tool_name == "todo_write":
                    return f"{symbol} writing todos"
                elif self.tool_name == "todo_read":
                    return f"{symbol} reading todos"
        except json.JSONDecodeError:
            # JSON not complete yet, fall through to partial parsing
            pass

        # Handle partial/incomplete JSON by extracting what we can
        if self.arguments:
            import re

            # Try to extract common patterns from incomplete JSON
            if self.tool_name == "cat" and '"filePath"' in self.arguments:
                # Extract filePath value if possible - handle both complete and incomplete strings
                match = re.search(
                    r'"filePath":\s*"([^"]*)', self.arguments
                )  # Remove closing quote requirement
                if match:
                    file_path = match.group(1)
                    if file_path:  # Only show if we have some path content
                        return f"{symbol} cat {file_path}"
            elif self.tool_name == "ls" and '"directory"' in self.arguments:
                # Extract directory value if possible
                match = re.search(
                    r'"directory":\s*"([^"]*)', self.arguments
                )  # Remove closing quote requirement
                if match:
                    directory = match.group(1)
                    return f"{symbol} ls {directory}" if directory else f"{symbol} ls ."
                elif self.arguments == "{}":
                    return f"{symbol} ls ."
            elif self.tool_name == "glob" and '"pattern"' in self.arguments:
                # Extract pattern value if possible
                match = re.search(
                    r'"pattern":\s*"([^"]*)', self.arguments
                )  # Remove closing quote requirement
                if match:
                    pattern = match.group(1)
                    if pattern:  # Only show if we have some pattern content
                        return f"{symbol} glob '{pattern}'"
            elif self.tool_name == "grep" and '"pattern"' in self.arguments:
                # Extract pattern value if possible
                match = re.search(
                    r'"pattern":\s*"([^"]*)', self.arguments
                )  # Remove closing quote requirement
                if match:
                    pattern = match.group(1)
                    if pattern:  # Only show if we have some pattern content
                        return f"{symbol} grep '{pattern}'"

        # Fallback to tool name with symbol
        if self.tool_name == "todo_write":
            return f"{symbol} writing todos"
        elif self.tool_name == "todo_read":
            return f"{symbol} reading todos"
        else:
            return f"{symbol} {self.tool_name}" if symbol else self.tool_name

    def render(self) -> Text:
        """Render a compact tool indicator."""
        if self.completed:
            text = Text(self.display_text)

            # If this is a todo tool and we have todo data, append it
            if self.tool_name in ["todo_write", "todo_read"] and self.todo_data:
                for i, todo in enumerate(self.todo_data):
                    # First todo gets the tree branch
                    if i == 0:
                        text.append("\n  └ ")
                    else:
                        text.append("\n    ")

                    # Add checkbox
                    status = todo.get("status", "incomplete")
                    if status == "complete":
                        text.append("●")  # Filled circle for completed
                    else:
                        text.append("○")  # Empty circle for incomplete

                    # Add todo content
                    content = todo.get("content", "")
                    # Truncate if too long
                    max_length = 35
                    if len(content) > max_length:
                        content = content[: max_length - 3] + "..."
                    text.append(f" {content}")

            return text
        else:
            # Don't display anything while running
            return Text("")

    def mark_completed(self) -> None:
        """Mark the tool as completed."""
        self.completed = True
        self.refresh()
