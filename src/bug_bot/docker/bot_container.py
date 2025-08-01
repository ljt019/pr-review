import os
import subprocess
import uuid
from pathlib import Path


class BotContainer:
    def __init__(self, zipped_codebase_path: str):
        self.zipped_codebase_path = zipped_codebase_path

    def start(self):
        """Start a fresh Docker container with a copy of the workspace."""
        try:
            self._ensure_image()
            container_name = f"bugbot-{uuid.uuid4().hex[:8]}"

            docker_command = [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "-v",
                f"{Path(self.zipped_codebase_path).resolve()}:/original_workspace:ro",
                "--network",
                "none",
                "bugbot-env:air",
                "sh",
                "-c",
                "mkdir -p /workspace && cp -r /original_workspace/* /workspace/ 2>/dev/null || true; sleep 3600",
            ]

            result = subprocess.run(
                docker_command, capture_output=True, text=True, timeout=10
            )

            # Check if /original_workspace is a directory or a file
            check_file_command = [
                "docker",
                "exec",
                container_name,
                "test",
                "-d",
                "/original_workspace",
            ]
            is_directory = subprocess.run(
                check_file_command, capture_output=True, text=True, timeout=10
            )

            # If /original_workspace is NOT a directory, assume it's the zip file itself
            if is_directory.returncode != 0:
                zip_file_path = "/original_workspace"
            else:
                # Otherwise, look for zip files in the directory
                find_zip_command = [
                    "docker",
                    "exec",
                    container_name,
                    "find",
                    "/original_workspace",
                    "-name",
                    "*.zip",
                    "-type",
                    "f",
                ]
                find_result = subprocess.run(
                    find_zip_command, capture_output=True, text=True, timeout=10
                )

                if find_result.returncode != 0 or not find_result.stdout.strip():
                    raise Exception("No zip file found in mounted directory")

                zip_file_path = find_result.stdout.strip().split("\n")[0]

            # Unzip the codebase and strip the top-level directory
            unzip_command = [
                "docker",
                "exec",
                container_name,
                "unzip",
                "-o",
                zip_file_path,
                "-d",
                "/tmp",
            ]
            unzip_result = subprocess.run(
                unzip_command, capture_output=True, text=True, timeout=30
            )

            if unzip_result.returncode == 0:
                # Move contents from the extracted subdirectory to workspace root
                move_command = [
                    "docker",
                    "exec",
                    container_name,
                    "sh",
                    "-c",
                    "cd /tmp && find . -mindepth 2 -maxdepth 2 -exec mv {} /workspace/ \\; 2>/dev/null || "
                    + "(cd /tmp/* && cp -r . /workspace/) 2>/dev/null || true",
                ]
                subprocess.run(move_command, capture_output=True, text=True, timeout=30)

            if unzip_result.returncode != 0:
                raise Exception(f"Unzip failed: {unzip_result.stderr}")

            if result.returncode != 0:
                raise Exception(f"Failed to start container: {result.stderr}")

            self.container_id = container_name
            # Expose container ID to BashTool via environment variable
            os.environ["BUGBOT_CONTAINER_ID"] = container_name
            return container_name
        except Exception as e:
            print(f"Error starting container: {str(e)}")
            raise

    def stop(self):
        """Stop the Docker container, and clean up the environment."""
        self._cleanup_container()

    def _ensure_image(self):
        """Build the bot environment image if it doesn't exist."""
        try:
            check_command = ["docker", "images", "-q", "bugbot-env:air"]
            result = subprocess.run(check_command, capture_output=True, text=True)

            if not result.stdout.strip():
                print("Building bot environment image...")
                build_command = [
                    "docker",
                    "build",
                    "-f",
                    "bot.dockerfile",
                    "-t",
                    "bugbot-env:air",
                    ".",
                ]
                build_result = subprocess.run(
                    build_command, capture_output=True, text=True, timeout=300
                )
                if build_result.returncode != 0:
                    raise Exception(f"Failed to build bot image: {build_result.stderr}")
                print("Bot environment image built successfully.")
        except Exception as e:
            print(f"Error ensuring bot image: {e}")
            raise

    def _cleanup_container(self):
        if hasattr(self, "container_id") and self.container_id:
            try:
                subprocess.run(
                    ["docker", "stop", self.container_id],
                    capture_output=True,
                    timeout=10,
                )
                subprocess.run(
                    ["docker", "rm", self.container_id], capture_output=True, timeout=10
                )
            except Exception:
                pass
            finally:
                # Remove environment variable when container is gone
                os.environ.pop("BUGBOT_CONTAINER_ID", None)
                self.container_id = None
