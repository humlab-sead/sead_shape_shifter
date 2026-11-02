---
name: create-change-pr
description: Commit uncommitted work to a new branch and merge it into dev through a pull request, using scripts/create_change_pr.py. Use when the user has local changes that must reach dev through review, or when a direct commit to dev would break later promotion to staging. Do not use for promotion pull requests (dev into staging or staging into main) or for reviewing pull requests.
---

# Create A Change Pull Request

Move uncommitted work onto a branch and merge it into `dev` through a pull
request. The mechanical steps are in `scripts/create_change_pr.py`; this skill
covers the decisions that the script cannot make for you.

## Why A Pull Request Into Dev

`docs`-level rules allow commits directly on `dev`, but
`scripts/verify_promotion_provenance.sh` runs on every promotion pull request and
fails when a commit touching `scripts/`, `src/`, `backend/`, `frontend/`,
`ingesters/`, `tests/`, or `.github/workflows/` reached `dev` without its own
pull request. Unrecorded commits block `dev` into `staging`.

So: any change touching those paths goes through a branch and a pull request
into `dev`, even when it looks like maintenance.

## Steps

1. Read the working tree once, then choose the paths.
2. Pass one `--path` per file or directory that belongs to the change.
3. Choose the commit type and subject.
4. Run the script with `--dry-run`, read the printed plan and pull request body.
5. Run it for real, then report the pull request number.

```bash
uv run python scripts/create_change_pr.py \
  --type chore \
  --scope deps \
  --subject "upgrade dev tooling and adapt code to new checks" \
  --path uv.lock \
  --path src/loaders \
  --path src/specifications \
  --validation "uv run pylint -j 0 src tests backend ingesters: exit 0" \
  --dry-run
```

## Choosing Paths

- Default to naming paths with `--path`. The script refuses the literal blanket
  value `.`, and unrelated work must stay uncommitted.
- Use `--all` only when every pending change really is one logical commit. It is
  mutually exclusive with `--path`, and it stages the whole working tree, so read
  the `--dry-run` file list before running it for real.
- Name a directory only when every pending file under it belongs to the change.
- Leave unrelated modified files out, and mention them in the handoff.
- If two unrelated concerns are mixed in the tree, run the workflow twice.

## Choosing Type And Subject

- `feat`, `fix` — behavior changes users or API callers can notice.
- `chore` — dependency, tooling, and lockfile maintenance.
- `refactor`, `perf`, `style` — internal changes with no new behavior.
- `test`, `docs`, `build`, `ci` — the suite, documentation, packaging, workflow.
- Subject is lowercase imperative mood, no trailing period, and the full line
  stays within 72 characters, including `type(scope): `. The script rejects
  violations instead of rewriting them.
- `--generate-subject` drafts the subject from the pending diff instead, and
  makes `--type`, `--scope`, and `--subject` optional. Use it for fast-track
  maintenance commits. Read the drafted subject in the `--dry-run` output before
  running for real: it goes into `git log` permanently, and it is a model
  suggestion, not a verified description of the change. If it misrepresents the
  work, rerun with an explicit `--subject` rather than accepting it.

A dependency upgrade that forces code edits stays one commit, because the edits
exist only to satisfy the upgraded tools.

## Pull Request Body

- The script writes the four sections required by
  `.github/pull_request_template.md` in the required order.
- `--summary` defaults to the commit subject. Pass a real summary for anything
  larger than a one-line change.
- Pass `--release-note` and `--upgrade-notes` only when the impact is known. The
  script otherwise writes the template's "not verified" fallback text, which is
  correct rather than guessed.
- Pass each check actually run as `--validation`. Do not list checks that were
  not run, and do not describe unverified results.
- `--default-validation` adds the two repository default lines before any
  `--validation` lines: `uv run pylint -j 0 src tests backend ingesters: exit 0`
  and `pytest: all passed`. The script never executes them, so run both
  commands first and only use the flag when their real outcome matches. Pass
  `--validation` instead when the evidence is narrower, since the default pytest
  line claims the whole configured test path set.

## Copilot Description

`--generate-description` runs `scripts/update_pr_descriptions.py <n> --draft`
followed by `--publish` after the pull request exists. It reads
`REPO_SCRIPTS_DEFAULT_*` from the repository-root `.env` or the equivalent
`COPILOT_PROVIDER_*` variables; the values may be quoted and may have spaces
around `=`, so grep for the key name rather than `KEY=`. If the settings are
absent or the endpoint is unreachable, the step warns and the scaffold body
stays, which is not a workflow failure.

When the description is generated, read the published result before reporting
success. The draft file is committed to the pull request branch by default, so
the pull request carries its own record; pass `--no-commit-description-draft`
when the user does not want a second commit.

## Merge

- Default is a merge commit into `dev`, matching repository history.
- `--no-merge` opens the pull request and stops; use it when the user wants to
  review first.
- `gh pr merge --delete-branch` also switches the checkout to the pull request
  base branch, runs `git pull --ff-only`, and deletes the local head branch. After
  a default run you are already on `dev` and up to date, so do not tell the user
  to switch again.
- With `--keep-branch` gh does not switch, so the checkout stays on the head
  branch and the script prints the `git switch` step needed to get back to `dev`.
- If merge fails, the script prints the pull request number and the command to
  retry. Do not rewrite history or force-push to recover.

## Boundaries

- Promotions (`dev` into `staging`, `staging` into `main`) use
  `.github/promotion_pr_template.md` and a separate pull request. The script
  refuses those base branches on purpose.
- Never commit credentials, `.env` files, or connection strings.
- Report the pull request number and the validation actually run. Do not claim a
  merge or a passing check without the command output that shows it.
