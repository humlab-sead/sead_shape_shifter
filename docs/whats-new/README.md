# What's New

This directory is for user-facing release notes.

Unlike `CHANGELOG.md`, the files here should be written for normal users rather than developers. The goal is to explain what changed in terms of visible improvements, workflow changes, and upgrade impact.

## Purpose

Use this directory for:

- concise release summaries
- visible new features
- important bug fixes users may notice
- workflow changes
- upgrade notes or cautions

Do not use this directory for:

- exhaustive engineering history
- commit-by-commit detail
- internal refactors with no user impact
- test or maintenance-only changes

## Recommended Structure

- one file per release or per minor version
- stable naming such as `v1.24.0.md` or `2026-03-v1.24.md`
- a short summary at the top
- links to the technical changelog and GitHub release

## Maintaining Release Notes

Changes reach `main` through three stages: a feature branch into `dev`, `dev` into `staging`, and `staging` into `main`. A release note for version `Rn` describes everything that shipped between release `R(n-1)` and release `Rn`.

Commits that reach a base branch without a pull request carry no release note. The generator reports pull requests only, so a direct push is absent from the release note even though it ships. See [Recording Commits Without a Pull Request](#recording-commits-without-a-pull-request) for recording them against the pull request that followed.

1. **Write a note in the change PR.** Complete the `User-facing release note` and `Upgrade notes` sections in [the PR template](../../.github/pull_request_template.md) on the pull request that changes behavior, which is normally the pull request into `dev`. Use one or two plain-language sentences for visible changes. If a PR has no user-visible change or needs no user action, use the exact `None` text in the template.
2. **Promote without repeating notes.** A `dev` into `staging` or `staging` into `main` pull request is a promotion. Use [the promotion template](../../.github/promotion_pr_template.md), keep the `<!-- promotion-pr -->` marker, and list the pull requests it carries under `Included PRs`. Promotion pull requests use the `None` fallbacks for their own note sections; the generator reads notes from the listed pull requests instead, so promoted changes are not reported twice.
3. **Generate the release draft.** During a release, semantic-release runs `scripts/generate_whats_new.py` for the new version. The generator lists merged pull requests whose base branch is `dev`, `staging`, or `main`, then keeps the ones whose merge commit is reachable from the release ref but not from the previous release. Selection therefore follows branch promotion rather than merge dates, so a change merged into `dev` before a release but promoted into `staging` after it is attributed to the release that shipped it. `CHANGELOG.md` supplies the version dates and the previous version; its commit summaries are not used as user-facing content. The generator also adds a `Pending Release` snapshot of pull requests that have not reached `main` yet, including their authored notes and, for promotions, the pull requests they carry. If an AI API key is configured, the generator can consolidate duplicate PR notes; otherwise it preserves the authored notes in the draft.
4. **Review the generated note.** Check that every distinct user-visible change and required upgrade action is represented, and confirm the pending items are not presented as released changes. The generator requires the GitHub CLI to be installed and authenticated so it can read PR descriptions, and it requires local git history and tags because it compares commit ancestry.
5. **Keep the file and release body in sync.** After editing `docs/whats-new/vX.Y.Z.md`, update the GitHub Release body with `gh release edit vX.Y.Z --notes-file docs/whats-new/vX.Y.Z.md`.
6. **Refresh the pending snapshot when needed.** After more PRs merge into `dev` or `staging`, rerun the generator for the latest version. Generation replaces the file, so review and reapply any manual edits afterward.

The release hooks live in `.releaserc.json`. semantic-release runs the generator from `prepareCmd`, which executes before the release tag exists, so the generator falls back to `HEAD` when the `vX.Y.Z` tag is absent. The generator uses heuristic output when no AI API key is configured and falls back to authored notes if AI generation fails. The `gh` CLI must be installed and authenticated. The previous `scripts/generate_user_release_notes.py` remains available for changelog-derived drafts.

The release window can be overridden when the defaults do not fit:

```bash
# Compare a specific pair of refs
python3 scripts/generate_whats_new.py --version 2.5.0 --current-ref v2.5.0 --previous-tag v2.4.0

# Change the branches that carry release-note pull requests
python3 scripts/generate_whats_new.py --version 2.5.0 --source-branches dev,staging,main
```


For manual runs, optional AI mode environment variables are:

- `RELEASE_NOTES_API_KEY` or `OPENAI_API_KEY`
- `RELEASE_NOTES_API_URL` for a custom OpenAI-compatible endpoint
- `RELEASE_NOTES_MODEL` to override the default model
- `RELEASE_NOTES_API_TIMEOUT` to adjust request timeout in seconds

For local runs, the script also checks the repo root `.env` file and loads those variables if they are not already exported in your shell. Exported environment variables still win.

## Copilot CLI Drafting

If you prefer Copilot CLI for the human-in-the-loop drafting step, use:

```bash
python3 scripts/prepare_copilot_release_notes.py --version X.Y.Z

# List versions available in CHANGELOG.md
python3 scripts/prepare_copilot_release_notes.py --list-versions
```

This does two things:

1. Generates a draft release note file.
2. Prints and saves a ready-to-paste Copilot CLI prompt with filtered, user-visible changelog context.

By default it writes:

- `docs/whats-new/vX.Y.Z.md`
- `tmp/copilot-release-notes-vX.Y.Z.prompt.md`

The prompt uses changelog content, not PR-body note sections. Review the resulting release note against the merged PRs before publishing or editing the GitHub Release.

## PR Description Drafts

Generate editable PR descriptions with:

```bash
.venv/bin/python scripts/update_pr_descriptions.py 620-627 --draft
```

The command writes one file per PR to `docs/whats-new/PRs/PR_<number>.txt`. Each file starts with the title on one line, followed by `description:` and the complete Markdown body:

```text
title: Add a project validation check
description:
## Summary
...
```

Draft generation requires a model, provider type, provider URL, and API key. Set `PR_DESCRIPTION_DEFAULT_MODEL`, `PR_DESCRIPTION_DEFAULT_PROVIDER_TYPE`, `PR_DESCRIPTION_DEFAULT_PROVIDER_BASE_URL`, and `PR_DESCRIPTION_DEFAULT_PROVIDER_KEY` in the repository-root `.env`, or provide equivalent `COPILOT_PROVIDER_*` environment variables. `--model` can supply the model identifier. The script has no built-in model, endpoint, provider type, or key defaults, and it does not read VS Code's secret store.

Promotion pull requests are drafted without a model. When a pull request targets `main` from `staging`, or targets `staging` from `dev`, the script writes a promotion description that lists the pull requests merged into the source branch and absent from the target branch. The comparison uses the promotion pull request's own base and merge commits, so a historical promotion lists what it actually carried. Override detection with an explicit list when branch history is unavailable:

```bash
.venv/bin/python scripts/update_pr_descriptions.py 627 --draft --included-prs 621,626
```

Review and edit these files, then publish the saved contents with:

```bash
.venv/bin/python scripts/update_pr_descriptions.py 620-627 --publish
```

Draft generation skips existing files without querying Copilot unless `--force` is provided. It writes each successful draft immediately and continues after individual PR failures; failed PRs are reported and make the command exit nonzero. Publishing validates every requested file before updating any PR and does not regenerate descriptions.

Use `--verbose` with `--draft` to print the raw Copilot response when response parsing or validation fails. The configured API key is redacted from this output.

A failed draft names the single problem it found and quotes the offending value, so `--verbose` is only needed when the model's overall response is in question. The title must be one line of at most 71 characters with no trailing period, matching the rule in [the PR-description instructions](../../.github/pr-description-instructions.md). When a model writes a preamble before the title, the last line before the body separator is used as the title, so a narrated response still produces a usable draft.

## Recording Commits Without a Pull Request

Commits pushed straight to a base branch have no pull request to describe them, so add `--include-orphaned` to record them against the pull request that followed:

```bash
.venv/bin/python scripts/update_pr_descriptions.py 620-634 --draft --include-orphaned
```

The script compares the previous merged pull request into the same base branch with the pull request being drafted, then lists the commits on that branch's first-parent chain that no merged pull request carried. The result is appended as a `Detected orphaned commits` section. The section is omitted when nothing is listed, and it is replaced rather than duplicated when a draft is regenerated. The oldest pull request into a branch has no earlier pull request to compare against, so its draft reports no commits.

Housekeeping commits are filtered out of the list by default. A commit counts as housekeeping when any of these applies:

- Its subject is machine-written: `chore(release): X.Y.Z [skip ci]`, `feat(release): add vX.Y.Z release notes…`, or `chore: updated graphify graph`.
- Every changed path is inside `graphify-out/`, which holds generated output.
- Every changed path is inside `docs/`, so the commit changes documentation only.
- Every changed path is inside `.github/` or `.vscode/`, or is `sead_shape_shifter.code-workspace`, so the commit changes contributor configuration.

One path outside those locations keeps the commit, because the commit then carries a real change. The filtering is never silent: the section names the filtered counts, and the command reports the totals on standard error. Pass `--show-all-orphaned` to list every detected commit instead.

## Drafting Every Pull Request

Historically generated PR descriptions can be regenerated for a whole repository with one command:

```bash
# Show what would be drafted without writing anything
.venv/bin/python scripts/draft_all_pr_descriptions.py --dry-run

# Draft every merged pull request that has no draft file yet
.venv/bin/python scripts/draft_all_pr_descriptions.py

# Redraft everything, newest first, in batches of 10
.venv/bin/python scripts/draft_all_pr_descriptions.py --force --newest-first --batch-size 10
```

The script enumerates pull requests with `gh pr list` and drives `scripts/update_pr_descriptions.py` with `--draft --include-orphaned`. Existing draft files are kept unless `--force` is given, so an interrupted run resumes where it stopped and a later run retries only the missing drafts. It confirms the Copilot configuration before drafting; pass `--no-preflight` when every pull request in the set is a promotion, which needs no model.

The script relays the target script's output as it runs and ends with a summary of drafted, failed, and skipped pull requests. It never publishes: review `docs/whats-new/PRs/`, then publish with `scripts/update_pr_descriptions.py --publish`.

## Writing Guidelines

Prefer:

- plain language
- grouped highlights
- user-visible behavior
- short sections
- links to deeper technical material when needed

Avoid:

- commit hashes
- internal filenames unless they help the reader
- implementation detail
- long unstructured lists

## Template

Start from [TEMPLATE.md](TEMPLATE.md) when drafting a new release note.
