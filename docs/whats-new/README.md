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

## Suggested Workflow

1. Let semantic-release continue generating `CHANGELOG.md`.
2. Let the release automation generate a draft `docs/whats-new/vX.Y.Z.md` summary from the new changelog section.
3. Review and refine that draft into a user-facing summary for the release.
4. Let the automation use that draft as the GitHub Release body, then refine it if needed.
5. If useful, keep the reviewed summary here for long-term documentation access.

The current automation hook lives in `.releaserc.json` and runs `scripts/generate_user_release_notes.py` after semantic-release publishes. When `RELEASE_NOTES_API_KEY` is configured, the script uses an OpenAI-compatible chat endpoint to draft the summary; otherwise it falls back to the built-in heuristic summary generator. When `gh` is available, it also updates the matching GitHub Release body from the generated draft.

Optional AI mode environment variables:

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

1. Generates a heuristic draft release note file.
2. Prints and saves a ready-to-paste Copilot CLI prompt with filtered, user-visible changelog context.

By default it writes:

- `docs/whats-new/vX.Y.Z.md`
- `tmp/copilot-release-notes-vX.Y.Z.prompt.md`

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
