# User-Facing Release Notes Strategy

## Summary

Keep the existing `CHANGELOG.md` as the technical, developer-oriented change log, and add a separate user-facing release notes surface for normal users.

The current changelog is useful, but it is generated from engineering commits and therefore optimized for auditability and development history rather than user communication.

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

For this repository, the current `CHANGELOG.md` should remain the canonical technical log.

## Naming

If a repo file is added for user-facing notes, `WHATS_NEW.md` is clearer than `RELEASE.md`.

However, a single root-level file is not ideal long term. A better structure is:

- `docs/whats-new/`
- `docs/releases/`

with one file per release or per minor version.

Benefits:

- easier to maintain over time
- easier to link from docs, GitHub releases, or the app UI
- avoids turning one file into an unstructured archive

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

This repo is a clear example: the current changelog contains a mix of user-visible improvements, internal refactors, TODO updates, test maintenance, and documentation work.

## Recommended Workflow

The cleanest workflow for this project is:

1. Keep semantic-release generating `CHANGELOG.md`
2. Use GitHub Releases as the primary user-facing release notes surface
3. Curate the GitHub release text manually or semi-manually
4. Optionally mirror important releases into `docs/whats-new/` if in-product or docs-site visibility is needed

This aligns well with the current semantic-release setup because it already generates release notes and publishes GitHub releases.

## Why GitHub Releases Are a Good Primary Surface

GitHub Releases are a good fit because they are:

- naturally versioned
- easy to link to
- expected by technical users and evaluators
- compatible with semantic-release automation
- separate from the full technical changelog

They also let the project maintain:

- a short curated summary for users
- a link to the full changelog for technical readers

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

## Practical Example

Instead of presenting a release as a long list of commit subjects, a user-facing summary for a release should say things like:

- Added graph edge visibility controls
- Added graph label size controls
- Improved SQL entity column handling
- Improved foreign key editor behavior and validation clarity
- Fixed several issues in graph view and project-scoped data source handling

It should not surface every internal cleanup, docs patch, or test change.

## Long-Term Improvement Option

If better automation is desired later, improve commit and release classification first.

For example:

- exclude `docs`, `test`, `chore`, `style`, and internal maintenance work from user-facing summaries
- map selected scopes to user-facing categories
- optionally use labels or PR metadata to mark changes as user-visible

Without that discipline, fully automated user-facing release notes will still read like engineering output.

## Proposed Decision

Adopt the following approach:

- Keep `CHANGELOG.md` as the technical changelog
- Use curated GitHub Release notes as the main user-facing release notes
- Add `docs/whats-new/` only if a docs-based release history becomes useful

## Conclusion

The best practice for this project is not to replace the current changelog, but to complement it.

Use:

- `CHANGELOG.md` for technical history
- curated release notes for users
- stable documentation for current system behavior

This gives each audience the right level of detail without forcing one document to do incompatible jobs.
