---
description: "Use when asked to create a GitHub issue and commit changes, prepare commit messages, or document a change for issue plus commit workflow."
---
# GitHub Workflow

- Use the fast path by default: check status once, understand the scoped files, and avoid extra repo scans unless the change is unclear.
- Stage only files relevant to the requested task; never use `git add .`.
- Leave unrelated user changes unstaged and mention them in the handoff.
- Prefer one atomic Conventional Commit unless the user explicitly asks to split commits.
- Use commit format `<type>(<scope>): <description>` with imperative mood, lowercase description, no trailing period, and subject under 72 characters.
- Include `Closes #<issue>` or `Fixes #<issue>` when the commit should close the related issue. Put it in the commit message, not only in the pull request body: a closing keyword in a pull request into `dev` closes nothing, but the same keyword in the commit message closes the issue when the commit reaches `main` through promotion.
- When a pull request resolves an issue, repeat `Closes #<issue>` in its description so the promotion description can copy it. Prose such as `this fixes #<issue>` is not a closing reference.
- For issue creation, keep the body concise with three sections: `Problem`, `Solution`, and `Files`.
- If `gh issue create` is needed, prefer `--body-file - <<'EOF'` to avoid shell substitution problems.
- When uncommitted work must reach `dev` through review, run `scripts/create_change_pr.py` instead of assembling branch, commit, push, and `gh pr create` calls by hand. It stages only the `--path` values it is given, refuses blanket paths, and writes the required pull request body sections.
- Pass `--closes <issue>` to that script for every issue the change resolves, so the closing reference reaches both the pull request body and the commit message.
