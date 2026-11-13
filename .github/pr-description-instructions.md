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
- Keep the title to at most 71 characters, including spaces. A longer title is rejected.
- Use terminology found in the change; avoid vague titles such as "Updates" or "Improvements".
- Do not add a period at the end.
- Include an issue reference only when it is known and relevant.
- Write the title on one line with no label, quotes, or bold markers.

## Description

For standard, non-promotion pull requests, use `.github/pull_request_template.md` as the required structure. Produce a ready-to-use Markdown description with these headings, in exactly this order:

1. `## Summary`
2. `## User-facing release note`
3. `## Upgrade notes`
4. `## Validation`

Keep all four sections. Replace template comments with completed content or the specified fallback text. Do not reproduce the HTML comments, add unrelated sections, or wrap the description in a code fence.

### Promotion pull requests

A promotion pull request moves one branch into the next stage of the pipeline: `dev` into `staging`, or `staging` into `main`. Use `.github/promotion_pr_template.md` for these, and start the body with the `<!-- promotion-pr -->` marker. Promotion descriptions use these headings, in exactly this order:

1. `## Summary`
2. `## Included PRs`
3. `## User-facing release note`
4. `## Upgrade notes`
5. `## Validation`

Treat any request for a PR message, title, or description that says `dev` is being promoted to `staging` as a promotion request, even if the user does not call it a promotion. Use `.github/promotion_pr_template.md`, not the general PR template. If the user asks only for a message and provides no title, use `Promote dev to staging` as the title and provide the promotion-template body.

Keep promotion bodies compact: put `## Summary` immediately after the marker, use at most one blank line between Markdown blocks, and keep `Included PRs` list items consecutive without blank lines.

Each promotion is usually built from another pull request in this repository, so the description states only what is being promoted and lists the pull request numbers it carries. Promotion pull requests use the `None` fallbacks for the release-note and upgrade sections, because the release-note generator reads those sections from the pull requests listed under `Included PRs`. Do not restate their notes here.

List the issues the promotion resolves as `Closes #<issue>` lines in `## Summary`, copied from the closing references of the included pull requests. Merging the promotion into `main` closes them. Keep those issue references out of `Included PRs`, which the release generator reads as pull request numbers.

### Summary

State what changed and why. Explain the main behavior or result, focusing on information useful to reviewers. Include implementation detail only when needed to understand the change. Distinguish implemented changes from planned or proposed work.

### Closing issues

- Give each resolved issue its own `Closes #<issue>` line at the end of `## Summary`. A closing keyword is the only reference GitHub acts on; prose such as "this fixes #123" is ignored.
- Standard pull requests target `dev`, which is not the default branch, so a closing keyword does not close the issue when they merge. GitHub still records it as a closing reference, and the promotion description copies it into the promotion body.
- Promotion pull requests repeat the closing references of every included pull request that resolves an issue, using the same `Closes #<issue>` form. The promotion into `main`, the default branch, then closes them; the `dev` into `staging` promotion only records the lines for the next promotion.
- Do not put issue numbers under `## Included PRs`. The release-note generator reads every `#<number>` in that section as a pull request number.
- Close an issue only when the change resolves it completely. When the change delivers part of the issue, keep it open and name the remaining scope.

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
