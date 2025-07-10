from prreview.review.reviewer import Reviewer

def main() -> None:
    reviewer = Reviewer()

    reviewer.run(repo_path="./.input_codebase", base_branch="main", head_branch="dev")



