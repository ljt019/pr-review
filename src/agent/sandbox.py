import os
import uuid
from pathlib import Path

import docker
from docker.errors import DockerException, ImageNotFound


class Sandbox:
    def __init__(self, zipped_codebase_path: str):
        self.zipped_codebase_path = zipped_codebase_path
        self.client = docker.from_env()
        self.container = None
        self.container_name = None

    def start(self) -> str:
        """Start a fresh Docker container with a copy of the workspace."""
        try:
            self._ensure_image()
            self.container_name = f"sniff-{uuid.uuid4().hex[:8]}"

            # Create and start container
            self.container = self.client.containers.run(
                "sniff-env:air",
                command="sh -c 'mkdir -p /workspace && cp -r /original_workspace/* /workspace/ 2>/dev/null || true; sleep 3600'",
                name=self.container_name,
                detach=True,
                volumes={
                    str(Path(self.zipped_codebase_path).resolve()): {
                        'bind': '/original_workspace',
                        'mode': 'ro'
                    }
                },
                network_mode='none'
            )

            # Check if /original_workspace is a directory or a file
            exit_code, _ = self.container.exec_run("test -d /original_workspace")
            
            # If /original_workspace is NOT a directory, assume it's the zip file itself
            if exit_code != 0:
                zip_file_path = "/original_workspace"
            else:
                # Otherwise, look for zip files in the directory
                exit_code, output = self.container.exec_run(
                    "find /original_workspace -name '*.zip' -type f"
                )
                
                if exit_code != 0 or not output.decode().strip():
                    raise Exception("No zip file found in mounted directory")
                
                zip_file_path = output.decode().strip().split("\n")[0]

            # Unzip the codebase
            exit_code, output = self.container.exec_run(
                f"unzip -o {zip_file_path} -d /tmp"
            )
            
            if exit_code != 0:
                raise Exception(f"Unzip failed: {output.decode()}")

            # Move contents from the extracted subdirectory to workspace root, preserving structure
            self.container.exec_run(
                "sh -c 'cd /tmp && if [ -d */ ]; then cd */ && cp -r . /workspace/; else cp -r . /workspace/; fi'"
            )

            # Expose container ID to BashTool via environment variable
            os.environ["SNIFF_CONTAINER_ID"] = self.container_name
            return self.container_name
            
        except Exception as e:
            self._cleanup_container()
            raise

    def stop(self) -> None:
        """Stop the Docker container, and clean up the environment."""
        self._cleanup_container()

    def _ensure_image(self) -> None:
        """Build the bot environment image if it doesn't exist."""
        try:
            # Check if image exists
            self.client.images.get("sniff-env:air")
        except ImageNotFound:
            # Build the image
            self.client.images.build(
                path=".",
                dockerfile="bot.dockerfile",
                tag="sniff-env:air",
                rm=True
            )
        except DockerException as e:
            raise

    def _cleanup_container(self) -> None:
        """Clean up the container and environment."""
        if not self.container:
            return
            
        # Try to stop and remove using container object
        try:
            self.container.stop(timeout=5)
            self.container.remove(force=True)
        except Exception:
            # If that fails, try using container name
            if self.container_name:
                try:
                    container = self.client.containers.get(self.container_name)
                    container.stop(timeout=5)
                    container.remove(force=True)
                except Exception:
                    # Both methods failed, but we still need to clean up state
                    pass
        
        # Always clean up state, regardless of success
        os.environ.pop("SNIFF_CONTAINER_ID", None)
        self.container = None
        self.container_name = None

