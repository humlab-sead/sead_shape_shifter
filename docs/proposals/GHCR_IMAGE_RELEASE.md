# Publish Container Images From CI To GHCR And Deploy By Pull

## Status

- Proposed change request
- Scope: deployment image build and delivery model (`deployment/`, `.github/workflows/`)
- Goal: replace host-side image builds and the container-release archive flow with CI-built images published to GHCR, pulled by digest on each host.

## Summary

Build the Shape Shifter container image in GitHub Actions and publish it to
`ghcr.io/humlab-sead/shape-shifter`. Each deployment environment pulls a
digest-pinned image and restarts; the deploy host no longer clones the
repository or runs a build. This removes the build toolchain requirement from
deploy hosts, eliminates the `GIT_REF`/`IMAGE_NAME` drift failure mode, and
makes staging and production run the same artifact. It also retires most of the
`shape-shifter-container-release` manager, whose integrity and rollback
guarantees the registry already provides for images.

The `sead_authority_service` repository has historically published its images
to `ghcr.io/humlab-sead/` and still defines an (currently disabled) image
workflow for it. This proposal aligns Shape Shifter's image release with that
repository's conventions so both services under `humlab-sead` consume and
publish container images the same way.

## Problem

Today the image is built on each deploy host by `make build`, which clones the
repository at `GIT_REF` and builds the frontend and backend inside the build.
This causes recurring operational problems:

- **Drift between configuration and image.** `IMAGE_NAME` must be kept in step
  with `GIT_REF` by hand; DEPLOYMENT.md documents the failure mode where
  `make restart` silently starts the previous image.
- **No shared artifact.** The staging host and the production host build
  separate images from separate refs. Nothing proves the image validated on
  staging is the image promoted to production.
- **Build toolchain on deploy hosts.** Host builds need Node, Java, and full
  network access to GitHub on the machine that only needs to run a container.
- **Weak rollback.** Rolling an environment back means rebuilding or
  re-tagging a host-built image; the dated local tags
  (`shape-shifter:staging-20261016`) exist only on that host.
- **Duplicated release machinery.** The `container-release` workflow, the
  `container-vX.Y.Z` archives, and the 663-line
  `deployment/container-host/deploy/manage_container_release.sh` exist to give
  the deployment an immutable, verifiable, rollback-capable artifact. A
  container registry provides the same properties for the image itself, and
  the current flow does not version the image at all.

## Scope

- A GitHub Actions workflow that builds `deployment/container/Containerfile`
  and pushes to `ghcr.io/humlab-sead/shape-shifter`.
- Deploy-side change: pull the image by digest, record the digest in
  `~/config/deployment.env`, and start it with the existing
  `podman-compose.yml` / Makefile lifecycle.
- A thin host-side selection step for image activation and rollback, replacing
  the archive install/verify/activate flow for images.
- Migration of the existing environments (`test-shape-shifter.sead.se`,
  `shape-shifter.sead.se`) from host-built images to registry images.
- Keeping the image workflow and published packages within GitHub's free
  storage and operational limits for public repositories.
- Aligning image naming, tagging, digest pinning, and registry credentials
  with the `sead_authority_service` repository, the org's existing GHCR
  consumer, so the two services share one operational pattern.
- Documentation updates in `deployment/container/DEPLOYMENT.md` and the
  container README.

## Non-Goals

- Changing application versioning: semantic-release on `main` (`release.yml`)
  stays as it is; its tags become the trigger for image builds.
- Changing the runtime layout (`~/config`, `~/container-data`), nginx setup,
  authorization bootstrap, or systemd unit behavior.
- Image signing and admission policy (cosign, signature verification). The
  registry digest is the integrity check for this step; signing can be added
  later without changing the deploy flow.
- Removing local development builds: `make build-local` from a working tree
  remains available for developers.
- Distributing the deployment bundle (Makefile, scripts, compose file) inside
  the image. That remains a separate, later decision; see Open Questions.

## Current Behavior

Verified from the repository:

- `release.yml` runs semantic-release on pushes to `main` and creates
  application release tags. It builds no container image.
- `container-release.yml` publishes `container-vX.Y.Z` tarballs of
  `deployment/container/` plus a sha256 file as GitHub Release assets from the
  `container-release` branch. It builds no container image.
