import os
import subprocess
from pathlib import Path

# Re-export unified path utilities
from .path_utils import normalize_path, to_workspace_relative

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
    content = prompt_path.read_text().strip()

    # Handle template substitution for system_prompt
    if prompt_name == "system_prompt" and "{PROCESS_INSTRUCTIONS}" in content:
        process_instructions = load_prompt("process_instructions")
        content = content.replace("{PROCESS_INSTRUCTIONS}", process_instructions)

    return content


def run_in_container(command: str) -> str:
    """Run a command inside the analysis container (Docker SDK first, CLI fallback)."""
    container_id = os.environ.get("SNIFF_CONTAINER_ID")
    if not container_id:
        return "Error: Container not available"

    full_command = f"cd /workspace && {command}"

    # Preferred path: Docker SDK
    try:
        import docker

        client = docker.from_env()
        container = client.containers.get(container_id)
        result = container.exec_run(
            cmd=["sh", "-c", full_command], stdout=True, stderr=True
        )
        output = (
            result.output.decode("utf-8", errors="replace")
            if isinstance(result.output, (bytes, bytearray))
            else str(result.output)
        )
        if result.exit_code == 0:
            return output
        return f"Error: {output}\nReturn code: {result.exit_code}"
    except Exception:
        # Fallback path: docker CLI
        try:
            result = subprocess.run(
                ["docker", "exec", container_id, "sh", "-c", full_command],
                capture_output=True,
                text=True,
                timeout=RUN_IN_CONTAINER_TIMEOUT_SEC,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0:
                return result.stdout
            output = result.stderr if result.stderr else "Command failed"
            output += f"\nReturn code: {result.returncode}"
            return f"Error: {output}"
        except subprocess.TimeoutExpired:
            return (
                f"Error: Command timed out after {RUN_IN_CONTAINER_TIMEOUT_SEC} seconds"
            )
        except Exception as e:
            return f"Error: {str(e)}"
