from qwen_agent.tools.base import BaseTool, register_tool

from agent.tools import load_tool_description, run_in_container
from agent.utils.param_parser import ParameterParser


@register_tool("bash")
class BashTool(BaseTool):
    description = load_tool_description("bash")
    parameters = [
        {
            "name": "command",
            "type": "string",
            "description": "Bash command to execute",
            "required": True,
        }
    ]

    def call(self, params: str, **kwargs) -> str:
        parsed_params = ParameterParser.parse_params(params)
        command = ParameterParser.get_required_param(parsed_params, "command")
        return run_in_container(command)
