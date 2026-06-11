# Writing Style Instructions

Use this file when generating or editing:

- documentation
- comments and docstrings
- PR descriptions and issue text
- proposals and user-facing messages

## Standard

Write for a junior developer who is new to the project but comfortable with
Python, APIs, tests, and configuration files.

They should understand:

- what the code, feature, or document describes
- what input is required
- what output or side effect is produced
- what rule, constraint, or failure case applies
- what to do next

Use clear, concrete, behavior-first language:

- name the actual thing, action, rule, input, output, or result
- define project-specific terms near first use
- avoid internal shorthand unless it is established project vocabulary
- avoid metaphors, fashion-driven language, and vague claims

## Comments

Explain what is not obvious from the code:

- assumptions
- constraints
- edge cases
- side effects
- reasons for non-obvious choices

Do not restate code that is already clear.

Good:

`# Use local system_id values because external IDs may change.`

Bad:

`# Increment counter.`

## Docstrings

Start with what the function, class, or module does.

Prefer:

- `Reads sample rows from a CSV file.`
- `Returns validation errors for missing required fields.`
- `Uses the site ID to find matching sample groups.`
- `Does not write changes to the database.`

Avoid:

- `Ingests artifacts across the import boundary.`
- `Resolves canonical entities for downstream consumers.`
- `Emits signals for the review surface.`

## Documentation

For guides, design notes, and reference pages:

- state the purpose before details
- use numbered steps for procedures
- state defaults, required fields, and error cases explicitly
- include examples when they make the rule easier to apply

## PRs and issues

Include:

- what changed
- why it changed
- expected impact
- testing performed

Avoid vague summaries such as `improved architecture`,
`enhanced functionality`, and `optimized workflow`.

Describe the actual behavior or code change instead.