"""Service layer for agent interaction, separating business logic from UI concerns."""

import logging
from pathlib import Path
from typing import Callable, Iterator, Optional

from agent import SniffAgent
from agent.agent import ModelOptions
from agent.messages import BotMessage
from src.paths import get_assets_path

logger = logging.getLogger(__name__)


class AgentService:
    """Handles all agent-related business logic and execution."""

    def __init__(self, model_option: ModelOptions, zipped_codebase: Optional[str] = None):
        """Initialize the agent service.
        
        Args:
            model_option: The model to use for analysis
            zipped_codebase: Path to the zipped codebase to analyze, 
                           defaults to toy-webserver.zip if not provided
        """
        self.model_option = model_option
        self.zipped_codebase = zipped_codebase or get_assets_path("toy-webserver.zip")
        self._agent: Optional[SniffAgent] = None

    def validate_codebase(self) -> tuple[bool, Optional[str]]:
        """Validate that the codebase file exists.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not Path(self.zipped_codebase).exists():
            return False, f"Test file '{self.zipped_codebase}' not found"
        return True, None

    def run_analysis(self) -> Iterator[BotMessage]:
        """Run the bug analysis and yield messages.
        
        Yields:
            BotMessage events from the agent
            
        Raises:
            Exception: If analysis fails
        """
        try:
            with SniffAgent(
                zipped_codebase=self.zipped_codebase, 
                model_option=self.model_option
            ) as self._agent:
                yield from self._agent.run_streaming()
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
        finally:
            self._agent = None

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