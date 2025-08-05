"""Evaluation metrics for bug detection system."""

import json
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any
from datetime import datetime

from .ground_truth import BugGroundTruth


@dataclass 
class DetectionMatch:
    """Represents a match between detected and ground truth bug."""
    detected_bug: Dict[str, Any]
    ground_truth_bug: BugGroundTruth
    match_score: float
    match_type: str  # "exact", "partial", "semantic"


@dataclass
class EvaluationMetrics:
    """Comprehensive evaluation metrics."""
    
    # Basic counts
    total_ground_truth: int
    total_detected: int
    true_positives: int
    false_positives: int
    false_negatives: int
    
    # Calculated metrics  
    precision: float
    recall: float
    f1_score: float
    
    # Detailed results
    matches: List[DetectionMatch]
    unmatched_detections: List[Dict[str, Any]]
    missed_ground_truth: List[BugGroundTruth]
    
    # File analysis
    files_analyzed: int
    files_with_bugs: int
    
    # Metadata
    evaluation_timestamp: str
    model_response: Dict[str, Any]
    
    @classmethod
    def calculate(
        cls,
        detected_bugs: List[Dict[str, Any]],
        ground_truth_bugs: List[BugGroundTruth],
        files_analyzed: int,
        model_response: Dict[str, Any]
    ) -> "EvaluationMetrics":
        """Calculate evaluation metrics from detections and ground truth."""
        
        matches = []
        unmatched_detections = []
        matched_gt_ids = set()
        
        # Match detected bugs to ground truth
        for detected in detected_bugs:
            best_match = None
            best_score = 0.0
            
            for gt_bug in ground_truth_bugs:
                if gt_bug.bug_id in matched_gt_ids:
                    continue
                    
                score = cls._calculate_match_score(detected, gt_bug)
                if score > best_score and score >= 0.7:  # Threshold for valid match
                    best_score = score
                    best_match = gt_bug
            
            if best_match:
                match_type = "exact" if best_score >= 0.95 else "partial"
                matches.append(DetectionMatch(
                    detected_bug=detected,
                    ground_truth_bug=best_match,
                    match_score=best_score,
                    match_type=match_type
                ))
                matched_gt_ids.add(best_match.bug_id)
            else:
                unmatched_detections.append(detected)
        
        # Find missed ground truth bugs
        missed_ground_truth = [
            gt_bug for gt_bug in ground_truth_bugs 
            if gt_bug.bug_id not in matched_gt_ids
        ]
        
        # Calculate metrics
        tp = len(matches)
        fp = len(unmatched_detections) 
        fn = len(missed_ground_truth)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # File statistics
        files_with_bugs = len(set(gt_bug.file_path for gt_bug in ground_truth_bugs))
        
        return cls(
            total_ground_truth=len(ground_truth_bugs),
            total_detected=len(detected_bugs),
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            matches=matches,
            unmatched_detections=unmatched_detections,
            missed_ground_truth=missed_ground_truth,
            files_analyzed=files_analyzed,
            files_with_bugs=files_with_bugs,
            evaluation_timestamp=datetime.now().isoformat(),
            model_response=model_response
        )
    
    @staticmethod
    def _calculate_match_score(detected: Dict[str, Any], ground_truth: BugGroundTruth) -> float:
        """Calculate match score between detected bug and ground truth.""" 
        score = 0.0
        
        # File path match (40% weight)
        detected_file = detected.get("file", "").strip()
        if detected_file == ground_truth.file_path:
            score += 0.4
        elif ground_truth.file_path in detected_file or detected_file in ground_truth.file_path:
            score += 0.2
        
        # Line number match (30% weight)
        detected_line = detected.get("line", "")
        if detected_line:
            try:
                if "-" in str(detected_line):
                    # Range like "621-636"  
                    start, end = map(int, str(detected_line).split("-"))
                    gt_range = range(ground_truth.line_start, (ground_truth.line_end or ground_truth.line_start) + 1)
                    detected_range = range(start, end + 1)
                    
                    # Check for overlap
                    overlap = set(gt_range) & set(detected_range)
                    if overlap:
                        overlap_ratio = len(overlap) / max(len(gt_range), len(detected_range))
                        score += 0.3 * overlap_ratio
                else:
                    # Single line number
                    line_num = int(str(detected_line))
                    if ground_truth.line_start <= line_num <= (ground_truth.line_end or ground_truth.line_start):
                        score += 0.3
            except (ValueError, TypeError):
                pass
        
        # Category match (20% weight)
        detected_category = detected.get("category", "").lower()
        if detected_category == ground_truth.category.lower():
            score += 0.2
        
        # Severity match (10% weight)  
        detected_severity = detected.get("severity", "").lower()
        if detected_severity == ground_truth.severity.lower():
            score += 0.1
        
        return min(score, 1.0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return {
            "summary": {
                "precision": round(self.precision, 3),
                "recall": round(self.recall, 3), 
                "f1_score": round(self.f1_score, 3),
                "true_positives": self.true_positives,
                "false_positives": self.false_positives,
                "false_negatives": self.false_negatives
            },
            "analysis": {
                "total_ground_truth_bugs": self.total_ground_truth,
                "total_detected_bugs": self.total_detected,
                "files_analyzed": self.files_analyzed,
                "files_with_bugs": self.files_with_bugs
            },
            "matches": [
                {
                    "detected": match.detected_bug,
                    "ground_truth": {
                        "bug_id": match.ground_truth_bug.bug_id,
                        "file": match.ground_truth_bug.file_path,
                        "line_range": f"{match.ground_truth_bug.line_start}-{match.ground_truth_bug.line_end or match.ground_truth_bug.line_start}",
                        "description": match.ground_truth_bug.description,
                        "category": match.ground_truth_bug.category,
                        "severity": match.ground_truth_bug.severity
                    },
                    "match_score": round(match.match_score, 3),
                    "match_type": match.match_type
                }
                for match in self.matches
            ],
            "false_positives": self.unmatched_detections,
            "false_negatives": [
                {
                    "bug_id": bug.bug_id,
                    "file": bug.file_path,
                    "line_range": f"{bug.line_start}-{bug.line_end or bug.line_start}",
                    "description": bug.description,
                    "category": bug.category,
                    "severity": bug.severity
                }
                for bug in self.missed_ground_truth
            ],
            "metadata": {
                "evaluation_timestamp": self.evaluation_timestamp,
                "model_response": self.model_response
            }
        }