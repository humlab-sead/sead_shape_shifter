---
description: "Use when writing or editing documentation, comments, docstrings, PR text, issues, proposals, user-facing messages, or AI coding-agent instructions."
applyTo: "**/*.md,**/*.py,**/*.ts,**/*.vue"
---

# Writing Style Instructions

Use this file when generating or editing:

* documentation
* comments and docstrings
* PR descriptions and issue text
* proposals and user-facing messages
* AI coding-agent instructions

## Standard

Write for developers, technical project members, domain experts, and AI coding agents that need accurate implementation or review context.

Prefer clear technical writing over simplification. Preserve terminology, structure, tone, and intent unless a change clearly improves readability.

Readers should understand:

* what is described
* what input is required
* what output or side effect is produced
* what rule, constraint, tradeoff, or failure case applies
* what to do next

## Wording and Docstrings

"Documentation Vocabulary" in the root `AGENTS.md` has the main wording rules and docstring examples. In addition:

* Start a docstring with what the function, class, or module does.
* Use technical terms when they are the correct project terms.
* Name the actual thing where you can, such as the input, output, error, side effect, or request details.

No word is forbidden. Use the terms below carefully unless they are established project vocabulary. Pick the replacement that says what you mean.

| Use carefully | Write instead, for example |
|---|---|
| `evidence` | data, result, validation result, check, source |
| `boundary` | limit, responsibility, allowed range, rule |
| `framing` | purpose, reason, background |
| `canonical` | standard, preferred, normalized, official |
| `surface` | interface, page, endpoint, entry point |
| `facing` | used by, shown to, exposed to |
| `slice` | part, section, subset, step |
| `signal` | indicator, warning, metric, status |

## Documentation

For guides, design notes, proposals, and reference pages:

* state the purpose before details
* preserve the document’s register and technical level
* use numbered steps for procedures
* state defaults, required fields, constraints, tradeoffs, and error cases explicitly
* keep examples, identifiers, paths, YAML, code blocks, and section order unless a small change improves readability
* distinguish current design from planned (next release cycle) or long-term work, and mark unimplemented sections `TBD`
* mark intentionally undefined processes `TBD` instead of inventing a process
* shorten or remove a section that does not help its readers act or understand

Do not normalize the whole document into a new writing style. Improve confusing, dense, repetitive, or vague passages in place.

## PRs and Issues

Include:

* what changed
* why it changed
* expected impact
* testing performed

Avoid vague summaries such as `improved architecture`, `enhanced functionality`, and `optimized workflow`.

Describe the actual behavior or code change instead.
