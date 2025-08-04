import json5
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ParameterParser:
    """Shared utility for parsing tool parameters."""
    
    @staticmethod
    def parse_params(params: str) -> Dict[str, Any]:
        """
        Parse parameters as JSON5.
        
        Args:
            params: Raw parameter string from tool call
            
        Returns:
            Dict containing parsed parameters
            
        Raises:
            ValueError: If parameters cannot be parsed
        """
        logger.debug(f"Parsing params: {params}")
        
        # Handle empty params
        if not params or params.strip() == "":
            raise ValueError("Parameters are required")
        
        try:
            parsed_params = json5.loads(params)
            logger.debug(f"Successfully parsed JSON5: {parsed_params}")
            return parsed_params
        except Exception as parse_error:
            raise ValueError(f"Invalid parameters format: {parse_error}")
    
    @staticmethod
    def get_required_param(parsed_params: Dict[str, Any], key: str) -> Any:
        """
        Get a required parameter, raising ValueError if missing.
        
        Args:
            parsed_params: Dictionary of parsed parameters
            key: Parameter key to retrieve
            
        Returns:
            Parameter value
            
        Raises:
            ValueError: If required parameter is missing
        """
        value = parsed_params.get(key)
        if value is None:
            raise ValueError(f"{key} parameter is required")
        return value
    
    @staticmethod
    def get_optional_param(parsed_params: Dict[str, Any], key: str, default: Any = None) -> Any:
        """
        Get an optional parameter with default value.
        
        Args:
            parsed_params: Dictionary of parsed parameters
            key: Parameter key to retrieve
            default: Default value if parameter is missing
            
        Returns:
            Parameter value or default
        """
        return parsed_params.get(key, default)