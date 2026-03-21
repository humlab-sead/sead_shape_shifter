# User-Facing Release Notes Strategy

## Summary

Keep the existing `CHANGELOG.md` as the technical, developer-oriented changelog, and add a separate user-facing release notes surface for normal users.

The current changelog is useful, but it is generated from engineering commits and therefore optimized for auditability and development history rather than user communication. The goal is not to replace that workflow, but to complement it with a shorter, curated layer for GitHub Releases and optionally `docs/whats-new/`.

## Problem

The current semantic-release setup generates useful technical notes, but those notes are too detailed and too commit-driven to work well as release communication for normal users.

If the same generated text is used everywhere, GitHub Releases inherit the same problems as the technical changelog:

- too much internal detail
- too many low-level fixes
- no grouping by user value
- poor signal-to-noise ratio for non-developers

This repo is a clear example: the current changelog contains a mix of user-visible improvements, internal refactors, TODO updates, test maintenance, and documentation work.

## Goal

Make GitHub Releases shorter and more user-facing without losing the current automated technical changelog.

## Recommendation

Use a three-layer documentation model:

1. **Technical changelog**
   - Keep `CHANGELOG.md`
   - Audience: developers and maintainers
   - Purpose: detailed release history, commit-derived notes, traceability

2. **User-facing release notes / What's New**
   - Add a separate release-notes surface for end users
   - Audience: normal users, stakeholders, evaluators
   - Purpose: explain what changed in user terms
   - Focus on:
     - new capabilities
     - visible fixes
     - behavior changes
     - upgrade notes
     - changes in recommended workflows

3. **Stable product documentation**
   - Keep user guidance in the user guide and other canonical docs
   - Audience: anyone learning or using the product
   - Purpose: explain current behavior, not release history

## Best Practice

Do not try to make a single document serve both developers and users.

Best practice is usually:

- one technical changelog for engineering history
- one curated release note format for users
- stable documentation for how the system works now

For this repository, `CHANGELOG.md` should remain the canonical technical log.

## Fit With Semantic Release

This should be done partly within semantic-release and partly outside it.

### Use semantic-release for

- version calculation
- tagging
- GitHub release creation
- technical changelog generation

### Do not rely on semantic-release alone for

- high-quality user-facing release notes

Reason:

- commit-derived notes are usually too granular
- they often expose internal implementation detail
- they are not grouped by user value
- they include changes normal users should not have to parse

## Recommended Workflow

Use a hybrid release flow:

1. semantic-release continues to generate `CHANGELOG.md`
2. semantic-release continues to calculate the version and create the release
3. a curated user-facing summary is prepared separately
4. GitHub Release content is updated to use the short summary plus a link to the full changelog
5. optionally mirror that short summary into `docs/whats-new/` if in-product or docs-site visibility is useful

This keeps semantic-release as the source of truth for versioning and technical output while avoiding the mistake of forcing one generated note body to serve both `CHANGELOG.md` and end users.

## Why GitHub Releases Are The Right Primary Surface

GitHub Releases are a good primary surface for user-facing release notes because they are:

- naturally versioned
- easy to link to
- expected by technical users and evaluators
- compatible with semantic-release automation
- separate from the full technical changelog

They also let the project maintain:

- a short curated summary for users
- a link to the full changelog for technical readers

## Naming And Storage

If repo-managed user notes are added, `WHATS_NEW.md` is clearer than `RELEASE.md`, but a single root-level file is not ideal long term.

A better structure is:

- `docs/whats-new/`
- optionally `docs/releases/`

with one file per release or per minor version.

Benefits:

- easier to maintain over time
- easier to link from docs, GitHub releases, or the app UI
- avoids turning one file into an unstructured archive

## Concrete Adjustment

The preferred adjustment is to add a small release-content generation step rather than changing the changelog generator itself.

### Preferred Option

Add a script invoked by `@semantic-release/exec` during `publishCmd` or `successCmd` that:

1. reads the release version
2. reads a prepared short summary from `docs/whats-new/` or another release-notes file
3. builds a concise GitHub release body
4. updates the GitHub release body using `gh release edit` or the GitHub API

This preserves:

- technical notes in `CHANGELOG.md`
- shorter notes in GitHub Releases

### Optional Extension

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

## What User-Facing Notes Should Include

User-facing notes should answer:

- What can I do now that I could not do before?
- What was fixed that I may notice?
- Do I need to change anything in how I work?
- Is there anything important to watch for after upgrading?

Good content categories:

- Highlights
- New features
- Important fixes
- Workflow changes
- Upgrade notes
- Known limitations if relevant

## What User-Facing Notes Should Avoid

Avoid including routine engineering detail such as:

- test maintenance
- TODO updates
- formatting-only changes
- refactors with no user impact
- low-level implementation detail unless it changes behavior

Avoid:

- removing detail from `CHANGELOG.md`
- forcing commit messages to read like marketing copy
- treating all commit scopes as user-visible

## Practical Example

Instead of presenting a release as a long list of commit subjects, a user-facing summary for a release should say things like:

- Added graph edge visibility controls
- Added graph label size controls
- Improved SQL entity column handling
- Improved foreign key editor behavior and validation clarity
- Fixed several issues in graph view and project-scoped data source handling

It should not surface every internal cleanup, docs patch, or test change.

## Why This Is Low Risk

- no need to replace the existing changelog workflow
- no need to weaken commit traceability
- no need to overfit commit messages for end-user prose
- GitHub Releases become easier to read immediately

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

The script would publish a concise release body to GitHub while leaving the technical changelog untouched.

## Long-Term Improvement Options

If better automation is desired later, improve commit and release classification first.

For example:

- exclude `docs`, `test`, `chore`, `style`, and internal maintenance work from user-facing summaries
- map selected scopes to user-facing categories
- optionally use labels, PR metadata, or release summary fragment files to mark changes as user-visible

Without that discipline, fully automated user-facing release notes will still read like engineering output.

## Proposed Decision

Adopt a hybrid model:

- keep semantic-release for technical release automation
- keep `CHANGELOG.md` as the detailed technical record
- use curated GitHub Release notes as the main user-facing release notes surface
- optionally store those summaries in `docs/whats-new/`

## Conclusion

The best practice for this project is not to replace the current changelog, but to complement it.

Use:

- `CHANGELOG.md` for technical history
- curated release notes for users
- stable documentation for current system behavior

This gives each audience the right level of detail without forcing one document to do incompatible jobs.
