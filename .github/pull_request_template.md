## Summary

<!-- What changed and why? Focus on the main behavior or result.
     Promotion pull requests (`dev` into `staging`, `staging` into `main`) use
     .github/promotion_pr_template.md instead. They must not repeat the release-note text of the
     pull requests they carry.
     End this section with one `Closes #<issue>` line per resolved issue. This pull request targets
     `dev`, so the issue closes when the change reaches `main` through promotion, and the promotion
     description copies the reference. Prose such as "this fixes #123" does not count. -->

## User-facing release note

<!-- Required: Write 1-2 plain-language sentences describing what users can do or notice. Avoid implementation details and unsupported benefits.
     If there is no user-visible change, write exactly: "None - no user-visible change."
     If user-visible impact cannot be established, write: "User-visible impact not verified."
     Example: Validation results now include normalizer findings, such as row-count warnings. -->

## Upgrade notes

<!-- Required: Describe any upgrade or migration actions for users, administrators, deployers, or API consumers.
     If no action is needed, write exactly: "None - no user action required."
     If upgrade impact cannot be established, write: "Upgrade impact not verified." -->

## Validation

<!-- List checks actually run and their outcomes. Identify checks known not to have been run and explain why, when known.
     Do not report unverified checks as passed or assume tests were not run merely because results are unavailable.
     If no validation evidence is available, write: "Not verified: validation results unavailable." -->
