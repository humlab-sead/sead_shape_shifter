---
description: "Use when writing or editing documentation, comments, docstrings, PR text, issues, proposals, user-facing messages, or AI coding-agent instructions."
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

Use concrete, behavior-first language:

* Name the actual thing, action, rule, input, output, or result.
* Write `# Increment counter.` rather than an abstract comment.

## Concrete Language

Use plain, concrete language in generated code, comments, docstrings, PR text, and documentation.

- Prefer words that name the actual thing, action, rule, input, output, or result directly.
- Use abstract or overloaded terms carefully. When a technical term is necessary, define it nearby or pair it with a plain-language explanation.
- Unless they are established project vocabulary, use terms such as `evidence`, `boundary`, `framing`, `canonical`, `surface`, `facing`, `slice`, and `signal` carefully.
- Prefer explicit wording such as `data`, `result`, `source`, `check`, `validation result`, `limit`, `responsibility`, `allowed range`, `rule`, `purpose`, `reason`, `background`, `request details`, `standard`, `preferred`, `normalized`, `official`, `interface`, `page`, `endpoint`, `entry point`, `used by`, `shown to`, `exposed to`, `part`, `section`, `subset`, `step`, `indicator`, `warning`, `metric`, `status`, `input`, `output`, `error`, and `side effect`.
- Match the level of detail to the reader: junior developers, maintainers, testers, data managers, researchers, and non-technical stakeholders may all use the text.
- The closer text is to code or user-visible behavior, the more concrete it should be.

## Docstrings

Start with what the function, class, or module does.

Prefer:

* `Reads sample rows from a CSV file.`
* `Returns validation errors for missing required fields.`
* `Does not write changes to the database.`

Explain behavior, responsibility, assumptions, inputs, outputs, and side effects. Avoid vague, metaphorical, fashion-driven, or overloaded wording when a more precise description is available.

Do not avoid technical terms when they are the correct project terms.

## Documentation

For guides, design notes, proposals, and reference pages:

* state the purpose before details
* preserve the document’s register and technical level
* use numbered steps for procedures
* state defaults, required fields, constraints, tradeoffs, and error cases explicitly
* keep examples, identifiers, paths, YAML, code blocks, and section order unless a small change improves readability

Do not normalize the whole document into a new writing style. Improve confusing, dense, repetitive, or vague passages in place.

## PRs and Issues

Include:

* what changed
* why it changed
* expected impact
* testing performed

Avoid vague summaries such as `improved architecture`, `enhanced functionality`, and `optimized workflow`.

Describe the actual behavior or code change instead.
