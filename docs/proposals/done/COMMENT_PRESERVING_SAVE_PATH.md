# Proposal: Comment-Preserving Save Path

## Status

- Proposed feature
- Scope: Project load/save path, YAML editing workflow
- Goal: Preserve author comments across normal edit and save operations

## Summary

Preserve YAML comments across normal load/edit/save operations instead of dropping them during backend round trips. This matters because comments currently carry a meaningful share of complex modeling rationale, and the project documentation already encourages authors to document unusual configurations inline. The recommendation is to add a comment-preserving save path first, not to treat a new generic `note` attribute as a replacement. The persistence foundation that may enable this is proposed separately in [BOUNDARY_BASED_PROJECT_PERSISTENCE.md](BOUNDARY_BASED_PROJECT_PERSISTENCE.md).

## Problem

Complex projects often need local explanation in the YAML itself.

Examples:

- why a branch exists even though the target model does not expose it directly
- why a lookup is intentionally modeled as a fact-like table or vice versa
- why an append, filter, or derived column sequence is intentionally unusual
- what temporary workaround should be removed later

Today the backend save path normalizes YAML into plain Python objects before writing it back. That loses comments even when the underlying configuration stays semantically unchanged.

This creates three problems:

- explanation disappears even though the configuration still parses and validates
- authors stop trusting UI-driven saves for complex projects
- mixed UI plus hand-edited workflows become less maintainable over time

The issue is not cosmetic. It is about preserving modeling intent close to the configuration that needs explanation.

## Scope

This proposal covers:

- preserving YAML comments during ordinary project edit and save flows
- preserving author-only explanatory context without turning it into runtime configuration
- keeping mixed editor and YAML workflows safe for complex projects

## Non-Goals

This proposal does not:

- redesign the full project persistence format
- guarantee byte-for-byte formatting preservation for every whitespace choice
- introduce a general annotation system for every configuration object
- replace structured metadata fields that have real product value elsewhere

## Current Behavior

- YAML comments are a practical way to document unusual configurations inline
- the documentation already recommends comments for complex logic and section boundaries
- the current save path does not reliably preserve those comments after edits

## Proposed Design

Add a save path that preserves comments and nearby YAML structure well enough that ordinary editor operations do not silently strip explanatory text.

The design goal should be pragmatic:

- preserve comments and nearby placement during routine project edits
- keep author comments inert so they do not affect processing semantics
- prefer a focused persistence improvement over expanding the configuration schema

The system does not need perfect source-code-style round-tripping of every formatting detail to deliver value. It does need to stop discarding human explanation during normal saves.

The broader persistence rationale, including the intended initial subtree boundaries, is proposed separately in [BOUNDARY_BASED_PROJECT_PERSISTENCE.md](BOUNDARY_BASED_PROJECT_PERSISTENCE.md). This proposal stays focused on the user-visible goal: comments should survive normal saves.

Implementation details, delivery order, and a side-by-side comparison of the current and proposed save flows are documented in [COMMENT_PRESERVING_SAVE_PATH_IMPLEMENTATION_SKETCH.md](COMMENT_PRESERVING_SAVE_PATH_IMPLEMENTATION_SKETCH.md).

## Alternatives Considered

### Add An Entity-Level `note` Attribute Instead

This is not a full substitute.

- a single `note` field only explains an entity as a whole, while many explanations belong to a specific foreign key, `extra_columns` expression, append block, or temporary workaround
- comments can mark section boundaries and local cautions without changing the project schema
- forcing author-only prose into schema fields blurs the line between processing configuration and inert explanation
- adding `note` recursively across nested structures would expand the schema and still not cover free-form file-level commentary

A structured `note` field may still be useful later where it has clear workflow value, but it should not be used to justify losing comments.

## Risks And Tradeoffs

- comment-preserving persistence adds implementation complexity to the save path
- partial round-trip preservation may still leave some formatting changes in place
- the more aggressively the UI rewrites YAML structure, the harder exact comment retention becomes

Even with those tradeoffs, preserving comments is lower risk than pushing explanatory prose into ad hoc schema fields across the config model.

## Testing And Validation

Validate with save-roundtrip scenarios that cover:

- entity-level comments
- comments on nested blocks such as foreign keys, `extra_columns`, filters, and append items
- mixed workflows where a project is hand-edited, loaded in the editor, modified, and saved again
- edits that change one field while leaving nearby comments intact

## Acceptance Criteria

- comments survive ordinary project save operations in representative complex configs
- editor-driven saves no longer strip explanatory comments from unchanged sections
- author comments remain non-semantic and do not alter validation or processing behavior
- the solution works without adding a broad new `note` field across the entity schema

## Final Recommendation

Implement a comment-preserving save path as a focused persistence improvement.

Do not treat a generic `note` attribute as the main answer to this problem. If structured notes are added later, they should be justified by specific workflow value, not used as a substitute for preserving existing YAML comments.