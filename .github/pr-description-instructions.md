# Pull Request Title and Description

Use these instructions when drafting or generating a pull request title and description.

## Review the change

- Read the complete diff against the target branch, including relevant tests and documentation.
- Use linked issue or task context when available, but treat the code and verified behavior as authoritative.
- Describe only changes present in the diff. Do not guess at intent, claim unverified behavior, or invent validation results.

## Title

- Write a concise title that states the main change or user-visible outcome.
- Use specific terms from the change; avoid vague titles such as "Updates" or "Improvements".
- Do not add a period at the end.
- Include an issue reference only when one is known and relevant.

## Description

Use `.github/pull_request_template.md` as the required structure. Keep its headings and order, replace its HTML comments with completed content, and do not omit a section.

### Summary

State what changed and why. Include the main behavior or result, and keep implementation detail to what helps reviewers understand the change.

### User-facing release note

Draft a release-note candidate that helps the PR author write the final user-facing note. In 1-2 plain-language sentences, explain what users can now do or notice and, where useful, why it helps them. Avoid internal implementation details, and only describe benefits supported by the change. If there is no user-visible change, write exactly: `None - no user-visible change.`

Use these sources to identify and verify the user-visible change:

- Start with the PR diff. Follow changed code and configuration through the affected user-facing workflows, and check relevant tests and documentation to confirm observable behavior.
- Use linked issues, change requests, or proposals to understand the user problem, intended benefit, and terminology. Include only goals implemented in this PR.
- Consult commit history only when needed to clarify the change; commit messages and plans do not prove that behavior shipped.
- Keep the search limited to related material. If sources conflict, describe only behavior supported by the PR diff and relevant validation.

### Upgrade notes

State any action users must take to upgrade or continue using the project. If no action is needed, write exactly: `None - no user action required.`

### Validation

List the checks actually run and their outcomes. Explain relevant checks that were not run; never imply a check passed if it was not run. If no checks were run, say so and give the reason when known.
