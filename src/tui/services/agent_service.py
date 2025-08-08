"""Service layer for agent interaction, separating business logic from UI concerns."""

import logging
from pathlib import Path
from typing import Iterator, Optional

from agent.agent import ModelOptions, create_agent
from agent.messaging import AgentMessage, MessageReceiver
from paths import get_path

logger = logging.getLogger(__name__)


class AgentService:
    """Handles all agent-related business logic and execution."""

    def __init__(
        self,
        model_option: ModelOptions,
        zipped_codebase: Optional[str] = None,
        enable_logging: bool = False,
    ):
        """Initialize the agent service.

        Args:
            model_option: The model to use for analysis
            zipped_codebase: Path to the zipped codebase to analyze,
                           defaults to toy-webserver.zip if not provided
            enable_logging: Whether to enable conversation logging
        """
        self.model_option = model_option
        self.zipped_codebase = zipped_codebase or get_path(
            "assets", "toy-webserver.zip"
        )
        self.enable_logging = enable_logging
        self._agent = None
        self._receiver: Optional[MessageReceiver] = None

    def validate_codebase(self) -> tuple[bool, Optional[str]]:
        """Validate that the codebase file exists.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not Path(self.zipped_codebase).exists():
            return False, f"Test file '{self.zipped_codebase}' not found"
        return True, None

    def run_analysis(self) -> Iterator[AgentMessage]:
        """Run the bug analysis and yield messages.

        Yields:
            AgentMessage events from the agent

        Raises:
            Exception: If analysis fails
        """
        try:
            logger.info(f"Starting analysis with model: {self.model_option.value}")
            logger.info(f"Using codebase: {self.zipped_codebase}")

            # Validate codebase first
            is_valid, error = self.validate_codebase()
            if not is_valid:
                logger.error(f"Codebase validation failed: {error}")
                raise ValueError(error)

            logger.info("Codebase validation successful")

            # Create agent and get receiver
            self._agent, self._receiver = create_agent(
                codebase_path=self.zipped_codebase, model=self.model_option
            )

            logger.info("Agent created successfully, starting analysis...")

            # Start agent
            with self._agent:
                # Start analysis in background and yield messages as they come
                import queue
                import threading
                import time

                def run_agent_with_sandbox():
                    """Run agent analysis with proper sandbox startup."""
                    try:
                        # Context manager starts the sandbox; avoid double start
                        self._agent.run_analysis()
                    except Exception as e:
                        logger.error(f"Agent analysis failed: {e}")
                        raise

                analysis_thread = threading.Thread(target=run_agent_with_sandbox)
                analysis_thread.start()

                # Yield messages in real-time without busy-waiting
                while True:
                    try:
                        # Block briefly for a message; timeout avoids deadlock at end
                        message = self._receiver.get_message(timeout=0.5)
                        yield message
                    except queue.Empty:
                        # No message within timeout; check for termination condition
                        if not analysis_thread.is_alive() and self._receiver.empty():
                            break
                    except Exception as e:
                        logger.error(f"Error receiving message: {e}")
                        if not analysis_thread.is_alive() and self._receiver.empty():
                            break

                # Wait for analysis to complete
                analysis_thread.join()
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            raise
        finally:
            self._agent = None
            self._receiver = None

    @staticmethod
    def map_model_name_to_option(model_name: str) -> ModelOptions:
        """Map UI model names to ModelOptions enum.

        Args:
            model_name: Display name of the model

        Returns:
            Corresponding ModelOptions enum value
        """
        model_map = {
            "Qwen3 480B A35B Coder": ModelOptions.QWEN3_480B_A35B_CODER,
            "Qwen3 235B A22B Instruct": ModelOptions.QWEN3_235B_A22B_INSTRUCT,
            "Qwen3 30B A3B Instruct": ModelOptions.QWEN3_30B_A3B_INSTRUCT,
        }
        return model_map.get(model_name, ModelOptions.QWEN3_30B_A3B_INSTRUCT)
