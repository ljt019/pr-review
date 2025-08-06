#!/usr/bin/env python3
"""
Dynamic evaluation runner that generates bug zips on-the-fly from .bugs_in_py.
No local zip storage required!
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import io

from agent import SniffAgent
from agent.agent import ModelOptions
from agent.evals import BugDetectionEvaluator
from paths import get_path


def parse_model_response(raw: str) -> Dict[str, Any]:
    """Extract and parse the first JSON object in a model response.

    The LLM often sends explanatory prose before the JSON payload. This helper
    skips everything before the first '{' and then attempts to parse the JSON
    incrementally with ijson (stream-based parser). If ijson is unavailable we
    fall back to the standard json library.
    """
    # Locate beginning of JSON object
    start_idx = raw.find("{")
    if start_idx == -1:
        raise ValueError("No JSON object found in model response")

    json_chunk = raw[start_idx:]

    # Try incremental parsing with ijson
    try:
        import ijson  # type: ignore
    except ImportError:
        # Install ijson on the fly (mirrors behaviour elsewhere in this script)
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "ijson"],
            check=True,
            capture_output=True,
        )
        import ijson  # type: ignore

    try:
        # The empty prefix ('') returns the first complete JSON value in the stream
        return next(ijson.items(io.StringIO(json_chunk), ""))
    except Exception:
        # Fall back to stdlib json for unexpected structures
        return json.loads(json_chunk)


def get_available_projects() -> Dict[str, int]:
    """Get all available projects and their bug counts."""
    info_file = Path("evals/dataset/all_projects_info.json")
    if info_file.exists():
        with open(info_file, "r") as f:
            data = json.load(f)
            return data["projects"]

    # Fallback to checking directory
    bugs_in_py_path = Path("evals/dataset/.bugs_in_py/projects")
    projects = {}

    for project_dir in bugs_in_py_path.iterdir():
        if project_dir.is_dir():
            bugs_dir = project_dir / "bugs"
            if bugs_dir.exists():
                bug_count = len(
                    [d for d in bugs_dir.iterdir() if d.is_dir() and d.name.isdigit()]
                )
                if bug_count > 0:
                    projects[project_dir.name] = bug_count

    return projects


def checkout_bug_to_zip(project: str, bug_id: int, output_path: Path) -> bool:
    """
    Checkout a bug directly using git and create a zip file.
    Returns True if successful.
    """
    # Get bug info from .bugs_in_py
    bugsinpy_path = Path("evals/dataset/.bugs_in_py")
    bug_info_path = (
        bugsinpy_path / "projects" / project / "bugs" / str(bug_id) / "bug.info"
    )
    project_info_path = bugsinpy_path / "projects" / project / "project.info"

    if not bug_info_path.exists():
        print(f"  Error: Bug info file not found: {bug_info_path}")
        return False

    if not project_info_path.exists():
        print(f"  Error: Project info file not found: {project_info_path}")
        return False

    # Parse bug.info to get commit hash
    with open(bug_info_path, "r") as f:
        bug_info_content = f.read()

    # Parse project.info to get repository URL
    with open(project_info_path, "r") as f:
        project_info_content = f.read()

    import re

    buggy_commit_match = re.search(r'buggy_commit_id="([^"]+)"', bug_info_content)
    github_url_match = re.search(r'github_url="([^"]+)"', project_info_content)

    if not buggy_commit_match or not github_url_match:
        print("  Error: Could not parse bug info or project info file")
        return False

    buggy_commit = buggy_commit_match.group(1)
    github_url = github_url_match.group(1)

    # Create a temporary directory for checkout
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir) / project

        try:
            # Use GitPython for better handling
            try:
                import git
            except ImportError:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "GitPython"],
                    check=True,
                    capture_output=True,
                )
                import git

            # Clone and checkout silently
            repo = git.Repo.clone_from(github_url, project_dir, no_checkout=True)
            try:
                repo.git.checkout(buggy_commit)
            except git.exc.GitCommandError:
                repo.remote().fetch(unshallow=True)
                repo.git.checkout(buggy_commit)

            # Remove .git directory to save space
            git_dir = project_dir / ".git"
            if git_dir.exists():
                try:
                    shutil.rmtree(git_dir)
                except PermissionError:
                    pass  # Ignore permission errors

            # Create zip file
            zip_base = str(output_path.with_suffix(""))
            shutil.make_archive(zip_base, "zip", temp_dir, project)
            return True

        except Exception as e:
            print(f"  Error during checkout: {e}")
            return False


def get_or_create_ground_truth(project: str) -> Optional[Dict[str, Any]]:
    """
    Get ground truth for a project. Create it if it doesn't exist.
    """
    ground_truth_path = Path(f"evals/dataset/{project}/ground-truth.json")

    if ground_truth_path.exists():
        with open(ground_truth_path, "r") as f:
            return json.load(f)

    # Generate ground truth from .bugs_in_py
    print(f"  Generating ground truth for {project}...")

    bugs_dir = Path(f"evals/dataset/.bugs_in_py/projects/{project}/bugs")
    if not bugs_dir.exists():
        print(f"  Error: No bugs directory found for {project}")
        return None

    bugs = []
    for bug_dir in sorted(
        bugs_dir.iterdir(), key=lambda x: int(x.name) if x.name.isdigit() else 0
    ):
        if bug_dir.is_dir() and bug_dir.name.isdigit():
            bug_num = int(bug_dir.name)

            # Read bug.info if it exists
            bug_info_path = bug_dir / "bug.info"
            buggy_commit = ""
            fixed_commit = ""

            if bug_info_path.exists():
                with open(bug_info_path, "r") as f:
                    content = f.read()
                    # Extract commits
                    import re

                    buggy_match = re.search(r'buggy_commit_id="([^"]+)"', content)
                    fixed_match = re.search(r'fixed_commit_id="([^"]+)"', content)
                    if buggy_match:
                        buggy_commit = buggy_match.group(1)
                    if fixed_match:
                        fixed_commit = fixed_match.group(1)

            bugs.append(
                {
                    "bug_id": f"{project}-{bug_num}",
                    "project": project,
                    "file_path": "unknown",  # Would need to parse patch
                    "line_start": 0,
                    "line_end": 0,
                    "description": f"Bug #{bug_num} from BugsInPy dataset",
                    "category": "unknown",
                    "severity": "major",
                    "commit_buggy": buggy_commit,
                    "commit_fixed": fixed_commit,
                }
            )

    ground_truth = {"project": project, "version": "1.0", "bugs": bugs}

    # Save for future use
    ground_truth_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ground_truth_path, "w") as f:
        json.dump(ground_truth, f, indent=2)

    return ground_truth


def run_single_evaluation(
    project: str,
    bug_id: int,
    model_option: ModelOptions,
    output_dir: Path,
    keep_zip: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Run evaluation on a single bug, generating the zip on-the-fly.
    """
    bug_name = f"{project}-bug{bug_id}"
    print(f"  Evaluating {bug_name}...", end=" ", flush=True)

    # Create bug-specific output directory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    eval_output_dir = output_dir / f"eval_{bug_name}_{timestamp}"
    eval_output_dir.mkdir(parents=True, exist_ok=True)

    # Create temporary zip file
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_zip = Path(temp_dir) / f"{bug_name}.zip"

        # Generate the zip from .bugs_in_py
        if not checkout_bug_to_zip(project, bug_id, temp_zip):
            print("FAILED (checkout)")
            return None

        # Optionally keep the zip for debugging
        if keep_zip:
            kept_zip = eval_output_dir / f"{bug_name}.zip"
            shutil.copy2(temp_zip, kept_zip)

        try:
            # Initialize agent and run analysis
            agent = SniffAgent(str(temp_zip), model_option)
            model_response_raw = agent.run(save_response=False)

            if not model_response_raw:
                print("FAILED (no response)")
                return None

            # Parse model response (handles non-JSON prelude)
            try:
                model_response = parse_model_response(model_response_raw)
            except Exception as e:
                print("FAILED (parse error)")
                with open(eval_output_dir / "model_response_raw.txt", "w") as f:
                    f.write(model_response_raw)
                return None

            # Save model response
            with open(eval_output_dir / "model_response.json", "w") as f:
                json.dump(model_response, f, indent=2)

            # Get ground truth
            ground_truth = get_or_create_ground_truth(project)
            if not ground_truth:
                print("FAILED (no ground truth)")
                return None

            # Find specific bug in ground truth
            bug_ground_truth = None
            for bug in ground_truth["bugs"]:
                if bug["bug_id"] == f"{project}-{bug_id}":
                    bug_ground_truth = bug
                    break

            if not bug_ground_truth:
                print("FAILED (bug not found)")
                return None

            # Create temporary ground truth with just this bug
            temp_ground_truth = {
                "project": project,
                "version": ground_truth["version"],
                "bugs": [bug_ground_truth],
            }

            temp_ground_truth_path = eval_output_dir / "ground_truth.json"
            with open(temp_ground_truth_path, "w") as f:
                json.dump(temp_ground_truth, f, indent=2)

            # Run evaluation
            evaluator = BugDetectionEvaluator(str(temp_ground_truth_path))
            evaluation_result = evaluator.evaluate(model_response)

            # Convert to dict once for reuse
            evaluation_dict = evaluation_result.to_dict()

            # Save evaluation results
            with open(eval_output_dir / "evaluation.json", "w") as f:
                json.dump(evaluation_dict, f, indent=2)

            # Save summary
            with open(eval_output_dir / "summary.txt", "w") as f:
                f.write(evaluator.get_summary(evaluation_result))

            # Print compact results
            precision = evaluation_dict["summary"]["precision"]
            recall = evaluation_dict["summary"]["recall"]
            f1 = evaluation_dict["summary"]["f1_score"]
            files = model_response.get("files_analyzed", 0)

            print(f"P:{precision:.2f} R:{recall:.2f} F1:{f1:.2f} Files:{files}")

            return evaluation_dict

        finally:
            if "agent" in locals():
                agent._cleanup()


