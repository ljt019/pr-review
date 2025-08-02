"""
Response saving functionality for bug detection results.
Handles file organization, directory creation, and JSON serialization.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import json5

from paths import EVALS_DIR


def save_response(
    response_data: Dict[str, Any],
    project_root: str,
    model_name: str = "qwen/qwen3-30b-a3b-instruct-2507",
) -> Optional[str]:
    """
    Save bug detection response to organized file structure.

    Args:
        response_data: Response data (raw text or structured dict)
        project_root: Root directory of the project
        model_name: Name of the model used for analysis

    Returns:
        File path where response was saved, or None if failed
    """

    try:
        # Create evals directory structure with individual eval folder
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        eval_dir = EVALS_DIR / timestamp
        eval_dir.mkdir(parents=True, exist_ok=True)

        # Create filename
        filename = "model-response.json"
        filepath = eval_dir / filename

        # Add run metadata to the response
        if isinstance(response_data, dict):
            response_data["run_metadata"] = {
                "timestamp": datetime.now().isoformat(),
                "eval_id": timestamp,
                "model": model_name,
            }

        # Save to file
        with open(filepath, "w", encoding="utf-8") as f:
            json5.dump(response_data, f, indent=2, ensure_ascii=False)

        return str(filepath)

    except Exception as e:
        print(f"Failed to save response: {e}")
        return None


def create_eval_summary(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a simple summary of the evaluation for quick review.

    Args:
        response_data: Response data (raw text or dict)

    Returns:
        Summary dictionary with basic metrics
    """
    # Handle both string responses and dict responses
    if isinstance(response_data, str):
        return {
            "response_type": "text",
            "response_length": len(response_data),
            "timestamp": datetime.now().isoformat(),
        }

    # For dict responses, extract what we can
    bugs = response_data.get("bugs", [])
    nitpicks = response_data.get("nitpicks", [])

    return {
        "response_type": "structured",
        "total_bugs": len(bugs),
        "total_nitpicks": len(nitpicks),
        "total_issues": len(bugs) + len(nitpicks),
        "timestamp": datetime.now().isoformat(),
    }


def save_response_with_summary(
    response_data: Dict[str, Any],
    project_root: str,
    model_name: str = "qwen/qwen3-30b-a3b-instruct-2507",
) -> Optional[Dict[str, str]]:
    """
    Save response and create summary file.

    Args:
        response_data: Response data (raw text or structured dict)
        project_root: Root directory of the project
        model_name: Name of the model used for analysis

    Returns:
        Dictionary with file paths, or None if failed
    """

    # Save main response
    response_path = save_response(response_data, project_root, model_name)
    if not response_path:
        return None

    try:
        # Create summary
        summary = create_eval_summary(response_data)

        # Save summary file
        eval_dir = Path(response_path).parent
        summary_path = eval_dir / "summary.json"

        with open(summary_path, "w", encoding="utf-8") as f:
            json5.dump(summary, f, indent=2, ensure_ascii=False)

        return {"response": response_path, "summary": str(summary_path)}

    except Exception as e:
        print(f"Failed to save summary: {e}")
        return {"response": response_path}
