import json5
from qwen_agent.tools.base import BaseTool, register_tool

from bug_bot.tools import run_in_container

@register_tool('list_dir')
class ListDirTool(BaseTool):
    description = 'List directory contents'
    parameters = [{
        'name': 'directory',
        'type': 'string',
        'description': 'Directory path (defaults to current)',
        'required': False
    }]

    def call(self, params: str, **kwargs) -> str:
        parsed_params = json5.loads(params)
        directory = parsed_params.get('directory', '.')
        self._pretty_print_tool(directory)
        return run_in_container(f"ls -la {directory}")
    
    def _pretty_print_tool(self, directory: str):
        print(f"🛠️ Listing")
        print(f"  - directory: {directory}\n")