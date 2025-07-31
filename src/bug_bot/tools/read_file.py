import json5
from qwen_agent.tools.base import BaseTool, register_tool

from bug_bot.tools import run_in_container

@register_tool('read_file')
class ReadFileTool(BaseTool):
    description = 'Read file contents'
    parameters = [{
        'name': 'filepath',
        'type': 'string',
        'description': 'Path to the file to read',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        parsed_params = json5.loads(params)
        filepath = parsed_params.get('filepath')
        if not filepath:
            return "Error: filepath parameter is required"
        
        self._pretty_print_tool(filepath)
        return run_in_container(f"cat {filepath}")
    
    def _pretty_print_tool(self, filepath: str):
        print(f"🛠️ Reading file")
        print(f"  - filepath: {filepath}\n")