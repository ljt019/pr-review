from pathlib import Path
from prreview.review.diff_analyzer import diff_hunks
from prreview.review.context_selector import select_context

class Reviewer:
    def __init__(self):
        # TODO: This will be a real database path later for indexing metadata
        self.db_path = None  # Placeholder for now
   
    def run(self, repo_path: str, base_branch: str, head_branch: str):

        print(f"Reviewing {repo_path} from {base_branch} to {head_branch}")

        # 1) get diff hunks (Tier 0 inputs)
        hunks = diff_hunks(Path(repo_path), base_branch, head_branch)
        if not hunks:
            print("No file changes detected."); return
        
        # 2) select context chunks (Tier 0 + Tier 1 for now)
        #    Later this will query the indexer metadata DB.
        ctx = select_context(self.db_path, hunks, Path(repo_path))

        # 3) Print (Milestone 1 goal)
        for h in hunks:
            path, start, end = h
            print(f"\n--- {path}:{start}-{end} (diff hunk) ---")
        for chunk in ctx:
            print(f"\n### {chunk.file_path}:{chunk.start_line}-{chunk.end_line}\n{chunk.text}")


    

