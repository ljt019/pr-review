import click

from prreview.review.reviewer import Reviewer


@click.command()
@click.option("--repo-path", default="./.input_codebase", help="Target repository")
@click.option("--base-branch", default="main", help="Base branch")
@click.option("--head-branch", default="dev", help="Head branch")
def main(repo_path: str, base_branch: str, head_branch: str) -> None:
    """Run the PR reviewer on *repo_path* between two branches."""
    reviewer = Reviewer()
    reviewer.run(repo_path=repo_path, base_branch=base_branch, head_branch=head_branch)



