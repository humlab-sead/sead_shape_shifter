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
2. **Generate the release draft.** During a release, semantic-release runs `scripts/generate_user_release_notes.py` for the new version. It derives the main sections from `CHANGELOG.md` and adds a `Pending Release` snapshot of PRs merged into `staging` after the latest PR merged into `main`. The release automation publishes this generated file as the GitHub Release body.
3. **Review and correct the published note.** Use the merged PRs' authored notes to replace vague or duplicated heuristic text with concise user-facing information. Check upgrade actions and remove duplicate staging-promotion entries where appropriate. The generator does not yet read PR-body note sections; [issue #628](https://github.com/humlab-sead/sead_shape_shifter/issues/628) tracks that follow-up.
4. **Keep the file and release body in sync.** After editing `docs/whats-new/vX.Y.Z.md`, update the GitHub Release body with `gh release edit vX.Y.Z --notes-file docs/whats-new/vX.Y.Z.md`.
5. **Refresh the pending snapshot when needed.** After more PRs merge into `staging`, rerun the generator for the latest version. Generation replaces the file, so review and reapply any manual edits afterward.

The release hooks live in `.releaserc.json`. The preparation hook runs the generator in heuristic mode, so it does not need an external AI API key. The latest-version run uses the `gh` CLI to read merged PRs for the pending section; `gh` must be installed and authenticated. Historical versions generated with `--generate-missing` do not receive the current pending list.

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
