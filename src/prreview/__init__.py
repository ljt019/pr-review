from prreview.review.reviewer import Reviewer

REPO_PATH = "./.input_codebase"
BASE_BRANCH = "main"
HEAD_BRANCH = "dev"



def main() -> None:
    """Run the PR reviewer on *repo_path* between two branches."""
    reviewer = Reviewer()
    reviewer.run(repo_path=REPO_PATH, base_branch=BASE_BRANCH, head_branch=HEAD_BRANCH)



