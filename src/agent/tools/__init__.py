import os
import subprocess
from pathlib import Path

# Re-export unified path utilities
from .path_utils import normalize_path, to_workspace_relative

# Export common tool utilities
__all__ = [
    "normalize_path",
    "to_workspace_relative",
    "run_in_container",
    "load_tool_description",
    "load_prompt",
    "parse_tool_params",
]

# Configurable timeout for container commands
RUN_IN_CONTAINER_TIMEOUT_SEC = 60


def load_tool_description(tool_name: str) -> str:
    """Load tool description from corresponding .txt file"""
    description_path = Path(__file__).parent / f"{tool_name}.txt"
    try:
        return description_path.read_text().strip()
    except FileNotFoundError:
        return ""


def load_prompt(prompt_name: str) -> str:
    """Load prompt from corresponding .txt file in prompts directory"""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    prompt_path = prompts_dir / f"{prompt_name}.txt"
    return prompt_path.read_text().strip()


def run_in_container(command: str) -> str:
    """Run a command inside the analysis container (Docker SDK first, CLI fallback)."""
    container_id = os.environ.get("SNIFF_CONTAINER_ID")
    if not container_id:
        return "Error: Container not available"

    full_command = f"cd /workspace && {command}"

    def _format_result(success: bool, output: str, exit_code: int = 0) -> str:
        """Format execution result consistently."""
        if success:
            return output
        return f"Error: {output}\nReturn code: {exit_code}"

    # Try Docker SDK first, then CLI fallback
    for method in [_try_docker_sdk, _try_docker_cli]:
        try:
            return method(container_id, full_command, _format_result)
        except Exception:
            continue

    return "Error: All execution methods failed"


def _try_docker_sdk(container_id: str, command: str, formatter) -> str:
    """Execute via Docker SDK."""
    import docker

    client = docker.from_env()
    result = client.containers.get(container_id).exec_run(cmd=["sh", "-c", command])
    output = (
        result.output.decode("utf-8", errors="replace")
        if isinstance(result.output, (bytes, bytearray))
        else str(result.output)
    )
    return formatter(result.exit_code == 0, output, result.exit_code)


def _try_docker_cli(container_id: str, command: str, formatter) -> str:
    """Execute via Docker CLI."""
    result = subprocess.run(
        ["docker", "exec", container_id, "sh", "-c", command],
        capture_output=True,
        text=True,
        timeout=RUN_IN_CONTAINER_TIMEOUT_SEC,
        encoding="utf-8",
        errors="replace",
    )
    output = (
        result.stdout if result.returncode == 0 else (result.stderr or "Command failed")
    )
    return formatter(result.returncode == 0, output, result.returncode)


def parse_tool_params(
    params: str,
    path_param: str = "path",
    required_path: bool = False,
    default_path: str = ".",
):
    """Parse and normalize common tool parameters."""
    from agent.utils.param_parser import ParameterParser

    parsed_params = ParameterParser.parse_params(params)
    original_path = (
        ParameterParser.get_required_param(parsed_params, path_param)
        if required_path
        else ParameterParser.get_optional_param(parsed_params, path_param, default_path)
    )
    return parsed_params, normalize_path(original_path), original_path
