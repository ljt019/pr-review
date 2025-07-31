"""
Main evaluation engine that uses the bug matcher to evaluate model responses.
"""
import json
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from paths import get_eval_path
from .bug_matcher import SemanticBugMatcher


class BugDetectionEvaluator:
    """Evaluates bug detection model performance against ground truth"""
    
    def __init__(self, ground_truth_path: Optional[str] = None):
        """Initialize evaluator with ground truth data"""
        if ground_truth_path is None:
            ground_truth_path = str(get_eval_path("bugs_ground_truth.json"))
        self.ground_truth = self._load_ground_truth(ground_truth_path)
        self.matcher = SemanticBugMatcher()
    
    def _load_ground_truth(self, filepath: str) -> Dict:
        """Load ground truth bugs from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def evaluate_response(self, model_response: Dict) -> Dict:
        """Evaluate a model response against ground truth"""
        # Extract bugs from model response
        detected_bugs = model_response.get('bugs', [])
        ground_truth_bugs = self.ground_truth.get('bugs', [])
        
        # Perform matching
        match_results = self.matcher.match_bugs(
            detected_bugs, 
            ground_truth_bugs,
            threshold=0.65  # Configurable threshold
        )
        
        # Calculate metrics
        tp = len(match_results['matches'])
        fp = len(match_results['unmatched_detected'])
        fn = len(match_results['unmatched_truth'])
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # Calculate metrics by severity
        severity_metrics = self._calculate_severity_metrics(match_results)
        
        # Calculate metrics by category
        category_metrics = self._calculate_category_metrics(match_results)
        
        return {
            'summary': {
                'total_ground_truth_bugs': len(ground_truth_bugs),
                'total_detected_bugs': len(detected_bugs),
                'true_positives': tp,
                'false_positives': fp,
                'false_negatives': fn,
                'precision': precision,
                'recall': recall,
                'f1_score': f1_score
            },
            'by_severity': severity_metrics,
            'by_category': category_metrics,
            'matches': match_results['match_details'],
            'false_positives': match_results['unmatched_detected'],
            'missed_bugs': match_results['unmatched_truth']
        }
    
    def _calculate_severity_metrics(self, match_results: Dict) -> Dict:
        """Calculate performance metrics by severity level"""
        severities = ['critical', 'major', 'minor']
        metrics = {}
        
        for severity in severities:
            # Count ground truth bugs of this severity
            truth_count = sum(1 for bug in self.ground_truth['bugs'] 
                            if bug.get('severity') == severity)
            
            # Count matched bugs of this severity
            matched_count = sum(1 for match in match_results['matches']
                              if match.ground_truth_bug.get('severity') == severity)
            
            recall = matched_count / truth_count if truth_count > 0 else 0.0
            
            metrics[severity] = {
                'found': matched_count,
                'total': truth_count,
                'recall': recall
            }
        
        return metrics
    
    def _calculate_category_metrics(self, match_results: Dict) -> Dict:
        """Calculate performance metrics by bug category"""
        categories = {}
        
        # Count ground truth bugs by category
        for bug in self.ground_truth['bugs']:
            category = bug.get('category', 'unknown')
            if category not in categories:
                categories[category] = {'total': 0, 'found': 0}
            categories[category]['total'] += 1
        
        # Count matched bugs by category
        for match in match_results['matches']:
            category = match.ground_truth_bug.get('category', 'unknown')
            if category in categories:
                categories[category]['found'] += 1
        
        # Calculate recall for each category
        for category in categories:
            total = categories[category]['total']
            found = categories[category]['found']
            categories[category]['recall'] = found / total if total > 0 else 0.0
        
        return categories
    
    def _wilson_confidence_interval(self, successes: int, total: int, z: float = 1.96) -> Tuple[float, float]:
        """Calculate Wilson score confidence interval for binomial proportion"""
        if total == 0:
            return 0.0, 0.0
        
        p = successes / total
        z_squared = z * z
        denominator = 1 + z_squared / total
        center = p + z_squared / (2 * total)
        half_width = z * math.sqrt((p * (1 - p) + z_squared / (4 * total)) / total)
        
        lower = (center - half_width / denominator) / denominator
        upper = (center + half_width / denominator) / denominator
        
        return max(0.0, lower), min(1.0, upper)
    
    def format_report(self, evaluation_results: Dict) -> str:
        """Format evaluation results as a readable report"""
        report = []
        report.append("\n" + "="*60)
        report.append("EVALUATION REPORT")
        report.append("="*60)
        
        # Summary metrics
        summary = evaluation_results['summary']
        report.append("\n📊 SUMMARY METRICS:")
        report.append(f"  Total Ground Truth Bugs: {summary['total_ground_truth_bugs']}")
        report.append(f"  Total Detected Bugs: {summary['total_detected_bugs']}")
        report.append(f"  True Positives: {summary['true_positives']}")
        report.append(f"  False Positives: {summary['false_positives']}")
        report.append(f"  False Negatives: {summary['false_negatives']}")
        
        # Add statistical significance
        tp, fp, fn = summary['true_positives'], summary['false_positives'], summary['false_negatives']
        total_detections = tp + fp
        total_truth = tp + fn
        
        # Wilson score confidence intervals for precision and recall
        precision_ci = self._wilson_confidence_interval(tp, total_detections) if total_detections > 0 else (0, 0)
        recall_ci = self._wilson_confidence_interval(tp, total_truth) if total_truth > 0 else (0, 0)
        
        report.append(f"\n  🎯 Precision: {summary['precision']:.2%} (95% CI: {precision_ci[0]:.2%}-{precision_ci[1]:.2%})")
        report.append(f"  🎯 Recall: {summary['recall']:.2%} (95% CI: {recall_ci[0]:.2%}-{recall_ci[1]:.2%})")
        report.append(f"  🎯 F1 Score: {summary['f1_score']:.2%}")
        
        # Statistical assessment
        if total_truth < 20:
            report.append(f"  ⚠️  Small sample size (n={total_truth}) - results may have high uncertainty")
        if summary['precision'] < 0.7 or summary['recall'] < 0.3:
            report.append(f"  ⚠️  Performance concerns detected - consider ground truth review")
        
        # Performance by severity
        report.append("\n📈 PERFORMANCE BY SEVERITY:")
        for severity in ['critical', 'major', 'minor']:
            data = evaluation_results['by_severity'][severity]
            report.append(f"  {severity.upper()}: {data['found']}/{data['total']} found (Recall: {data['recall']:.2%})")
        
        # Performance by category
        report.append("\n📂 PERFORMANCE BY CATEGORY:")
        sorted_categories = sorted(evaluation_results['by_category'].items(), 
                                 key=lambda x: x[1]['recall'], reverse=True)
        for category, data in sorted_categories:
            report.append(f"  {category}: {data['found']}/{data['total']} found (Recall: {data['recall']:.2%})")
        
        # Sample matches with reasons
        if evaluation_results['matches']:
            report.append("\n✅ SAMPLE MATCHES (showing match reasons):")
            for match in evaluation_results['matches'][:3]:
                report.append(f"\n  Detected: {match['detected'].get('title', 'No title')}")
                report.append(f"  Matched to: {match['truth'].get('id', 'Unknown')} - {match['truth'].get('description', '')[:60]}...")
                report.append(f"  Score: {match['score']:.2f}")
                report.append(f"  Reasons: {', '.join(match['reasons'])}")
        
        # Missed critical bugs
        critical_missed = [bug for bug in evaluation_results['missed_bugs'] 
                          if bug.get('severity') == 'critical']
        if critical_missed:
            report.append("\n⚠️  MISSED CRITICAL BUGS:")
            for bug in critical_missed[:5]:  # Show up to 5
                report.append(f"  - {bug['id']}: {bug['description'][:60]}...")
                report.append(f"    File: {bug['file']}, Line: {bug['line']}")
        
        # False positives
        if evaluation_results['false_positives']:
            report.append(f"\n❌ FALSE POSITIVES ({len(evaluation_results['false_positives'])}):")
            for bug in evaluation_results['false_positives'][:3]:
                report.append(f"  - {bug.get('title', 'No title')}")
                report.append(f"    File: {bug.get('file', 'Unknown')}, Line: {bug.get('line', 'Unknown')}")
        
        report.append("\n" + "="*60)
        
        return '\n'.join(report)