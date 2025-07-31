"""
Metadata generation for bug detection results.
Automatically generates metadata based on bug analysis results.
"""

import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import Counter


def generate_metadata(
    bugs: List[Dict[str, Any]], 
    nitpicks: List[Dict[str, Any]], 
    files_analyzed: List[str],
    scan_id: Optional[str] = None,
    model_name: str = "qwen-agent"
) -> Dict[str, Any]:
    """
    Generate metadata for bug detection results.
    
    Args:
        bugs: List of bug dictionaries
        nitpicks: List of nitpick dictionaries  
        files_analyzed: List of file paths that were analyzed
        scan_id: Optional unique identifier for this scan
        model_name: Name of the model used for analysis
        
    Returns:
        Dictionary containing generated metadata
    """
    
    # Count bugs by severity
    severity_counts = Counter(bug.get('severity', 'unknown') for bug in bugs)
    
    # Count bugs by category
    category_counts = Counter(bug.get('category', 'unknown') for bug in bugs)
    
    # Generate scan ID if not provided
    if not scan_id:
        scan_id = f"scan_{int(time.time())}"
    
    # Generate timestamp
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    # Calculate confidence based on bug patterns
    confidence = _calculate_confidence(bugs, nitpicks)
    
    metadata = {
        "scan_id": scan_id,
        "timestamp": timestamp,
        "model": model_name,
        "confidence": confidence,
        "total_bugs": len(bugs),
        "total_nitpicks": len(nitpicks),
        "critical_bugs": severity_counts.get('critical', 0),
        "major_bugs": severity_counts.get('major', 0), 
        "minor_bugs": severity_counts.get('minor', 0),
        "severity_breakdown": dict(severity_counts),
        "category_breakdown": dict(category_counts),
        "files_analyzed": files_analyzed,
        "files_with_bugs": list(set(bug.get('file', '') for bug in bugs if bug.get('file'))),
        "analysis_summary": {
            "total_files": len(files_analyzed),
            "files_with_issues": len(set(bug.get('file', '') for bug in bugs + nitpicks if bug.get('file'))),
            "most_problematic_category": category_counts.most_common(1)[0][0] if category_counts else None
        }
    }
    
    return metadata


def _calculate_confidence(bugs: List[Dict[str, Any]], nitpicks: List[Dict[str, Any]]) -> float:
    """
    Calculate confidence score based on bug detection patterns.
    
    Args:
        bugs: List of detected bugs
        nitpicks: List of detected nitpicks
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    
    base_confidence = 0.7
    
    # Higher confidence for specific, actionable bugs
    specific_indicators = 0
    total_issues = len(bugs) + len(nitpicks)
    
    if total_issues == 0:
        return 0.5  # Neutral confidence when no issues found
    
    for bug in bugs:
        # Check for specific line numbers
        if bug.get('line') and str(bug['line']).isdigit():
            specific_indicators += 1
            
        # Check for specific file paths
        if bug.get('file') and '/' in bug['file']:
            specific_indicators += 0.5
            
        # Check for detailed descriptions
        if bug.get('description') and len(bug['description']) > 50:
            specific_indicators += 0.5
    
    # Boost confidence based on specificity
    specificity_boost = min(0.25, specific_indicators / total_issues * 0.25)
    
    # Adjust based on severity distribution
    severity_counts = Counter(bug.get('severity', 'unknown') for bug in bugs)
    if severity_counts.get('critical', 0) > 0:
        # High confidence for critical bugs if they seem legitimate
        base_confidence += 0.1
    
    final_confidence = min(0.95, base_confidence + specificity_boost)
    return round(final_confidence, 2)


def enhance_bug_report(
    summary: str, 
    bugs: List[Dict[str, Any]], 
    nitpicks: List[Dict[str, Any]],
    files_analyzed: List[str]
) -> Dict[str, Any]:
    """
    Take LLM output and enhance it with automatically generated metadata.
    
    Args:
        summary: Summary text from LLM
        bugs: List of bugs from LLM
        nitpicks: List of nitpicks from LLM
        files_analyzed: List of files that were analyzed
        
    Returns:
        Complete bug report with metadata
    """
    
    metadata = generate_metadata(bugs, nitpicks, files_analyzed)
    
    return {
        "summary": summary,
        "bugs": bugs,
        "nitpicks": nitpicks,
        "metadata": metadata
    }