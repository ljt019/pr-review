import os
import subprocess
from pathlib import Path


def load_tool_description(tool_name: str) -> str:
    """Load tool description from corresponding .txt file"""
    description_path = Path(__file__).parent / f"{tool_name}.txt"
    return description_path.read_text().strip()


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
    """Run a command inside the analysis container."""
    container_id = os.environ.get("SNIFF_CONTAINER_ID")
    if not container_id:
        return "Error: Container not available"

    full_command = f"cd /workspace && {command}"

    try:
        result = subprocess.run(
            ["docker", "exec", container_id, "sh", "-c", full_command],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return result.stdout
        else:
            output = result.stderr if result.stderr else "Command failed"
            output += f"\nReturn code: {result.returncode}"
            return f"Error: {output}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds"
    except Exception as e:
        return f"Error: {str(e)}"
