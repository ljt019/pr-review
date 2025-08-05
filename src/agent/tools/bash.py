from pydantic_ai.tools import Tool

from agent.tools import load_tool_description, run_in_container


def bash(command: str) -> str:
    """Execute a bash command inside the docker workspace.

    Args:
        command: Bash command to execute
    """
    return run_in_container(command)


bash_tool = Tool(bash, name="bash", description=load_tool_description("bash"))
