"""
Professional bug matching system using semantic similarity and multiple strategies.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass
class BugMatch:
    """Represents a match between detected and ground truth bug"""

    detected_bug: Dict
    ground_truth_bug: Dict
    match_score: float
    match_reasons: List[str]


class SemanticBugMatcher:
    """Matches detected bugs to ground truth using semantic similarity and multiple strategies"""

    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        """Initialize with a sentence transformer model for semantic matching"""
        try:
            self.embedder = SentenceTransformer(embedding_model)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load embedding model '{embedding_model}': {e}"
            ) from e

        # Vulnerability type patterns with enhanced category coverage
        self.vulnerability_patterns = {
            "sql_injection": [
                r"sql.{0,20}injection",
                r"string.{0,20}formatting.{0,20}quer",
                r"f.?string.{0,20}quer",
                r"concatenat.{0,20}quer",
                r"parameterized.{0,20}quer",
            ],
            "hardcoded_secret": [
                r"hardcoded.{0,20}(secret|password|key|credential)",
                r"(secret|password|key).{0,20}(hardcoded|plain.?text)",
                r"credential.{0,20}source.?code",
            ],
            "command_injection": [
                r"command.{0,20}injection",
                r"shell.{0,20}true",
                r"subprocess.{0,20}shell",
                r"os\.system",
            ],
            "pickle_vulnerability": [
                r"pickle.{0,20}(unsafe|security|deserializ)",
                r"deserializ.{0,20}untrusted",
                r"arbitrary.{0,20}code.{0,20}execution",
            ],
        }

        # Enhanced category-specific detection patterns to address 0% recall categories
        self.category_patterns = {
            "performance": [
                r"rate.{0,20}limit(?:ing)?",
                r"timeout",
                r"batch.{0,20}(?:operation|query)",
                r"inefficient",
                r"n\+1",
                r"optimization",
                r"slow.{0,20}query",
                r"memory.{0,20}leak",
                r"high.{0,20}cpu",
                r"per.{0,20}request",
                r"loop.{0,20}(?:per|each)",
                r"cache.{0,20}(?:miss|invalidat)",
                r"(?:database|db).{0,20}(?:call|query).*(?:loop|each)",
                r"automatic.{0,20}save",
                r"frequent.{0,20}(?:save|write)",
            ],
            "validation": [
                r"input.{0,20}validation",
                r"sanitiz",
                r"file.{0,20}size",
                r"type.{0,20}check",
                r"format.{0,20}validation",
                r"bounds.{0,20}check",
                r"length.{0,20}validation",
                r"whitelist",
                r"blacklist",
                r"no.{0,20}validation",
                r"(?:size|type).{0,20}validation",
                r"path.{0,20}validation",
                r"email.{0,20}validation",
                r"backup.{0,20}(?:path|file)",
                r"config.{0,20}validation",
            ],
            "error_handling": [
                r"exception.{0,20}handling",
                r"try.{0,20}catch",
                r"error.{0,20}suppress",
                r"silent.{0,20}fail",
                r"broad.{0,20}except",
                r"bare.{0,20}except",
                r"error.{0,20}handling",
                r"fault.{0,20}tolerance",
                r"(?:except|catch).*(?:pass|ignore)",
                r"\bpass\b.*exception",
                r"swallow(?:ed|ing)",
                r"missing.{0,20}error",
            ],
            "resource_management": [
                r"resource.{0,20}leak",
                r"file.{0,20}handle",
                r"connection.{0,20}pool",
                r"memory.{0,20}management",
                r"garbage.{0,20}collection",
                r"cleanup",
                r"(?:connection|socket|file).{0,20}(?:not.{0,20})?clos(?:e|ed|ing)",
                r"(?:resource|handle).{0,20}cleanup",
                r"(?:set|assign).{0,20}none",
            ],
            "authorization": [
                r"access.{0,20}control",
                r"permission.{0,20}check",
                r"privilege.{0,20}escalation",
                r"authorization",
                r"rbac",
                r"role.{0,20}based",
                r"(?:missing|no).{0,20}(?:authorization|permission)",
                r"requesting.{0,20}user",
                r"verify.{0,20}permission",
            ],
            "reliability": [
                r"timeout",
                r"hang(?:ing)?",
                r"request.{0,20}timeout",
                r"(?:connection|network).{0,20}(?:timeout|hang)",
                r"prevent.{0,20}hanging",
                r"reliability",
                r"fault.{0,20}tolerance",
            ],
            "dead_code": [
                r"dead.{0,20}code",
                r"unused",
                r"unreachable",
                r"never.{0,20}(?:used|called|reached)",
                r"obsolete",
                r"(?:import|function|method).{0,20}(?:not|never).{0,20}used",
                r"after.{0,20}return",
                r"unreachable.{0,20}code",
            ],
        }

    def normalize_file_path(self, path: str) -> str:
        """Normalize file paths for comparison"""
        if not path:
            return ""
        # Remove leading/trailing slashes and backslashes
        path = path.strip("/\\")
        # Convert backslashes to forward slashes
        path = path.replace("\\", "/")
        # Remove ./ prefix if present
        if path.startswith("./"):
            path = path[2:]
        return path.lower()

    def extract_line_numbers(self, line_str: str) -> set:
        """Extract line numbers from various formats (single, range, comma-separated)"""
        numbers = set()
        if not line_str:
            return numbers

        line_str = str(line_str)

        # Handle single number
        if line_str.isdigit():
            numbers.add(int(line_str))
        # Handle ranges like "20-25"
        elif "-" in line_str:
            parts = line_str.split("-")
            if len(parts) == 2:
                try:
                    start = int(parts[0].strip())
                    end = int(parts[1].strip())
                    numbers.update(range(start, end + 1))
                except ValueError:
                    pass
        # Handle comma-separated numbers
        elif "," in line_str:
            for part in line_str.split(","):
                if part.strip().isdigit():
                    numbers.add(int(part.strip()))

        # Also extract any numbers from the string
        for num in re.findall(r"\d+", line_str):
            numbers.add(int(num))

        return numbers

    def location_similarity(self, detected: Dict, truth: Dict) -> float:
        """Calculate location similarity based on file and line proximity"""
        # File must match
        detected_file = self.normalize_file_path(detected.get("file", ""))
        truth_file = self.normalize_file_path(truth.get("file", ""))

        if detected_file != truth_file:
            return 0.0

        # Extract line numbers
        detected_lines = self.extract_line_numbers(detected.get("line", ""))
        truth_lines = self.extract_line_numbers(truth.get("line", ""))

        if not detected_lines or not truth_lines:
            # If no line numbers, but same file, give more generous credit
            return 0.5

        # Calculate proximity score
        min_distance = float("inf")
        for d_line in detected_lines:
            for t_line in truth_lines:
                distance = abs(d_line - t_line)
                min_distance = min(min_distance, distance)

        # More generous proximity scoring to improve recall
        if min_distance == 0:
            return 1.0
        elif min_distance <= 3:
            return 0.9  # Increased from 0.8
        elif min_distance <= 8:
            return 0.7  # Increased from 0.6
        elif min_distance <= 15:
            return 0.5  # Increased from 0.4
        else:
            # Same file but far apart - still give some credit
            return 0.3

    def normalize_security_terms(
        self, text: str, term_mappings: Dict[str, List[str]]
    ) -> str:
        """Normalize domain-specific terms for better matching"""
        normalized_text = text.lower()
        for main_term, alternatives in term_mappings.items():
            for alt_term in alternatives:
                normalized_text = normalized_text.replace(alt_term, main_term)
        return normalized_text

    def semantic_similarity(self, detected: Dict, truth: Dict) -> float:
        """Calculate semantic similarity between bug descriptions with enhanced term matching"""

        # Combine relevant text for detected bug
        detected_text = " ".join(
            filter(
                None,
                [
                    detected.get("title", ""),
                    detected.get("description", ""),
                    detected.get("recommendation", ""),
                    f"severity: {detected.get('severity', '')}",
                    f"category: {detected.get('category', '')}",
                ],
            )
        )

        # Combine relevant text for ground truth
        truth_text = " ".join(
            filter(
                None,
                [
                    truth.get("description", ""),
                    truth.get("code_snippet", ""),
                    truth.get("recommendation", ""),
                    f"severity: {truth.get('severity', '')}",
                    f"category: {truth.get('category', '')}",
                ],
            )
        )

        if not detected_text or not truth_text:
            return 0.0

        # Enhanced semantic matching with comprehensive domain-specific term mappings
        term_mappings = {
            "url parameters": ["query parameters", "get parameters", "url params"],
            "exposed": ["leaked", "visible", "accessible", "logged"],
            "api key": ["authentication token", "auth key", "access token"],
            "hardcoded": ["hard-coded", "hard coded", "embedded", "static"],
            "password": ["credential", "secret", "auth"],
            "injection": ["command injection", "code injection", "script injection"],
            "timeout": ["hang", "hanging", "blocking", "freeze"],
            "validation": ["sanitization", "verification", "checking"],
            "exception": ["error", "failure", "crash"],
            "resource": ["handle", "connection", "memory", "file"],
            "cleanup": ["close", "release", "free"],
            "authorization": ["permission", "access control", "privilege"],
            "performance": ["efficiency", "optimization", "speed"],
            "dead code": ["unused", "unreachable", "obsolete"],
            "n+1": ["loop query", "per request", "inefficient loop"],
            "broad exception": ["generic exception", "catch all", "bare except"],
        }

        # Apply term normalization
        detected_text = self.normalize_security_terms(detected_text, term_mappings)
        truth_text = self.normalize_security_terms(truth_text, term_mappings)

        try:
            # Get embeddings
            embeddings = self.embedder.encode([detected_text, truth_text])

            # Calculate cosine similarity
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )

            return float(similarity)
        except Exception as e:
            print(f"Error calculating semantic similarity: {e}")
            return 0.0

    def pattern_similarity(self, detected: Dict, truth: Dict) -> float:
        """Check if bugs match known vulnerability and category patterns"""
        detected_text = (
            detected.get("description", "") + " " + detected.get("title", "")
        ).lower()
        truth_text = (
            truth.get("description", "") + " " + truth.get("code_snippet", "")
        ).lower()

        detected_patterns = set()
        truth_patterns = set()

        # Find matching vulnerability patterns
        for vuln_type, patterns in self.vulnerability_patterns.items():
            for pattern in patterns:
                if re.search(pattern, detected_text, re.IGNORECASE):
                    detected_patterns.add(vuln_type)
                if re.search(pattern, truth_text, re.IGNORECASE):
                    truth_patterns.add(vuln_type)

        # Find matching category patterns
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if re.search(pattern, detected_text, re.IGNORECASE):
                    detected_patterns.add(category)
                if re.search(pattern, truth_text, re.IGNORECASE):
                    truth_patterns.add(category)

        if not detected_patterns and not truth_patterns:
            # No patterns found, neutral score
            return 0.5

        if detected_patterns & truth_patterns:
            # Matching vulnerability types or categories
            return 1.0
        else:
            return 0.0

    def category_similarity(self, detected: Dict, truth: Dict) -> float:
        """Check if bug categories match"""
        detected_cat = detected.get("category", "").lower()
        truth_cat = truth.get("category", "").lower()

        if not detected_cat or not truth_cat:
            return 0.5  # Neutral if missing

        if detected_cat == truth_cat:
            return 1.0

        # Check for similar categories
        similar_categories = {
            "security": ["authentication", "authorization", "injection", "crypto"],
            "validation": ["input validation", "sanitization", "verification"],
            "error_handling": ["exception", "error handling", "fault tolerance"],
        }

        for main_cat, related in similar_categories.items():
            if detected_cat == main_cat and truth_cat in related:
                return 0.7
            if truth_cat == main_cat and detected_cat in related:
                return 0.7

        return 0.0

    def severity_similarity(self, detected: Dict, truth: Dict) -> float:
        """Check if bug severities match or are close"""
        severity_map = {"critical": 3, "major": 2, "minor": 1}

        detected_sev = detected.get("severity", "").lower()
        truth_sev = truth.get("severity", "").lower()

        if not detected_sev or not truth_sev:
            return 0.5  # Neutral if missing

        detected_val = severity_map.get(detected_sev, 0)
        truth_val = severity_map.get(truth_sev, 0)

        if detected_val == truth_val:
            return 1.0
        elif abs(detected_val - truth_val) == 1:
            return 0.7  # Off by one severity level
        else:
            return 0.3

    def calculate_match_score(
        self, detected: Dict, truth: Dict
    ) -> Tuple[float, List[str]]:
        """Calculate overall match score using weighted combination of strategies"""
        scores = {
            "location": self.location_similarity(detected, truth),
            "semantic": self.semantic_similarity(detected, truth),
            "pattern": self.pattern_similarity(detected, truth),
            "category": self.category_similarity(detected, truth),
            "severity": self.severity_similarity(detected, truth),
        }

        # Rebalanced weights for fairer matching across all bug categories
        weights = {
            "location": 0.30,  # Increased - location is very reliable
            "semantic": 0.40,  # Most important for understanding
            "pattern": 0.15,  # Reduced to prevent security bias
            "category": 0.10,  # Helpful but not decisive
            "severity": 0.05,  # Reduced - can vary and less critical for matching
        }

        # Calculate weighted score
        total_score = sum(scores[k] * weights[k] for k in scores)

        # Determine match reasons
        reasons = []
        for strategy, score in scores.items():
            if score >= 0.7:
                reasons.append(f"{strategy}_match(score={score:.2f})")

        return total_score, reasons

    def get_adaptive_threshold(self, truth_bug: Dict) -> float:
        """Get category and severity-specific threshold for better matching"""
        # More balanced thresholds across categories to reduce bias
        category_thresholds = {
            "security": 0.62,  # Slightly higher to reduce false positives
            "performance": 0.60,  # Reduced to improve recall
            "validation": 0.60,  # Reduced for better recall
            "error_handling": 0.60,  # Reduced for better recall
            "resource_management": 0.60,  # Reduced for better recall
            "authorization": 0.62,  # Balanced with security
            "reliability": 0.60,  # Reduced for better recall
            "dead_code": 0.65,  # Slightly higher - dead code is specific
        }

        category = truth_bug.get("category", "").lower()
        base_threshold = category_thresholds.get(
            category, 0.60
        )  # Lower default threshold

        # More conservative severity-based adjustments
        severity = truth_bug.get("severity", "").lower()
        if severity == "critical":
            return base_threshold - 0.03  # Smaller adjustment for critical issues
        elif severity == "minor":
            return base_threshold + 0.03  # Smaller adjustment for minor issues

        return base_threshold

    def match_bugs(
        self,
        detected_bugs: List[Dict],
        ground_truth_bugs: List[Dict],
        threshold: float = 0.65,
    ) -> Dict:
        """
        Match detected bugs to ground truth bugs.
        Returns evaluation results with detailed matching information.
        """
        results = {
            "matches": [],
            "unmatched_detected": [],
            "unmatched_truth": [],
            "match_details": [],
        }

        # Track which bugs have been matched
        matched_truth_indices = set()
        matched_detected_indices = set()

        # Create match matrix
        match_scores = []
        for i, detected in enumerate(detected_bugs):
            row = []
            for j, truth in enumerate(ground_truth_bugs):
                score, reasons = self.calculate_match_score(detected, truth)
                row.append((score, reasons))
            match_scores.append(row)

        # Greedy matching: pick best matches first
        while True:
            best_score = -1
            best_i = -1
            best_j = -1

            # Find best remaining match
            for i in range(len(detected_bugs)):
                if i in matched_detected_indices:
                    continue
                for j in range(len(ground_truth_bugs)):
                    if j in matched_truth_indices:
                        continue
                    score = match_scores[i][j][0]
                    adaptive_threshold = self.get_adaptive_threshold(
                        ground_truth_bugs[j]
                    )
                    if score > best_score and score >= adaptive_threshold:
                        best_score = score
                        best_i = i
                        best_j = j

            # No more good matches
            if best_i == -1:
                break

            # Record match
            match = BugMatch(
                detected_bug=detected_bugs[best_i],
                ground_truth_bug=ground_truth_bugs[best_j],
                match_score=best_score,
                match_reasons=match_scores[best_i][best_j][1],
            )
            results["matches"].append(match)
            results["match_details"].append(
                {
                    "detected": detected_bugs[best_i],
                    "truth": ground_truth_bugs[best_j],
                    "score": best_score,
                    "reasons": match_scores[best_i][best_j][1],
                }
            )

            matched_detected_indices.add(best_i)
            matched_truth_indices.add(best_j)

        # Record unmatched bugs
        for i, bug in enumerate(detected_bugs):
            if i not in matched_detected_indices:
                results["unmatched_detected"].append(bug)

        for j, bug in enumerate(ground_truth_bugs):
            if j not in matched_truth_indices:
                results["unmatched_truth"].append(bug)

        return results
