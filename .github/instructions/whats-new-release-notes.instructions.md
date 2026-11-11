---
description: "Use when creating or editing versioned What's New notes or the rolling pending snapshot."
applyTo:
  - "docs/whats-new/v*.md"
  - "docs/whats-new/????-??-v*.md"
  - "docs/whats-new/TEMPLATE.md"
  - "docs/whats-new/PENDING.md"
---
# What's New Release Note Instructions

- Write for users. Include visible changes, workflow effects, and required upgrade actions; omit implementation, test, and maintenance details.
- For PR-based drafts, use the included non-promotion PRs' `User-facing release note` and `Upgrade notes` sections as the source. Keep all distinct changes, consolidate duplicates, and do not infer missing details.
- For promotions, use the included PRs' notes instead of the promotion PR's own notes.
- Versioned notes contain only changes shipped between the previous release ref and the current release ref. Never add pending PRs to a versioned note.
- `PENDING.md` is a rolling snapshot of merged PRs that have not reached `main`. Keep it separate from versioned notes and GitHub release bodies.
- For changelog-based drafts, use only the filtered changelog context supplied to the drafting process.
- Preserve the target file's structure and check each note against its source before publication.
- See [the contributor guide](../../docs/whats-new/README.md) for workflow steps and [the scripts guide](../../scripts/README.md) for commands, options, and provider settings.
