"""Ground truth management for BugsInPy dataset evaluation."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from paths import get_path


@dataclass
class BugGroundTruth:
    """Represents ground truth for a single bug."""
    bug_id: str
    project: str
    file_path: str
    line_start: int
    line_end: Optional[int]
    description: str
    category: str
    severity: str
    commit_buggy: str
    commit_fixed: str


class GroundTruthManager:
    """Manages ground truth data for evaluation."""
    
    def __init__(self, ground_truth_file: Optional[str] = None):
        """Initialize with ground truth file."""
        if ground_truth_file is None:
            ground_truth_file = str(get_path("evals", "dataset", "ground_truth.json"))
        self.ground_truth_file = Path(ground_truth_file)
        self.bugs: List[BugGroundTruth] = []
        self._load_ground_truth()
    
    def _load_ground_truth(self) -> None:
        """Load ground truth from JSON file."""
        if not self.ground_truth_file.exists():
            self._create_default_ground_truth()
            return
            
        with open(self.ground_truth_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        self.bugs = [
            BugGroundTruth(**bug_data) 
            for bug_data in data.get("bugs", [])
        ]
    
    def _create_default_ground_truth(self) -> None:
        """Create default ground truth for Black bug 1."""
        default_bugs = [
            {
                "bug_id": "black-1",
                "project": "black",
                "file_path": "black.py",
                "line_start": 621,
                "line_end": 636,
                "description": "ProcessPoolExecutor creation can fail on systems that don't support multiprocessing (like AWS Lambda), causing OSError. Missing exception handling leads to crash.",
                "category": "error-handling",
                "severity": "major",
                "commit_buggy": "26c9465a22c732ab1e17b0dec578fa3432e9b558",
                "commit_fixed": "c0a7582e3d4cc8bec3b7f5a6c52b36880dcb57d7"
            }
        ]
        
        ground_truth_data = {
            "project": "black",
            "version": "1.0",
            "bugs": default_bugs
        }
        
        # Ensure directory exists
        self.ground_truth_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.ground_truth_file, 'w', encoding='utf-8') as f:
            json.dump(ground_truth_data, f, indent=2, ensure_ascii=False)
            
        self.bugs = [BugGroundTruth(**bug_data) for bug_data in default_bugs]
    
    def get_bug_by_id(self, bug_id: str) -> Optional[BugGroundTruth]:
        """Get ground truth for specific bug ID."""
        for bug in self.bugs:
            if bug.bug_id == bug_id:
                return bug
        return None
    
    def get_bugs_by_file(self, file_path: str) -> List[BugGroundTruth]:
        """Get all bugs in a specific file."""
        return [bug for bug in self.bugs if bug.file_path == file_path]
    
    def get_all_bugs(self) -> List[BugGroundTruth]:
        """Get all ground truth bugs."""
        return self.bugs.copy()
    
    def add_bug(self, bug: BugGroundTruth) -> None:
        """Add a new bug to ground truth."""
        self.bugs.append(bug)
        self._save_ground_truth()
    
    def _save_ground_truth(self) -> None:
        """Save current ground truth to file."""
        data = {
            "project": "black",
            "version": "1.0", 
            "bugs": [
                {
                    "bug_id": bug.bug_id,
                    "project": bug.project,
                    "file_path": bug.file_path,
                    "line_start": bug.line_start,
                    "line_end": bug.line_end,
                    "description": bug.description,
                    "category": bug.category,
                    "severity": bug.severity,
                    "commit_buggy": bug.commit_buggy,
                    "commit_fixed": bug.commit_fixed
                }
                for bug in self.bugs
            ]
        }
        
        with open(self.ground_truth_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)