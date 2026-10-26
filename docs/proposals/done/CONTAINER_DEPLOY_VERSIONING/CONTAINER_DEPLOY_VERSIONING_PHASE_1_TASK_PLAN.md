# Phase 1 Task Plan: Publish Reviewed Container Releases

## Phase Summary

- **Phase:** [Phase 1: Publish Reviewed Container Releases](./CONTAINER_DEPLOY_VERSIONING_PHASE_PLAN.md)
- **Goal:** Publish a complete, independently tagged `container/` archive from a reviewed merge without changing application releases.
- **Readiness:** **Validated; Phase 1 closed by user decision (2026-10-10).** PR #541 passed validation and published `container-v0.1.0`. The live workflow retry check was explicitly waived and not run; the retry-recovery defect remains recorded as a follow-up.
- **Source proposal:** [CONTAINER_DEPLOY_VERSIONING.md](./CONTAINER_DEPLOY_VERSIONING.md)
- **Phase plan:** [CONTAINER_DEPLOY_VERSIONING_PHASE_PLAN.md](./CONTAINER_DEPLOY_VERSIONING_PHASE_PLAN.md)
- **Dependency:** Configure and verify `T0.2` before enabling publication; complete `T0.1` before packaging. Phase 2's separately installed host script, download, activation, and rollback are not part of this task plan.

### Acceptance Criteria

