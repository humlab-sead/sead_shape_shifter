# Investigation findings: Copilot promotion pull-request descriptions

**Brief:** User report that VS Code's “Generate with Copilot” button omits the promotion format for `dev` to `staging` and uses the wrong direction for `staging` to `main`.
**Status:** Partially conclusive
**Environment / baseline:** `humlab-sead/sead_shape_shifter`, branch `staging`, revision `59a3fb86`; the worktree was clean before this change. The user confirmed the VS Code GitHub Pull Requests & Issues extension.

## Executive summary

Both `dev` into `staging` and `staging` into `main` are promotion routes and should use the promotion template. The workspace configures the VS Code pull-request description generator to read `.github/pr-description-instructions.md` ([`.vscode/settings.json`](../../../.vscode/settings.json#L77), [`sead_shape_shifter.code-workspace`](../../../sead_shape_shifter.code-workspace#L88)).

Before this change, the instructions named both routes but gave a branch-specific default title only for `dev` into `staging`. They also did not explicitly require using the current pull request's head and base refs to choose the route and fill in its direction. This is a supported explanation for both reported outputs, but the VS Code generation request was not run here. The instructions and promotion template now identify the source and target from those refs and forbid reusing branch names from another promotion.

The local PR-description script is a separate, deterministic path: it recognizes both branch pairs and builds the title and Summary from `headRefName` and `baseRefName` ([`update_pr_descriptions.py`](../../../scripts/workflow/update_pr_descriptions.py#L62), [promotion detection](../../../scripts/workflow/update_pr_descriptions.py#L1026), [promotion builder](../../../scripts/workflow/update_pr_descriptions.py#L1138)). A direct check confirmed the expected direction for both routes.

## Verified observations and reproduction

- The VS Code setting points to `.github/pr-description-instructions.md`; the same setting is present in the workspace file.
- The previous instructions explicitly defaulted a title-less promotion request to `Promote dev to staging`, without an equivalent title rule for `staging` into `main`.
- The updated instructions map `dev` → `staging` and `staging` → `main` to separate titles and Summary sentences, require the current PR's head and base refs, and say not to guess when those refs are unavailable ([`pr-description-instructions.md`](../../../.github/pr-description-instructions.md#L43)).
- The promotion template now says to use the current PR's head as the source and base as the target ([`promotion_pr_template.md`](../../../.github/promotion_pr_template.md#L9)).
- The repository-local generator produced `Promotes \`dev\` into \`staging\`.` for `dev` → `staging` and `Promotes \`staging\` into \`main\`.` for `staging` → `main` when given those branch names as metadata.
- The reported VS Code button output could not be reproduced because this investigation did not invoke the extension or its Copilot service.

## Evidence ledger

| ID | Observation or test | Source | Result | Assessment |
| --- | --- | --- | --- | --- |
| E1 | VS Code description-generation instructions are configured | [`.vscode/settings.json:77`](../../../.vscode/settings.json#L77), [`sead_shape_shifter.code-workspace:88`](../../../sead_shape_shifter.code-workspace#L88) | Both point to `.github/pr-description-instructions.md` | Verified |
| E2 | Promotion direction now comes from the current PR's head and base branches | [`.github/pr-description-instructions.md:43-48`](../../../.github/pr-description-instructions.md#L43) | Both supported routes have explicit titles and Summary text; unknown refs must not be guessed | Verified |
| E3 | Promotion template explains source and target branch selection | [`.github/promotion_pr_template.md:10`](../../../.github/promotion_pr_template.md#L10) | Uses this PR's head as source and base as target | Verified |
| E4 | Local promotion builder uses metadata for the description direction | [`scripts/workflow/update_pr_descriptions.py:1138-1147`](../../../scripts/workflow/update_pr_descriptions.py#L1138) | It formats both title and Summary from `headRefName` and `baseRefName` | Verified |
| E5 | VS Code button generated the reported output | User report only | No extension request or output log was available to reproduce it | Unverified |

## Root-cause assessment

**Supported hypothesis:** The custom instruction file used by the VS Code setting lacked an explicit route-to-title mapping and a rule to derive the promotion direction from the current PR's head and base refs. Its only no-title promotion default named `dev` into `staging`. That ambiguity can explain why the generator failed to select the promotion format for one route and reused the `dev`-to-`staging` direction for the other.

**Not established:** The exact prompt and branch metadata supplied by the extension for the reported generation. Copilot may also fail to follow instructions on an individual run; changing repository guidance cannot guarantee deterministic model output.

The repository-local script is not a likely source of the wrong direction when it receives correct metadata: its route detection includes both supported pairs, and its promotion builder formats the text from the received head and base refs. The VS Code setting points to the instruction file rather than invoking this script.

## Impact and extent

**Confirmed affected cases:** The user reported the `dev`-to-`staging` and `staging`-to-`main` generation cases.

**Potential wider impact:** Other VS Code-generated promotion descriptions may be affected by the same ambiguity. No other PRs were inspected, and the total extent is unknown.

## Remediation options

| Option | Benefits | Risks / compatibility | Prerequisites / validation |
| --- | --- | --- | --- |
| Make the configured instructions map each supported head/base pair to its own promotion title and Summary | Directly addresses both reported routes without changing standard PR descriptions | Copilot may still ignore instructions for an individual generation | Regenerate one PR for each route with the updated file |
| Use the repository-local PR-description script for deterministic promotion drafts | The script bypasses model generation for promotions and uses PR branch metadata | Requires using the local script workflow instead of the VS Code button | Validate the actual PR metadata and draft before publishing |

**Recommended next step:** Use the updated instructions for the next VS Code generation and verify the title, promotion marker, headings, and direction before publishing. If either route is still wrong, capture the extension version and its PR-description generation output log.

**Prevention / regression detection:** Keep both promotion routes listed in the VS Code instruction file and preserve the template's current-PR head/base rule. Review generated promotion directions before publishing.

## Unresolved questions and blockers

- Whether the exact reported output is caused by the old default-title wording, missing branch metadata, or another extension/model behavior remains unverified.
- The actual VS Code generation path could not be exercised in this environment.

## Verification record

- `rtk uv run pytest scripts/tests/workflow/test_update_pr_descriptions.py -q` — passed.
- Direct `build_promotion_draft` check for `dev` → `staging` and `staging` → `main` — both produced titles and Summary sentences with the supplied branch direction.
- `rtk git diff --check` — passed.
- VS Code “Generate with Copilot” — not run; extension and Copilot interaction were unavailable.

## References

- [VS Code custom instructions for pull-request descriptions](../../../.github/pr-description-instructions.md)
- [Promotion pull-request template](../../../.github/promotion_pr_template.md)
- [Local PR-description generator](../../../scripts/workflow/update_pr_descriptions.py)
- [GitHub Copilot custom-instructions documentation](https://docs.github.com/en/copilot/concepts/prompting-and-context/custom-instructions)
