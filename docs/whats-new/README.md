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
2. Write or refine a short user-facing summary for the release.
3. Publish the same summary in GitHub Releases.
4. If useful, store the summary here for long-term documentation access.

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
