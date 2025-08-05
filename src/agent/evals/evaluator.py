"""Evaluation system for bug detection agent."""

import json
from pathlib import Path
from typing import Any, Dict

from .ground_truth import GroundTruthManager
from .metrics import EvaluationMetrics


class BugDetectionEvaluator:
    """Evaluator for bug detection performance."""

    def __init__(self, ground_truth_file: str = None):
        """Initialize evaluator with ground truth."""
        self.ground_truth_manager = GroundTruthManager(ground_truth_file)

    def evaluate(
        self, model_response: Dict[str, Any], files_analyzed: int = 0
    ) -> EvaluationMetrics:
        """Evaluate model response against ground truth."""

        # Extract detected bugs from model response
        detected_bugs = model_response.get("bugs", [])

        # Get ground truth bugs
        ground_truth_bugs = self.ground_truth_manager.get_all_bugs()

        # Calculate comprehensive metrics
        metrics = EvaluationMetrics.calculate(
            detected_bugs=detected_bugs,
            ground_truth_bugs=ground_truth_bugs,
            files_analyzed=files_analyzed,
            model_response=model_response,
        )

        return metrics

    def save_evaluation(self, metrics: EvaluationMetrics, output_path: str) -> None:
        """Save evaluation results to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(metrics.to_dict(), f, indent=2, ensure_ascii=False)

    def print_summary(self, metrics: EvaluationMetrics) -> None:
        """Print evaluation summary to console."""
        summary = self.get_summary(metrics)
        print(summary)

    def get_summary(self, metrics: EvaluationMetrics) -> str:
        """Return a plain-text summary of the evaluation metrics."""
        lines: list[str] = []
        lines.append("\n" + "=" * 60)
        lines.append("BUG DETECTION EVALUATION RESULTS")
        lines.append("=" * 60)

        lines.append("\nOVERALL PERFORMANCE")
        lines.append(f"   Precision: {metrics.precision:.3f}")
        lines.append(f"   Recall:    {metrics.recall:.3f}")
        lines.append(f"   F1-Score:  {metrics.f1_score:.3f}")

        lines.append("\nDETECTION BREAKDOWN")
        lines.append(f"   True Positives:  {metrics.true_positives}")
        lines.append(f"   False Positives: {metrics.false_positives}")
        lines.append(f"   False Negatives: {metrics.false_negatives}")

        lines.append("\nANALYSIS SCOPE")
        lines.append(f"   Files Analyzed:    {metrics.files_analyzed}")
        lines.append(f"   Files with Bugs:   {metrics.files_with_bugs}")
        lines.append(f"   Ground Truth Bugs: {metrics.total_ground_truth}")
        lines.append(f"   Detected Bugs:     {metrics.total_detected}")

        if metrics.matches:
            lines.append(f"\nSUCCESSFUL DETECTIONS ({len(metrics.matches)})")
            for i, match in enumerate(metrics.matches, 1):
                gt = match.ground_truth_bug
                lines.append(f"   {i}. {gt.file_path}:{gt.line_start}")
                lines.append(
                    f"      Match Score: {match.match_score:.3f} ({match.match_type})"
                )
                lines.append(f"      Category: {gt.category} | Severity: {gt.severity}")

        if metrics.missed_ground_truth:
            lines.append(f"\nMISSED BUGS ({len(metrics.missed_ground_truth)})")
            for i, bug in enumerate(metrics.missed_ground_truth, 1):
                lines.append(f"   {i}. {bug.file_path}:{bug.line_start}")
                lines.append(f"      {bug.description[:80]}...")
                lines.append(
                    f"      Category: {bug.category} | Severity: {bug.severity}"
                )

        if metrics.unmatched_detections:
            lines.append(f"\nFALSE POSITIVES ({len(metrics.unmatched_detections)})")
            for i, detection in enumerate(metrics.unmatched_detections, 1):
                file_path = detection.get("file", "unknown")
                line = detection.get("line", "unknown")
                title = detection.get("title", "Untitled")
                lines.append(f"   {i}. {file_path}:{line}")
                lines.append(f"      {title}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
