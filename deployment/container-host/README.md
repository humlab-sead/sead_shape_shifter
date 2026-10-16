# Container Host Tooling

This source-only tree holds the host-side tools, release-policy checks, and
regression tests for the Shape Shifter container release. Its scripts run from a
repository checkout as root; they are not shipped to a deployment user.

- `deploy/` — host provisioning and installer tools: `deploy_environment.sh`,
  the systemd and NGINX installers, the authorization bootstrap, the host
  prerequisite check (`get-install.sh`), and the deployment sync tool
  (`sync-to-deploy`). The retired release manager
  (`manage_container_release.sh`) is kept only as a reference.
- `verify/` — the read-only release-policy checker used by the
  `container-release` workflow, and its [README](verify/README.md).
- `tests/` — shell regression suites for the tools above.

This tree is not an operations toolkit. The
[SEAD Runtime Verification Handoff](../../docs/proposals/CONTAINER_SETUP_SIMPLIFICATION/OPERATIONS_VERIFICATION_HANDOFF.md)
lists the required operational outcomes without prescribing tools.

## Why it is outside `deployment/container/`

Release archives are built with
`git archive --format=tar.gz --prefix=container/ HEAD:deployment/container`, which
can only reach tracked files under `deployment/container/`. Because
`deployment/container-host/` is a sibling, nothing in it can enter a release
archive: an archive carries only deployment-user runtime contents, and host
tooling never reaches a deployment user. The `container-release` workflow runs
the checker here against the source tree and the built archive. The release
manager that once validated a downloaded archive with its own trusted code is
retired: environments now keep a manual copy of `deployment/container/` in
`~/container`, refreshed with `sync-to-deploy`, until images are published to
GHCR (see `docs/proposals/GHCR_IMAGE_RELEASE.md`).

## See also

- [../container/DEPLOYMENT.md](../container/DEPLOYMENT.md) — the operator
  workflow for placing and refreshing deployment files.
- [verify/README.md](verify/README.md) — the release-policy checks.
