"""Minimal tool call indicator widget."""

import json

from rich.text import Text
from textual.widget import Widget


class ToolIndicator(Widget):
    """A minimal widget to show tool calls without taking up much space."""

    def __init__(self, tool_name: str, arguments: str = "", **kwargs):
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.arguments = arguments
        self.completed = False
        print(
            f"[DEBUG] ToolIndicator created: tool_name='{tool_name}', arguments='{arguments}'"
        )
        self.display_text = self._create_display_text()

    def update_arguments(self, arguments: str) -> None:
        """Update the arguments and refresh the display."""
        self.arguments = arguments
        self.display_text = self._create_display_text()
        self.refresh()

    def _create_display_text(self) -> str:
        """Create a user-friendly display text for the tool call."""
        print(
            f"[DEBUG] _create_display_text: tool_name='{self.tool_name}', arguments='{self.arguments}'"
        )

        # Try to parse complete JSON first
        try:
            if self.arguments and self.arguments.strip().endswith("}"):
                args = json.loads(self.arguments)
                print(f"[DEBUG] Parsed complete JSON args: {args}")

                # Create descriptive text based on tool name and arguments
                if self.tool_name == "cat":
                    file_path = args.get("filePath", "")
                    return f"cat {file_path}" if file_path else "cat"
                elif self.tool_name == "ls":
                    directory = args.get("directory", ".")
                    return f"ls {directory}"
                elif self.tool_name == "glob":
                    pattern = args.get("pattern", "")
                    return f"glob '{pattern}'" if pattern else "glob"
                elif self.tool_name == "grep":
                    pattern = args.get("pattern", "")
                    return f"grep '{pattern}'" if pattern else "grep"
                elif self.tool_name == "run_in_container":
                    command = args.get("command", "")
                    if len(command) > 30:
                        command = command[:27] + "..."
                    return f"run '{command}'" if command else "run"
                elif self.tool_name == "todo_write":
                    return "todo_write"
                elif self.tool_name == "todo_read":
                    return "todo_read"
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
                        return f"cat {file_path}"
            elif self.tool_name == "ls" and '"directory"' in self.arguments:
                # Extract directory value if possible
                match = re.search(
                    r'"directory":\s*"([^"]*)', self.arguments
                )  # Remove closing quote requirement
                if match:
                    directory = match.group(1)
                    return f"ls {directory}" if directory else "ls ."
                elif self.arguments == "{}":
                    return "ls ."
            elif self.tool_name == "glob" and '"pattern"' in self.arguments:
                # Extract pattern value if possible
                match = re.search(
                    r'"pattern":\s*"([^"]*)', self.arguments
                )  # Remove closing quote requirement
                if match:
                    pattern = match.group(1)
                    if pattern:  # Only show if we have some pattern content
                        return f"glob '{pattern}'"
            elif self.tool_name == "grep" and '"pattern"' in self.arguments:
                # Extract pattern value if possible
                match = re.search(
                    r'"pattern":\s*"([^"]*)', self.arguments
                )  # Remove closing quote requirement
                if match:
                    pattern = match.group(1)
                    if pattern:  # Only show if we have some pattern content
                        return f"grep '{pattern}'"

        # Fallback to tool name
        return self.tool_name

    def render(self) -> Text:
        """Render a compact tool indicator."""
        if self.completed:
            return Text(f"[DONE] {self.display_text}")
        else:
            return Text(f"[RUNNING] {self.display_text}")

    def mark_completed(self) -> None:
        """Mark the tool as completed."""
        self.completed = True
        self.refresh()
