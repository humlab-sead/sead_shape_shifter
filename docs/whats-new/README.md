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

1. **Write a note in each PR.** Complete the `User-facing release note` and `Upgrade notes` sections in [the PR template](../../.github/PULL_REQUEST_TEMPLATE.md). Use one or two plain-language sentences for visible changes. If a PR has no user-visible change or needs no user action, use the exact `None` text in the template.
2. **Generate the release draft.** During a release, semantic-release runs `scripts/generate_whats_new.py` for the new version. It reads the `User-facing release note` and `Upgrade notes` sections from PRs merged into `staging` and `main` between the previous and current main-promotion checkpoints. `CHANGELOG.md` supplies the version dates and remains the technical changelog; its commit summaries are not used as user-facing content. The generator also adds a `Pending Release` snapshot of staging PRs merged after the latest PR merged into `main`, including their authored notes. If an AI API key is configured, the generator can consolidate duplicate PR notes; otherwise it preserves the authored notes in the draft.
3. **Review the generated note.** Check that every distinct user-visible change and required upgrade action is represented, and confirm the pending staging items are not presented as released changes. The generator requires the GitHub CLI to be installed and authenticated so it can read PR descriptions.
4. **Keep the file and release body in sync.** After editing `docs/whats-new/vX.Y.Z.md`, update the GitHub Release body with `gh release edit vX.Y.Z --notes-file docs/whats-new/vX.Y.Z.md`.
5. **Refresh the pending snapshot when needed.** After more PRs merge into `staging`, rerun the generator for the latest version. Generation replaces the file, so review and reapply any manual edits afterward.

The release hooks live in `.releaserc.json`. The new generator uses heuristic output when no AI API key is configured and falls back to authored PR notes if AI generation fails. The `gh` CLI must be installed and authenticated. The previous `scripts/generate_user_release_notes.py` remains available for changelog-derived drafts.

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

Review and edit these files, then publish the saved contents with:

```bash
.venv/bin/python scripts/update_pr_descriptions.py 620-627 --publish
```

Draft generation skips existing files without querying Copilot unless `--force` is provided. It writes each successful draft immediately and continues after individual PR failures; failed PRs are reported and make the command exit nonzero. Publishing validates every requested file before updating any PR and does not regenerate descriptions.

Use `--verbose` with `--draft` to print the raw Copilot response when response parsing or validation fails. The configured API key is redacted from this output.

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
