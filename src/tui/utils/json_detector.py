"""Utilities for detecting and parsing JSON in streaming text."""

import json
import re
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ContentSplit:
    """Result of splitting content into text and JSON parts."""
    prefix_text: str  # Text before JSON
    json_content: str  # The JSON part
    has_json: bool    # Whether JSON was found
    json_start_pos: int  # Position where JSON starts
    is_complete_json: bool  # Whether JSON appears complete


class JSONDetector:
    """Detects and extracts JSON from streaming text content."""
    
    # Common patterns that indicate JSON is starting
    JSON_INTRO_PATTERNS = [
        r"here\s+is\s+.*?json",
        r"json\s+format",
        r"json\s+response",
        r"json\s+report",
        r"analysis\s+in\s+json",
        r"review\s+in\s+json",
        r"following\s+json",
        r"json\s+below"
    ]
    
    def __init__(self):
        self.brace_stack = []
        self.in_string = False
        self.escape_next = False
    
    def find_json_start(self, content: str) -> Optional[int]:
        """Find the position where JSON likely starts."""
        content_lower = content.lower()
        
        # Look for JSON introduction patterns
        for pattern in self.JSON_INTRO_PATTERNS:
            matches = list(re.finditer(pattern, content_lower))
            if matches:
                # Look for opening brace after the pattern
                last_match = matches[-1]
                search_start = last_match.end()
                
                # Find the first '{' after the intro pattern
                json_start = content.find('{', search_start)
                if json_start != -1:
                    return json_start
        
        # Fallback: look for standalone opening brace
        # But only if it looks like it's starting a substantial JSON object
        for i, char in enumerate(content):
            if char == '{':
                # Check if this looks like a JSON start
                # (not just a brace in regular text)
                before = content[:i].strip()
                if (before.endswith(':') or 
                    before.endswith('json') or
                    before.endswith('format') or
                    len(before) == 0 or
                    before[-20:].lower().find('json') != -1):
                    return i
        
        return None
    
    def is_complete_json(self, json_str: str) -> bool:
        """Check if the JSON string is complete and valid."""
        try:
            json.loads(json_str)
            return True
        except json.JSONDecodeError:
            return False
    
    def find_json_end(self, content: str, start_pos: int) -> Optional[int]:
        """Find where the JSON ends by tracking braces."""
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i in range(start_pos, len(content)):
            char = content[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\' and in_string:
                escape_next = True
                continue
            
            if char == '"':
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return i + 1  # Include the closing brace
        
        return None
    
    def split_content(self, content: str) -> ContentSplit:
        """Split content into text prefix and JSON parts."""
        json_start = self.find_json_start(content)
        
        if json_start is None:
            return ContentSplit(
                prefix_text=content,
                json_content="",
                has_json=False,
                json_start_pos=-1,
                is_complete_json=False
            )
        
        prefix_text = content[:json_start].strip()
        
        # Try to find the end of JSON
        json_end = self.find_json_end(content, json_start)
        
        if json_end is not None:
            json_content = content[json_start:json_end]
            is_complete = self.is_complete_json(json_content)
        else:
            # JSON appears to be incomplete
            json_content = content[json_start:]
            is_complete = False
        
        return ContentSplit(
            prefix_text=prefix_text,
            json_content=json_content,
            has_json=True,
            json_start_pos=json_start,
            is_complete_json=is_complete
        )
    
    def parse_json(self, json_str: str) -> Optional[Dict[str, Any]]:
        """Parse JSON string safely."""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return None


# Global instance
json_detector = JSONDetector()