def run_project_evaluation(
    project: str,
    bug_ids: List[int],
    model_option: ModelOptions,
    output_dir: Path,
    keep_zips: bool = False,
) -> None:
    """Run evaluation on multiple bugs from a project."""

    print(f"\n{project.upper()} ({len(bug_ids)} bugs)")
    print("-" * 40)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    project_output_dir = output_dir / f"eval_{project}_{timestamp}"
    project_output_dir.mkdir(parents=True, exist_ok=True)

    # Track results
    all_results = []
    successful_evals = 0

    for i, bug_id in enumerate(bug_ids, 1):
        print(f"[{i:2d}/{len(bug_ids)}]", end="")
        result = run_single_evaluation(
            project, bug_id, model_option, project_output_dir, keep_zips
        )

        if result:
            all_results.append({"bug_id": bug_id, "result": result})
            successful_evals += 1

    # Calculate aggregate results
    if successful_evals > 0:
        total_precision = sum(r["result"]["summary"]["precision"] for r in all_results)
        total_recall = sum(r["result"]["summary"]["recall"] for r in all_results)
        total_f1 = sum(r["result"]["summary"]["f1_score"] for r in all_results)

        aggregate_results = {
            "project": project,
            "model": model_option.value,
            "timestamp": timestamp,
            "bugs_evaluated": bug_ids,
            "successful_evaluations": successful_evals,
            "aggregate_metrics": {
                "avg_precision": total_precision / successful_evals,
                "avg_recall": total_recall / successful_evals,
                "avg_f1_score": total_f1 / successful_evals,
            },
            "individual_results": all_results,
        }

        with open(project_output_dir / "aggregate_results.json", "w") as f:
            json.dump(aggregate_results, f, indent=2)

        # Print compact summary
        avg_p = aggregate_results["aggregate_metrics"]["avg_precision"]
        avg_r = aggregate_results["aggregate_metrics"]["avg_recall"]
        avg_f1 = aggregate_results["aggregate_metrics"]["avg_f1_score"]

        print(f"\nSUMMARY: {successful_evals}/{len(bug_ids)} successful")
        print(f"Average P:{avg_p:.2f} R:{avg_r:.2f} F1:{avg_f1:.2f}")
        print(f"Results: {project_output_dir.name}")


