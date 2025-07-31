import json5
from qwen_agent.tools.base import BaseTool, register_tool

from bug_bot.tools import run_in_container

@register_tool('bash')
class BashTool(BaseTool):
    description = 'Execute bash command'
    parameters = [{
        'name': 'command',
        'type': 'string',
        'description': 'Bash command to execute',
        'required': True
    }]

    def call(self, params: str, **kwargs) -> str:
        parsed_params = json5.loads(params)
        command = parsed_params.get('command')
        if not command:
            return "Error: command parameter is required"
        
        self._pretty_print_tool(command)
        return run_in_container(command)
    
    def _pretty_print_tool(self, command: str):
        print(f"🛠️ Executing command")
        print(f"  - command: {command}\n")