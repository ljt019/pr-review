"""Utilities for detecting and parsing JSON in streaming text using ijson."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import io

import ijson
from ijson.common import JSONError, IncompleteJSONError


@dataclass
class ContentSplit:
    """Result of splitting content into text and JSON parts."""

    prefix_text: str  # Text before JSON
    json_content: str  # The JSON part
    has_json: bool  # Whether JSON was found
    json_start_pos: int  # Position where JSON starts
    is_complete_json: bool  # Whether JSON appears complete


class JSONDetector:
    """Detects and extracts JSON from streaming text content."""

    def split_content(self, content: str) -> ContentSplit:
        """Split content into text prefix and JSON parts.

        This scans for potential JSON openings and uses ijson to
        confirm and locate the matching end.
        """

        for idx, char in enumerate(content):
            if char not in "{[":
                continue

            stream = io.StringIO(content[idx:])
            parser = ijson.parse(stream)
            depth = 0
            seen_value = False
            try:
                for _prefix, event, _value in parser:
                    if event in {"start_map", "start_array"}:
                        depth += 1
                    elif event in {"end_map", "end_array"}:
                        depth -= 1
                        if depth == 0:
                            end_pos = idx + stream.tell()
                            return ContentSplit(
                                prefix_text=content[:idx].strip(),
                                json_content=content[idx:end_pos],
                                has_json=True,
                                json_start_pos=idx,
                                is_complete_json=True,
                            )
                    else:
                        # We saw at least one non-structural event, so this looks like JSON
                        seen_value = True
            except IncompleteJSONError:
                if seen_value:
                    # Partial JSON found; return the available tail
                    return ContentSplit(
                        prefix_text=content[:idx].strip(),
                        json_content=content[idx:],
                        has_json=True,
                        json_start_pos=idx,
                        is_complete_json=False,
                    )
                # A lone '{' or '['; treat as plain text
                continue
            except JSONError:
                # Not valid JSON at this position; continue scanning
                continue

        return ContentSplit(
            prefix_text=content,
            json_content="",
            has_json=False,
            json_start_pos=-1,
            is_complete_json=False,
        )

    def parse_json(self, json_str: str) -> Optional[Dict[str, Any]]:
        """Parse JSON string using ijson."""

        try:
            return next(ijson.items(io.StringIO(json_str), ""))
        except (JSONError, StopIteration):
            return None


# Global instance
json_detector = JSONDetector()

