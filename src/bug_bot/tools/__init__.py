import os
import subprocess

def run_in_container(command: str) -> str:
    """Run a command in the Docker container."""
    container_id = os.environ.get("BUGBOT_CONTAINER_ID")
    if not container_id:
        return "Error: Container not available"
    
    try:
        full_command = f"cd /workspace && {command}"
        result = subprocess.run(
            ["docker", "exec", container_id, "bash", "-c", full_command],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return result.stdout
        else:
            output = result.stderr if result.stderr else "Command failed"
            if result.returncode != 0:
                output += f"\nReturn code: {result.returncode}"
            return f"Error: {output}"
    except Exception as e:
        return f"Error: {str(e)}"