def main():
    # Get available projects
    available_projects = get_available_projects()

    parser = argparse.ArgumentParser(
        description="Run bug detection evaluation with dynamic zip generation from .bugs_in_py"
    )
    parser.add_argument(
        "--project",
        type=str,
        required=True,
        help=f"Project(s) to evaluate. Use comma-separated list for multiple projects (e.g., 'black,fastapi') or 'all' for all projects. Available: {', '.join(available_projects.keys())}, all",
    )
    parser.add_argument(
        "--bugs",
        type=str,
        help="Comma-separated list of bug IDs (e.g., '1,2,3') or range (e.g., '1-5')",
    )
    parser.add_argument(
        "--all", action="store_true", help="Evaluate all bugs for the project"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="qwen3-30b",
        choices=["qwen3-480b", "qwen3-235b", "qwen3-30b"],
        help="Model to use",
    )
    parser.add_argument(
        "--output", type=str, default="evals/output", help="Output directory"
    )
    parser.add_argument(
        "--keep-zips",
        action="store_true",
        help="Keep generated zip files for debugging",
    )

    args = parser.parse_args()

    # Map model choice
    model_map = {
        "qwen3-480b": ModelOptions.QWEN3_480B_A35B_CODER,
        "qwen3-235b": ModelOptions.QWEN3_235B_A22B_INSTRUCT,
        "qwen3-30b": ModelOptions.QWEN3_30B_A3B_INSTRUCT,
    }
    model_option = model_map[args.model]

    # Parse project list
    if args.project == "all":
        projects_to_evaluate = sorted(available_projects.keys())
    else:
        projects_to_evaluate = [p.strip() for p in args.project.split(",")]

    # Validate projects
    invalid_projects = [p for p in projects_to_evaluate if p not in available_projects]
    if invalid_projects:
        print(f"Error: Invalid project(s): {invalid_projects}")
        print(f"Available projects: {', '.join(available_projects.keys())}")
        sys.exit(1)

    # Handle multiple projects case
    if len(projects_to_evaluate) > 1:
        total_bugs = sum(available_projects[p] for p in projects_to_evaluate)
        print(
            f"\nEvaluating {len(projects_to_evaluate)} projects ({total_bugs} total bugs)"
        )
        print(f"Model: {model_option.value}")

        for project_name in projects_to_evaluate:
            # Determine bugs for this project
            if args.all or (args.bugs and args.bugs.lower() == "all"):
                bug_ids = list(range(1, available_projects[project_name] + 1))
            elif args.bugs:
                bug_ids = []
                for part in args.bugs.split(","):
                    part = part.strip()
                    if part.lower() == "all":
                        # Handle "all" in comma-separated list
                        bug_ids = list(range(1, available_projects[project_name] + 1))
                        break
                    elif "-" in part:
                        start, end = map(int, part.split("-"))
                        bug_ids.extend(range(start, end + 1))
                    else:
                        bug_ids.append(int(part))

                # Validate bug IDs for this project (only if not "all")
                if not (args.bugs and args.bugs.lower() == "all"):
                    max_bugs = available_projects[project_name]
                    invalid_bugs = [b for b in bug_ids if b < 1 or b > max_bugs]
                    if invalid_bugs:
                        print(
                            f"Warning: Invalid bug IDs for {project_name}: {invalid_bugs} (max: {max_bugs})"
                        )
                        bug_ids = [b for b in bug_ids if 1 <= b <= max_bugs]
                        if not bug_ids:
                            print(f"No valid bugs for {project_name}, skipping...")
                            continue
            else:
                print(f"Error: Must specify --bugs or --all for {project_name}")
                continue

            run_project_evaluation(
                project_name, bug_ids, model_option, Path(args.output), args.keep_zips
            )

        print(f"\n" + "=" * 60)
        print(f"Completed {len(projects_to_evaluate)} projects")
        print("=" * 60)
        return

    # Single project evaluation
    project = projects_to_evaluate[0]

    # Determine which bugs to evaluate
    if args.all:
        bug_ids = list(range(1, available_projects[project] + 1))
    elif args.bugs:
        bug_ids = []
        for part in args.bugs.split(","):
            part = part.strip()
            if part.lower() == "all":
                # Handle "all" in comma-separated list
                bug_ids = list(range(1, available_projects[project] + 1))
                break
            elif "-" in part:
                start, end = map(int, part.split("-"))
                bug_ids.extend(range(start, end + 1))
            else:
                bug_ids.append(int(part))
    else:
        print("Error: Must specify either --bugs or --all")
        parser.print_help()
        sys.exit(1)

    # Validate bug IDs
    max_bugs = available_projects[project]
    invalid_bugs = [b for b in bug_ids if b < 1 or b > max_bugs]
    if invalid_bugs:
        print(f"Error: Invalid bug IDs for {project}: {invalid_bugs}")
        print(f"Valid range: 1-{max_bugs}")
        sys.exit(1)

    # Run evaluation
    run_project_evaluation(
        project, bug_ids, model_option, Path(args.output), args.keep_zips
    )


if __name__ == "__main__":
    main()
