# Container Host Tooling

This source-only tree holds the host-side tools, release-policy checks, and
regression tests for the Shape Shifter container release. Its scripts run from a
repository checkout as root; they are not shipped to a deployment user.

- `deploy/` — host provisioning, installer, and release-management tools:
  the release manager, `deploy_environment.sh`, the systemd and NGINX
  installers, the authorization bootstrap, the host prerequisite check
  (`get-install.sh`), and the development sync tool.
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
the checker here against the source tree and the built archive, and the host
release manager validates a downloaded archive with its own trusted code rather
than any file from the archive.

## See also

- [../container/DEPLOYMENT.md](../container/DEPLOYMENT.md) — the operator
  workflow for installing and selecting releases.
- [verify/README.md](verify/README.md) — the release-policy checks.
