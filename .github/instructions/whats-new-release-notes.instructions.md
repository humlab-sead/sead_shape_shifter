---
description: "Use when creating or editing versioned What's New release notes. Covers note sources, user-visible changes, upgrade actions, and pending entries."
applyTo:
  - "docs/whats-new/v*.md"
  - "docs/whats-new/????-??-v*.md"
  - "docs/whats-new/TEMPLATE.md"
---
# What's New Release Note Instructions

- Write for users. Include visible changes, workflow effects, and required upgrade actions; omit implementation, test, and maintenance details.
- For PR-based drafts, use the included non-promotion PRs' `User-facing release note` and `Upgrade notes` sections as the source. Keep all distinct changes, consolidate duplicates, and do not infer missing details.
- For promotions, use the included PRs' notes instead of the promotion PR's own notes.
- Keep released changes separate from pending PRs. Preserve the generated `Pending Release` snapshot and do not describe pending changes as shipped.
- For changelog-based drafts, use only the filtered changelog context supplied to the drafting process.
- Preserve the target file's structure and check each note against its source before publication.
- See [the contributor guide](../../docs/whats-new/README.md) for workflow steps and [the scripts guide](../../scripts/README.md) for commands, options, and provider settings.
