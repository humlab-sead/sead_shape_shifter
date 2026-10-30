# Pull Request Title and Description

Use these instructions when generating a pull request title and description.

## Review the change

- Base the description on the diff against the target branch. Inspect the complete diff, including relevant tests and documentation, when available.
- Consult linked issues, change requests, proposals, and related code when accessible to understand the problem and terminology. Treat the diff and verified behavior as authoritative for what this PR implements.
- Consult commit history only when necessary to clarify the change. Commit messages, plans, and issue descriptions are not evidence that behavior was implemented.
- Describe only changes supported by the available evidence. Do not guess at intent, claim unverified behavior, invent validation results, or imply that unavailable sources were inspected.
- Keep investigation limited to material relevant to this PR. If evidence is incomplete or conflicting, qualify the claim rather than filling gaps with assumptions.

## Title

- Write a concise, specific title describing the main change or user-visible outcome.
- Prefer fewer than 72 characters without sacrificing clarity.
- Use terminology found in the change; avoid vague titles such as "Updates" or "Improvements".
- Do not add a period at the end.
- Include an issue reference only when it is known and relevant.

## Description

Use `.github/pull_request_template.md` as the required structure. Produce a ready-to-use Markdown description with these headings, in exactly this order:

1. `## Summary`
2. `## User-facing release note`
3. `## Upgrade notes`
4. `## Validation`

Keep all four sections. Replace template comments with completed content or the specified fallback text. Do not reproduce the HTML comments, add unrelated sections, or wrap the description in a code fence.

### Summary

State what changed and why. Explain the main behavior or result, focusing on information useful to reviewers. Include implementation detail only when needed to understand the change. Distinguish implemented changes from planned or proposed work.

### User-facing release note

Provide a release-note candidate for the PR author to review. In one or two plain-language sentences, explain what users can now do or notice and, when supported, why it is useful. Avoid internal implementation details and speculative benefits.

- If the change is confirmed to have no user-visible effect, write exactly: `None - no user-visible change.`
- If the user-visible impact cannot be determined from available evidence, write: `User-visible impact not verified.`

### Upgrade notes

Describe any actions required to upgrade or continue using the project, including actions for end users, administrators, deployers, or API consumers, where applicable. Include required migrations, configuration changes, and breaking changes supported by the evidence.

- If no action is required based on the available evidence, write exactly: `None - no user action required.`
- If upgrade impact cannot be determined, write: `Upgrade impact not verified.`

### Validation

Report only checks and outcomes supported by available evidence. Distinguish:

- Checks confirmed as passed or failed, including the relevant command or test suite when known.
- Checks explicitly known not to have been run, with the reason when known.
- Checks whose execution or results are unknown.

Do not infer that checks passed or were not run merely because results are unavailable. If no validation evidence is available, write: `Not verified: validation results unavailable.`
