# Container release verification

This directory contains the read-only release-policy checker used by the
`container-release` workflow:
[`verify_container_release.sh`](verify_container_release.sh).

The checker validates the container version and release policy, the required
deployment files, the absence of host tooling and development tests, and the
archive contents. The workflow runs it against the source tree and the built
archive:

```bash
bash deployment/container-host/verify/verify_container_release.sh dir --require-main-merged
bash deployment/container-host/verify/verify_container_release.sh archive container-vX.Y.Z.tar.gz
```

The host release manager validates a downloaded archive with its own checksum,
path-safety, expected-root/version, and required-file checks. It never executes
a file from the downloaded archive.

This directory lives outside the `container/` release bundle, so it never ships
in a release archive, and it provides no host or deployed-runtime verification.
The
[SEAD Runtime Verification Handoff](../../../docs/proposals/CONTAINER_SETUP_SIMPLIFICATION/OPERATIONS_VERIFICATION_HANDOFF.md)
lists tool-agnostic outcomes for operations; it is not an operating procedure
or an implementation of those checks.