- [x] `PH1-AC-1` (from `P-AC-1`): PR validation produces no tag or Release; an approved merge produces exactly one complete archive, checksum, and source-commit record under a distinct immutable container tag. (Verified by PR #541 and `container-v0.1.0`; see `V-1` and `V-2`.)
- [x] `PH1-AC-2` (from `P-AC-1`): Publishing a container release leaves application release tags, version, and workflow behavior unchanged; missing content or a reused version fails publication. (Verified by `V-1` through `V-3`; the merged workflow's retry-recovery defect is recorded separately.)

## Repository Findings

**Repository basis:** Branch `container-deploy-versioning`, commit `93d00229`, planning date 2026-10-10. The working tree contains uncommitted container lifecycle edits and the new proposal and phase plan; no existing changes were modified for this plan.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `.github/workflows/release.yml` | The only GitHub Actions workflow in the inspected workflow directory runs semantic-release on `main` or manual dispatch. | Add separate container PR/publication automation; preserve this application workflow. |
| `.releaserc.json` | The application release is limited to `main`; its plugins update application version files, changelog, and release notes. | Do not reuse this configuration for container tagging or touch application version files. |
| `container/`, `container/README.md` | The tracked tree contains deployment files, build files, scripts, service definition, examples, resources, and documentation. The README describes a replaceable `~/container` checkout. | Package the complete tracked `container/` tree, not just scripts; document publication separately from the later host installation change. |
| `container/.containerignore` | The file filters standalone image-build context, excluding service and documentation files. | Do not use image-build context rules to decide what belongs in the release archive. |
| Local branch/tag inspection | No local `container-release` branch or `container-v*` tag was observed. Remote branch/tag settings and protections were not checked. | Create and protect the release branch and tags as part of `T0.2`; stop if repository permissions prevent it. |
| `.github/workflows/` inspection | No existing container release workflow or container-specific workflow test was found. | Proposed workflow and archive verification targets below are `NEW`; validation is planned, not a baseline pass. |

## Scope

**In scope**

- Record the next version in `container/VERSION` in a reviewed promotion PR based on `container-release` that merges `main`; review the resulting `container/` tree.
- Establish protection against unreviewed publication and tag rewriting.
- Validate complete release inputs on PRs without publishing; publish one complete, checksummed archive and source identity after an approved merge.
- Document the release/tag contract and verify the application's release workflow and version remain independent.

**Out of scope**

- Downloading or installing GitHub Releases on a deployment host, environment selection, rollback, or changing `~/container`.
- Container lifecycle dispatcher changes and verification-script disposition.
- Changing application release tags, application version files, or `.releaserc.json`.
- Publishing releases from unmerged PRs or a moving `main` branch.

## Work Breakdown

### Area 0: Establish the Reviewed Release Source

**Objective:** Prepare the reviewed version file and enforce the agreed branch and tag rules before publication is enabled.

**Affected code:** `container/VERSION` (`NEW`); GitHub branch/tag protection settings (external).

**Dependencies:** None.

**Tasks:**

* [x] `T0.1` **Change:** Introduce the reviewed container version and promotion flow. *(Implemented 2026-10-10: `container/VERSION` = `0.1.0`; verifier enforces format, strict increase, and merged `main`; flow documented in `container/README.md`. PR #541 was reviewed, merged, and published.)*
* [x] `T0.2` **Change:** Configure and verify GitHub publication protections. *(Configured and verified 2026-10-10 via API reads; see Execution Record. Tag-creation restriction deviates as noted: immutability enforced by deletion/update rules plus workflow refusal.)*

**Completion evidence:** A reviewed promotion PR carries an incremented `container/VERSION` and the intended merged tree; branch/tag rules and read-only PR permissions are configured and checked before any release is published.

### Area 1: Validate and Publish the Container Archive

**Objective:** Produce a complete, checksummed, source-identified GitHub Release only from the approved merged commit.

**Affected code:** `.github/workflows/container-release.yml` (`NEW`); `container/scripts/verify/verify_container_release.sh` (`NEW`); `container/VERSION` (`NEW`); `container/README.md`.

**Dependencies:** `T0.1` and initial branch/tag protection from `T0.2`; require the `T1.1` check and finish `T0.2` before `T1.2` publishes.

**Tasks:**

* [x] `T1.1` **Change:** Build and check the complete archive without publishing on PRs. *(Implemented 2026-10-10: `validate` passed on PR #541; the `publish` job was skipped; the archive artifact uploaded successfully.)*
* [x] `T1.2` **Change:** Publish one separately tagged release after an approved merge. *(Implemented 2026-10-10: `container-v0.1.0` was published from merge commit `71f52f8268daed3f04c501e50cf59341fbb1273d`; see `V-2` and finding `F1`.)*
* [x] `T1.3` **Change:** Document the publication and selection contract. *(Implemented 2026-10-10: `container/README.md` "Container Releases" and "Promoting a container release" sections.)*

**Completion evidence:** An approved merge publishes exactly one complete container release whose tag, archive, checksum, and commit agree; PR and invalid/duplicate attempts publish nothing; application release behavior remains unchanged.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH1-AC-1` (`P-AC-1`) | `T0.1`, `T0.2`, `T1.1`, `T1.2` | `V-1`, `V-2` | Reviewed promotion PR with an incremented version; read-only validation and one complete, immutable release from the merged commit. |
| `PH1-AC-2` (`P-AC-1`) | `T0.1`, `T1.1`, `T1.2`, `T1.3` | `V-2`, `V-3` | Invalid inputs or duplicate versions fail; the application release config, tags, and version remain independent. |

## Validation And Testing

The workflow, verifier, and version file are implemented (2026-10-10; see Execution Record). These executable checks were exercised on PR #541 and the first reviewed release, `container-v0.1.0`; no throwaway production tags were created. `VM-1` in the phase plan corresponds to `V-1` through `V-3`.

| ID | Check and target | Command or method | Covers | Expected result | Status |
| --- | --- | --- | --- | --- | --- |
| `V-1` | PR validation and complete-archive checks in `.github/workflows/container-release.yml`, `container/VERSION`, and `container/scripts/verify/verify_container_release.sh` | In a promotion PR based on `container-release` with `main` merged, inspect the workflow run and archive for tracked `container/` deployment/build files, scripts, service, resources, examples, and the incremented version. Test candidates with a missing required file and an unchanged or malformed version. Compare tags and Releases before and after; inspect PR job permissions and branch checks. | `PH1-AC-1`, `PH1-AC-2` | Valid candidate passes; incomplete or invalid candidates fail; none produces a tag or Release or gains publication permission. | **Passed (2026-10-10):** PR #541's `validate` job passed and uploaded its archive artifact; `publish` was skipped. The workflow grants PR jobs `contents: read`. Existing local positive and negative verifier tests are recorded in the Execution Record. |
| `V-2` | Approved publication, uniqueness, and metadata in `.github/workflows/container-release.yml` and verifier | After branch and tag protections are verified, merge the first intentionally reviewed promotion PR. Inspect the generated `container-vX.Y.Z` tag, archive, checksum, and source commit against the merged tree. Re-run the same workflow/version to confirm it refuses to overwrite the release; check inconsistent versions before merge via `V-1`. Inspect and explicitly report any partial publication failure. | `PH1-AC-1`, `PH1-AC-2` | One release identifies the exact merged commit and valid checksum; retry and invalid versions cannot replace its tag or assets. | **Publication verified; live retry check waived by user (2026-10-10):** the first publication succeeded; the tag resolves to `71f52f8268daed3f04c501e50cf59341fbb1273d`; the release contains the archive and checksum, the checksum verifies, and archive files exactly match the tracked `container/` files at that commit. A safe local retry simulation exposed `F1`. The live workflow retry was decided not to be run; this is recorded as not run, not as a pass. |
| `V-3` | Application-release separation and documentation | Compare `.github/workflows/release.yml`, `.releaserc.json`, application version files, and existing application tags before and after `V-2`; inspect `container/README.md` for exact-tag guidance. | `PH1-AC-2` | Existing application release behavior and version are unchanged; documentation distinguishes the two release streams. | **Passed (2026-10-10):** the container workflow ran on `container-release`; the application release workflow and `.releaserc.json` were unchanged, the application version remains `2.3.0`, and no application release was published by the container workflow. `pyproject.toml` also received a dependency addition from the merged `main` content; its application version did not change. README documents exact-tag selection. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Reviewed version and source tree | `container/VERSION` (`NEW`); promotion PR based on `container-release` | `T0.1` | PR #541 merged as `71f52f8268daed3f04c501e50cf59341fbb1273d`; release tag `container-v0.1.0` points to that source commit. |
| Protected publication | GitHub branch/tag and workflow permission settings (external) | `T0.2` | Verified 2026-10-10: branch protection (1 review, no force/delete, linear history, required `validate` check) and active tag ruleset `container-tags-immutable`; PR jobs read-only. |
| Container PR and publication automation | `.github/workflows/container-release.yml` (`NEW`) | `T1.1`, `T1.2` | PR validation and first approved-merge publication both succeeded; the retry-recovery defect is recorded as `F1`. |
| Complete-archive verification | `container/scripts/verify/verify_container_release.sh` (`NEW`) | `T1.1`, `T1.2` | PR and published archives passed validation; published archive file list matches the source commit and its checksum verifies. |
| Publication guidance | `container/README.md` | `T1.3` | Exact-tag selection and separation from application releases were confirmed during `V-3`. |
| Phase 1 execution record | `docs/proposals/done/CONTAINER_DEPLOY_VERSIONING/CONTAINER_DEPLOY_VERSIONING_PHASE_1_TASK_PLAN.md` | — | Execution Record updated with PR, release, checksum, archive, application-release separation, and retry-recovery evidence; the live workflow retry is explicitly waived and recorded as not run. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 0: Establish the reviewed release source | Implemented; `T0.2` verified | None | `container/VERSION` created (`0.1.0`). Remote `container-release` branch created from `main` and protected (1 required review, no direct/force push/delete, linear history, `validate` required check). Tag ruleset `container-tags-immutable` blocks deletion/update of `refs/tags/container-v*`. |
| Area 1: Validate and publish the container archive | Complete by user decision; live `V-2` retry check waived | Version and initial protections from Area 0 | PR #541 validated and published `container-v0.1.0`. The live retry was not run by decision. The merged workflow has the retry-recovery defect recorded as `F1`; the current local branch contains an unpromoted follow-up fix. |

## Execution Record

Implementation date 2026-10-10 on branch `container-deploy-versioning` (pre-existing uncommitted dispatcher edits preserved untouched).

**Implemented deliverables:**

- `container/VERSION` (`NEW`) — `0.1.0` (`T0.1`).
- GitHub protections (`T0.2`, configured and verified via API reads):
  - Branch protection on `container-release`: 1 required approving review, stale-review dismissal, last-push approval, enforce-admins, no force pushes, no deletions, linear history, required status check `validate` (strict).
  - Tag ruleset `container-tags-immutable` (id 24839352, active): `deletion` and `update` rules on `refs/tags/container-v*`. Tag creation is not blocked, so the post-merge workflow can publish; rewriting or deleting published tags is blocked for everyone including admins.
  - Workflow permission check: `container-release.yml` grants `contents: read` at top level; only the `publish` job (push to `container-release` only) escalates to `contents: write`. PR jobs run read-only.
- `.github/workflows/container-release.yml` (`NEW`) — `validate` job on PRs targeting `container-release` (no tag/Release, read-only) and `publish` job on merge (refuses existing tag/Release, publishes tag + archive + sha256 + source commit, verifies both assets after creation) (`T1.1`, `T1.2`).
- `container/scripts/verify/verify_container_release.sh` (`NEW`) — version format, strict increase over highest `container-v*` tag, duplicate-tag refusal, required-file presence in tree and archive, single-`container/` archive layout, `.git` exclusion, optional `--require-main-merged` (`T1.1`, `T1.2`).
- `container/README.md` — "Container Releases" and "Promoting a container release" sections; states host installation is not yet available (`T1.3`).

**Validation evidence (local, 2026-10-10):**

- `V-1` (passed): PR #541's `validate` job completed successfully, uploaded the review archive, and skipped `publish`. The workflow grants PR jobs read-only `contents` permission. The local positive and negative cases recorded above remain valid.
- `V-2` (initial publication passed; live retry check waived): PR #541 merged at `71f52f8268daed3f04c501e50cf59341fbb1273d`. The successful `Container Release` run created annotated tag `container-v0.1.0` at that commit and a GitHub Release containing `container-v0.1.0.tar.gz` and its `.sha256` file. The downloaded checksum passed; the archive verifier passed; its file list matched the complete tracked `container/` tree at the source commit. A local simulation found that a retry at the PR-era commit fails strict version validation before reaching the workflow's same-commit resume step. Per the user's decision on 2026-10-10, the live workflow retry will not be run; it remains not run, not passed. See `F1`.
- `V-3` (passed): the container workflow ran on `container-release`; `.github/workflows/release.yml`, `.releaserc.json`, `CHANGELOG.md`, and `backend/app/__init__.py` were unchanged. The application version in `pyproject.toml` remained `2.3.0`; the PR added a dependency from the merged `main` content. The container release tag and workflow are separate from the application release stream, and `container/README.md` specifies exact-tag selection.

**Promotion review finding:**

- `F1` (`P2`): In the merged workflow, `Verify release inputs` runs the strict version check before `Allow an existing tag only at this commit`. If publication pushes the tag and then fails before all release assets are available, a rerun rejects the current version as not greater than the highest tag and cannot reach the resume step. This was reproduced with a temporary local tag; no remote release was changed. The current local branch contains a follow-up `--resume-at-head` verifier change and workflow call, but `container-release` remains at `71f52f8268daed3f04c501e50cf59341fbb1273d`, so that fix is not part of the published workflow yet.

**Deviations:** None to the approved design. Note: GitHub tag rulesets do not support restricting tag *creation* to a specific actor for this plan's purpose, so tag immutability is enforced by blocking deletion/update plus the workflow's refusal of an existing tag/Release; the workflow also fails before creating a Release if the tag push fails.

## Definition Of Done

- [x] Complete `T0.1` and `T0.2`; do not enable publication until GitHub protections have been verified. (2026-10-10: version file created; branch protection and tag ruleset configured and verified via API reads.)
- [x] Demonstrate `PH1-AC-1` and `PH1-AC-2` with recorded `V-1`, `V-2`, and `V-3` outcomes. (`V-1` and `V-3` passed; the first `V-2` publication and archive passed verification. The live retry check was explicitly waived by the user and is not claimed as passed.)
- [x] PRs cannot publish; a reviewed merge creates exactly one complete, checksummed, source-identified release at a distinct immutable tag. (PR #541 passed `validate` with `publish` skipped; the merge published one archive, checksum, and source-identified tag.)
- [x] Missing content and reused or inconsistent versions fail without overwriting a release. (Local negative cases passed; the retry simulation confirms the PR-era verifier refuses an already-used version.)
- [x] Application release files, tags, and version behavior remain unchanged; publication guidance matches shipped behavior. (The application release workflow and version remain unchanged; exact-tag guidance matches `container-v0.1.0`.)
- [x] Record any deviations or remaining questions; no unresolved decision affects implementation or validation. (Deviation recorded in the Execution Record.)

## Risks And Open Questions

- Resolved 2026-10-10: GitHub branch/tag controls were confirmed available and active (`T0.2`). One policy detail could not be enforced as written — tag *creation* cannot be restricted to the publication workflow — so immutability relies on the deletion/update tag ruleset plus the workflow's refusal of an existing tag or Release. This is recorded as a deviation, not a silent weakening.
- `F1` remains a follow-up before relying on automated recovery from partial publication failures. The local branch contains a verifier/workflow fix, but it must be reviewed and promoted before the `container-release` workflow can resume a publication after the tag exists. The user decided not to run the live retry check; this waiver does not resolve the recovery defect and does not block Phase 2.
