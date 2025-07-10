# pr-review

A minimal prototype for a pull request review bot.

Running `uv run pr-review` will analyze the repository in `./.input_codebase`
and print the git diff between `main` and `dev` followed by simple context
windows around each modified hunk. The command also builds a metadata index in
`.prreview.sqlite` inside the target repository for use in later milestones.
