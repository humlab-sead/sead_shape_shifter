# Semantic Release Support For User-Facing Notes

## Summary

Keep semantic-release as the source of truth for versioning, tagging, and technical release output, but add a lightweight curated step so GitHub Releases can present a shorter user-facing summary.

The key requirement is to avoid forcing one generated note body to serve both `CHANGELOG.md` and end users.

## Problem

The current semantic-release setup generates useful technical notes, but those notes are too detailed and too commit-driven to work well as release communication for normal users.

If the same generated text is used everywhere, GitHub Releases will inherit the same problems as the technical changelog:

- too much internal detail
- too many low-level fixes
- no grouping by user value
- poor signal-to-noise ratio for non-developers

## Goal

Make GitHub Releases shorter and more user-facing without losing the current automated technical changelog.

## Recommended Approach

Use a hybrid release flow:

1. semantic-release continues to generate `CHANGELOG.md`
2. semantic-release continues to calculate the version and create the release
3. a curated user-facing summary is prepared separately
4. GitHub Release content is updated to use the short summary plus a link to the full changelog

## Why This Is Low Risk

- no need to replace the existing changelog workflow
- no need to weaken commit traceability
- no need to overfit commit messages for end-user prose
- GitHub Releases become easier to read immediately

## Concrete Adjustment

The preferred adjustment is to add a small release-content generation step rather than changing the changelog generator itself.

### Option A: Update GitHub release body after semantic-release publishes

Add a script invoked by `@semantic-release/exec` during `publishCmd` or `successCmd` that:

1. reads the release version
2. reads a prepared short summary from `docs/whats-new/` or a release notes file
3. builds a concise GitHub release body
4. updates the GitHub release body using `gh release edit` or the GitHub API

This preserves:

- technical notes in `CHANGELOG.md`
- shorter notes in GitHub Releases

### Option B: Generate a short summary file per release

Maintain a file such as `docs/whats-new/vX.Y.Z.md` and have the release workflow publish it or reference it.

This gives:

- versioned user notes in the repository
- a source for GitHub Release text
- content that can later be surfaced in documentation or the app

## Suggested Release Body Shape

GitHub Releases should be short and structured like this:

```md
## Highlights
- Added ...
- Improved ...
- Fixed ...

## Upgrade Notes
- If applicable, mention anything users need to verify.

## Full Technical Details
- See CHANGELOG.md
```

## What Not To Do

Avoid making the technical changelog less useful just to improve GitHub Releases.

Avoid:

- removing detail from `CHANGELOG.md`
- forcing commit messages to read like marketing copy
- treating all commit scopes as user-visible

## Possible Future Enhancements

If more automation is desired later, the project can add user-impact classification through:

- PR labels
- a release summary fragment file
- commit scope filtering for user-facing categories

That work should come after the split between technical and user-facing release output is established.

## Example Direction For `.releaserc.json`

The current config can remain mostly unchanged. The main addition would be an `exec` step that calls a script after release creation, for example:

```json
[
  "@semantic-release/exec",
  {
    "verifyConditionsCmd": "echo 'Python project - no package.json needed'",
    "prepareCmd": "sed -i 's/^version = \".*\"/version = \"${nextRelease.version}\"/' pyproject.toml && sed -i 's/^__version__ = \".*\"/__version__ = \"${nextRelease.version}\"/' backend/app/__init__.py",
    "successCmd": "scripts/publish-user-release-notes.sh ${nextRelease.version}"
  }
]
```

The script would be responsible for publishing a concise release body to GitHub while leaving the technical changelog untouched.

## Proposed Decision

Adopt a hybrid model:

- keep semantic-release for technical release automation
- keep `CHANGELOG.md` as the detailed record
- create short curated release notes for GitHub Releases
- optionally store those summaries in `docs/whats-new/`

## Conclusion

The best semantic-release adjustment is not to make automated notes do everything. It is to keep automation for the technical record and add a small curated layer for user-facing release communication.