- `manage_container_release.sh` installs those archives under
  `/opt/shape-shifter/<user>/container-releases/`, verifies checksums and
  required files, and selects releases through a root-owned symlink. It
  manages deployment files only; the image is out of its scope.
- `make build` on the deploy host builds the image from `GIT_REPO`/`GIT_REF`
  in `~/config/deployment.env` and tags it locally
  (`shape-shifter:<ref>`, `shape-shifter:<ref>-<date>`).
- `podman-compose.yml` runs `image: ${IMAGE_NAME}` with `userns_mode:
  keep-id` and bind mounts under `~/config` and `~/container-data`. Nothing in
  the runtime requires the image to have been built locally.

## Proposed Design

### Image build workflow

Add `.github/workflows/image-release.yml`:

- Trigger: application release tags (`v*`) created by semantic-release, plus
  `workflow_dispatch` for manual builds. Pushes to `main` and `staging`
  produce a moving `:latest` / `:staging` tag for convenience only.
- Build `deployment/container/Containerfile` with the existing build args
  (`SOURCE=github`, `GIT_REF` from the trigger).
- Push to `ghcr.io/humlab-sead/shape-shifter` with tags `vX.Y.Z` and the
  immutable digest printed in the job summary.
- PRs build without pushing, so Containerfile changes are validated before
  merge.

### GitHub free-tier compliance

`humlab-sead/sead_shape_shifter` is a public repository, so standard
GitHub-hosted runners are free and public GHCR packages carry no storage or
egress charge (limits checked for the sibling service on 2026-10-11; see
`sead_authority_service/deployment/container/README.md`). The workflow and
packages must be developed to stay within the free allowances:

- Build on standard GitHub-hosted runners only; no larger or self-hosted
  runners are introduced for this workflow.
- Publish images directly to GHCR. Image archives are never uploaded as
  Actions artifacts.
- Keep Actions artifacts (for example a PR build summary, if any) within the
  500 MB artifact storage allowance and caches within the 10 GB cache
  allowance per repository; set short artifact retention.
- Keep the published package public so GHCR storage and pull egress stay
  free, and keep the tag set small (release tags plus at most one moving tag
  per branch) so package growth stays bounded.
- Base-image sourcing. The current `Containerfile` pulls its base images from
  Docker Hub (`alpine`, `node:<v>-alpine`, `python:<v>-slim`). Docker Hub
  limits anonymous pulls per source IP, and GitHub-hosted runners share IPs
  across repositories, so CI builds can fail with `429 toomanyrequests` even
  when the same pull succeeds from the deploy host. The workflow must avoid
  anonymous Docker Hub pulls: either authenticate `docker.io` in the build
  job with a free Docker Hub account, or reference base images through GHCR
  mirrors (`ghcr.io/<org>/mirror/...` or the equivalent upstream-maintained
  mirror). Whichever mechanism is chosen, the base images must remain
  free-to-redistribute open-source images (Alpine and Debian-based official
  images qualify), and the final image must stay a slim multi-stage build so
  package growth and pull traffic stay small.
