# pr-review

A minimal prototype for a pull request review bot.

Running `uv run pr-review` will analyze the repository passed on the command
line and print the diff between two branches along with surrounding context and
semantic neighbours.

```bash
uv run pr-review -- --repo-path path/to/repo --base-branch main --head-branch dev
```

The first run builds a small SQLite metadata DB (`.prreview.sqlite`) plus a
vector store (`.prreview.hnsw` + `.prreview.vec.sqlite`) inside the target
repository.
