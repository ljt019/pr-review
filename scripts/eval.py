import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from paths import get_assets_path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bug_bot.bug_bot import BugBot

# Import semantic evaluation system
from bug_bot.evaluation.evaluator import BugDetectionEvaluator
from paths import EVALS_DIR, get_eval_path

# Load environment variables from .env file
load_dotenv()

zipped_codebase_path = get_assets_path("toy-webserver.zip")


def parse_model_response(response: str) -> dict:
    """Parse the model's JSON response"""
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # If parsing fails, return empty structure
        return {"bugs": [], "nitpicks": []}


def save_evaluation_results(results: dict, eval_dir: Path):
    """Save evaluation results in the same evaluation directory"""
    eval_filepath = eval_dir / "evaluation.json"

    with open(eval_filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    try:
        print(f"\n💾 Evaluation saved to: {eval_filepath}")
    except UnicodeEncodeError:
        print(f"\nEvaluation saved to: {eval_filepath}")


def main():
    """Run bug bot evaluation with semantic grading"""
    try:
        print("Starting bug bot evaluation...")

        # Run the bot
        bot = BugBot(zipped_codebase_path)
        result = bot.run(save_response=True)

        # Parse the model response
        model_response = parse_model_response(result)

        # Use semantic evaluator
        ground_truth_path = str(get_eval_path("bugs_ground_truth.json"))
        evaluator = BugDetectionEvaluator(ground_truth_path)
        evaluation_results = evaluator.evaluate_response(model_response)

        # Handle Unicode encoding issues on Windows
        report = evaluator.format_report(evaluation_results)
        try:
            print(report)
        except UnicodeEncodeError:
            # Fallback: replace problematic characters
            report_ascii = report.encode("ascii", "replace").decode("ascii")
            print(report_ascii)

        # Save evaluation results - find the latest eval directory
        if EVALS_DIR.exists():
            # Find the latest evaluation directory
            eval_dirs = [d for d in EVALS_DIR.iterdir() if d.is_dir()]
            if eval_dirs:
                latest_eval_dir = sorted(eval_dirs, key=lambda d: d.name)[-1]
                save_evaluation_results(evaluation_results, latest_eval_dir)

    except Exception as e:
        print(f"Error during evaluation: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if "bot" in locals():
            bot._cleanup()


if __name__ == "__main__":
    main()