- Recheck the current GitHub billing and limits rules before enabling the
  workflow or changing its triggers:
  [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions),
  [Actions limits](https://docs.github.com/en/actions/reference/limits),
  [GitHub Packages billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages).

### Alignment with sead_authority_service

`sead_authority_service` is the org's precedent for GHCR: its images live at
`ghcr.io/humlab-sead/sead_authority_service`, its deploy bundle documents the
pull/build conventions, and its `docker-build.yml` workflow exists but is
guarded with `if: false`, so publishing there is currently manual. This
migration must stay in step with that repository rather than inventing a
second pattern:

- Same org namespace (`ghcr.io/humlab-sead/`), lowercase package names, and a
  comparable tag scheme (version tags plus at most one moving tag per
  branch), so both packages look alike to hosts and to package cleanup.
- Same host-side contract: digest-pinned selection recorded in the
  deployment environment file, read-only package-scoped pull credential
  under the private config directory.
- Same free-tier rules (standard runners, direct GHCR publish, no image
  archives as artifacts) already stated for the authority service in its
  `deployment/container/README.md`.
- Coordinate before re-enabling the authority service workflow: if that repo
  re-enables image publishing, both repositories should adopt the same
  workflow shape (ideally one shared reusable workflow), rather than
  diverging twice. Triggering that change is out of scope here; the
  requirement is that this proposal's conventions do not block it.

### Deploy-side pull and selection

- The deploy user stores a read-only registry credential (fine-grained PAT
  scoped to the package, or an org package read token) under `~/config` with
  mode 600, alongside `.pgpass`.
- `~/config/deployment.env` gains `IMAGE_NAME=ghcr.io/humlab-sead/shape-shifter@sha256:<digest>`
  (or a tag plus a resolver that pins the digest at pull time). The existing
  `IMAGE_NAME` key keeps its meaning: the compose file already starts whatever
  `IMAGE_NAME` names.
- A small host helper (replacing the image-related role of the release
  manager) performs `select-image <ref>`: resolve and pull the digest, record
  the previous selection, rewrite `IMAGE_NAME`, and restart through
  `scripts/container.sh`. `rollback` re-selects the previous recorded digest.
  No download verification machinery: the registry digest is the check.
- `make build` on deploy hosts is removed from the documented flow; hosts run
  `make pull` (new target wrapping the helper) instead.

### Bundle handling

The deployment bundle (Makefile, scripts, compose file, unit) still needs a
source. This proposal keeps the existing `container-vX.Y.Z` archive flow for
the bundle unchanged in the first step, and defers the choice between keeping
it and simplifying it (git-tag checkout, or shipping the ops scripts inside
the image) to a follow-up decision once image releases are live.

### Migration

1. Build and push the current `staging` commit from CI.
2. On `test-shape-shifter.sead.se`: pull by digest, update `IMAGE_NAME`,
   restart, run `make healthcheck`, and rehearse rollback to the previous
   host-built image tag.
3. On `shape-shifter.sead.se`: repeat, then remove host build leftovers.
4. Update DEPLOYMENT.md and README to make pull-based deploy the documented
   path.

## Alternatives Considered

- **Keep host builds with the current release manager.** Rejected: keeps the
  drift failure mode, per-host toolchain, and no shared artifact; the manager
  still does not version images.
- **Ship the ops bundle inside the image now.** Deferred: cleanest end state,
  but it reworks the Makefile/compose entry points at the same time as the
  registry move. Splitting the decisions keeps each migration small.
- **Docker Hub instead of GHCR.** Rejected: the org already uses GHCR for
  `sead_authority_service`; GHCR is private-by-default for private repos and
  needs no extra account.
- **Build images on the release branch like `container-release.yml`.**
  Rejected: image builds should follow the application release stream on
  `main`, not a separate bundle branch.

## Risks And Tradeoffs

- **GitHub availability becomes a deploy dependency.** Mitigation: the last
  pulled image stays on the host and restarts offline; only a *new* selection
  needs the network.
- **Private package pull credentials on hosts.** Mitigation: read-only,
  package-scoped token, mode 600, same handling as `.pgpass`.
- **Moving tags are mutable.** Mitigation: `deployment.env` records digests;
  tags are human-readable annotations only.
- **Losing the release manager's bundle checks if it is retired too early.**
  Mitigation: this proposal retires it for images only; the bundle flow stays
  until a separate decision replaces it.
- **One-time migration cost** on two live environments. Bounded: each is a
  pull, one config edit, and a restart with a rehearsed rollback.
- **Free-tier operation depends on the repository staying public.** If it ever
  turns private, GHCR storage and Actions runner minutes become metered.
  Mitigation: the workflow design above (standard runners, no artifact
  archives, small tag set) keeps usage low enough to fit the GitHub Free
  allowances for private repositories, and the billing links above are the
  recheck point.

## Testing And Validation

- Workflow validation: PR builds the image without pushing; a tagged run
  pushes `vX.Y.Z` and reports the digest.
- Pull validation on the test environment: `make pull`, `make restart`,
  `make healthcheck` green; container logs show the expected version from
  `/api/v1/health`.
- Rollback validation: `select-image` rollback returns the environment to the
  previous digest and health passes.
- Parity validation: staging and test report the same image digest for the
  same release.
- Offline validation: `make restart` succeeds with the network path to GHCR
  unavailable, using the cached image.
- Free-tier validation: after the first runs, the repository's Actions
  storage/cache usage and the GHCR package visibility confirm the workflow
  stayed within the free allowances.
- Convention-parity validation: package name, tag scheme, digest-pinned
  selection, and credential handling match the conventions documented in
  `sead_authority_service/deployment/container/README.md`, or the differences
  are recorded as deliberate.

## Acceptance Criteria

- `P-AC-1` A GitHub Actions workflow builds the container image and pushes it
  to `ghcr.io/humlab-sead/shape-shifter` on application release tags, and
  builds without pushing on pull requests.
- `P-AC-2` Both `test-shape-shifter.sead.se` and `shape-shifter.sead.se` run
  images pulled from GHCR, with the running digest recorded in
  `~/config/deployment.env`.
- `P-AC-3` Neither deploy host requires the repository clone or build
  toolchain to start the service after migration; `make up`/`make restart`
  work against the pulled image.
- `P-AC-4` Rollback to the previous digest on one environment is rehearsed and
  returns the environment to a healthy state.
- `P-AC-5` The registry credential is read-only, package-scoped, stored under
  `~/config` with mode 600, and never mounted into the container.
- `P-AC-6` Two environments run the identical image digest for the same
  release, verified by `podman inspect` digest comparison.
- `P-AC-7` DEPLOYMENT.md and the container README document pull-based deploy
  as the default path and no longer instruct host builds for deployment
  environments.
- `P-AC-8` The image workflow uses only standard GitHub-hosted runners,
  publishes images directly to GHCR without image archives as Actions
  artifacts, keeps the package public, and its artifacts and caches stay
  within the free allowances (500 MB artifacts, 10 GB cache per repository).
- `P-AC-9` CI image builds do not depend on anonymous Docker Hub pulls: base
  images are pulled through an authenticated `docker.io` login or a GHCR
  mirror, and repeated PR builds show no `429 toomanyrequests` failures.
- `P-AC-10` The published package and the host-side pull/selection flow
  follow the same conventions as `sead_authority_service` (org namespace,
  tag scheme, digest pinning, read-only package-scoped credential, free-tier
  rules), and any deliberate divergence is documented in DEPLOYMENT.md.

## Planning Handoff

- Confirmed decisions:
  - Images are built only in CI and consumed by pull; host builds are not a
    documented deploy path.
  - `IMAGE_NAME` in `~/config/deployment.env` remains the single selection
    point consumed by `podman-compose.yml`.
  - Digests, not tags, are the recorded selection.
  - The `container-vX.Y.Z` bundle flow continues unchanged until a separate
    decision.
- Behavior to preserve:
  - The `container.sh` dispatcher is the single start/stop path for systemd
    and operators alike.
  - `~/config` mode 700, secrets mode 600, `.pgpass` never widened.
  - `userns_mode: keep-id` and the current bind-mount layout.
  - GitHub free-tier operation: standard runners only, public GHCR package,
    no image archives as artifacts, artifacts/caches within free allowances.
- Expected validation outcomes: the checks in Testing And Validation,
  including the offline restart and the digest-parity check.
- Open questions with required resolution phase:
  - Exact workflow triggers and moving-tag policy (Phase 1).
  - Base-image sourcing mechanism: authenticated `docker.io` pull versus GHCR
    mirror for `alpine`, `node`, and `python` (Phase 1, before the first CI
    build).
  - Whether `select-image` is a new script under `deployment/container-host/`
    or a slimmed role inside the existing manager (Phase 1).
  - Credential mechanism: org package read token vs per-host fine-grained PAT
    (Phase 1, before the first private pull).
  - Whether the image workflow is written as a GitHub reusable workflow now,
    so `sead_authority_service` can adopt the same file when its disabled
    `docker-build.yml` is re-enabled (Phase 1).
  - Bundle distribution end state after images move (Phase 2 or a separate
    proposal).

## Open Questions

- Should `staging`-branch builds publish a moving `:staging` tag, or should
  staging also pin digests from the first CI build?
- When is `manage_container_release.sh` formally retired versus reduced to
  bundle selection only?

## Final Recommendation

Add the CI image workflow, migrate both environments to digest-pinned GHCR
pulls, and keep the bundle archive flow untouched for now. This delivers the
integrity, rollback, and staging/production parity the current release
machinery aims at, with less host-side machinery, and sets up a simple
follow-up decision for the remaining bundle files.
