from pathlib import Path

import git
import json

from prreview.review.diff_analyzer import diff_hunks
from prreview.review.context_selector import select_context
from prreview.index.indexer import Indexer
from prreview.llm.qwen import Qwen3Model


class Reviewer:
    def __init__(self):
        # Database path will be created inside the target repository
        self.db_path: Path | None = None
        self.llm = Qwen3Model()

    def run(self, repo_path: str, base_branch: str, head_branch: str):

        print(f"Reviewing {repo_path} from {base_branch} to {head_branch}")

        # ------------------------------------------------------------------
        # 1) Run the indexer so later stages can access metadata
        # ------------------------------------------------------------------
        self.db_path = Path(repo_path) / ".prreview.sqlite"
        Indexer(self.db_path).run(repo_path)

        repo = git.Repo(repo_path)

        # ------------------------------------------------------------------
        # 2) get diff hunks (Tier 0 inputs)
        # ------------------------------------------------------------------
        hunks = diff_hunks(Path(repo_path), base_branch, head_branch)
        if not hunks:
            print("No file changes detected.")
            return

        # ------------------------------------------------------------------
        # 3) select context chunks (Tier 0 + Tier 1 for now)
        #    Later this will query the indexer metadata DB.
        # ------------------------------------------------------------------
        ctx = select_context(self.db_path, hunks, Path(repo_path))

        # ------------------------------------------------------------------
        # 4) Print diff + context (Milestone 1 goal)
        # ------------------------------------------------------------------
        diff_txt = repo.git.diff(f"{base_branch}..{head_branch}")
        print(f"\n{diff_txt}")

        for h in hunks:
            path, start, end = h
            print(f"\n--- {path}:{start}-{end} (diff hunk) ---")
        for chunk in ctx:
            print(
                f"\n### {chunk.file_path}:{chunk.start_line}-{chunk.end_line}\n{chunk.text}"
            )

        # ------------------------------------------------------------------
        # 5) Generate review text via Qwen3 (Milestone 3)
        # ------------------------------------------------------------------
        review = self.llm.generate_review(diff_txt, ctx)
        print("\nLLM Review:")
        print(json.dumps(review, indent=2))
