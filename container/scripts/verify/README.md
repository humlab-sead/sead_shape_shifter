# Deployment verification scripts

Read-only checks for the Shape Shifter deployment on this host. Each read-only
script exits non-zero on a failed check and never changes rules, services,
containers, images, or configuration. `rollback_exercise.sh` deliberately
changes the deployment as a controlled rollback test. The orchestrator runs
read-only checks by default; its authenticated and rollback phases are
explicitly opt-in. Record every result with the date and host.

| Script | Verifies |
| --- | --- |
| `verify_firewall.sh` | The backend binds loopback only, no firewall rule exposes the backend port, and the reverse proxy is the only external entry point. |
| `verify_container_config.sh` | The running container's loopback-only port, bind mounts, environment variable names (never values), and image labels and history. |
| `verify_postgres_grants.sh` | The read-only PostgreSQL role's grants in the release database and the authorization SQLite store's ownership and mode. |
| `verify_logs.sh` | The container, nginx, and PostgreSQL logs for credentials, connection strings, SQL text, and filesystem paths (candidate scan for operator review). |
| `verify_credential_rotation.sh` | The backend credentials that were reachable during the LAN-exposure window, listed by name (values never printed), plus the per-credential rotation or approved-exception record. |
| `verify_endpoint_containment.sh` | That the execution, raw YAML, data-source creation, and ingester endpoints reject unauthenticated (401) and unauthorized (404/403) calls, so no separate disablement is needed; records the ingester enforcement gap. |
| `setup.sh` / `teardown.sh` | Create and remove a registered disposable project and its temporary project-creator authorization role for containment checks. |
| `verify_authenticated_access.sh` | Through the proxy, that each of two real principals reaches only its own project (allowed 200, denied 404), and that the proxy rejects requests without credentials (401). |
| `rollback_exercise.sh` | Restores a recorded image and authorization backup, checks SQLite integrity, reconciles the authorization manifest, and verifies the resulting service health. This script changes deployment state. |
| `run_deployment_verification.sh` | Runs the host and deployment-user checks, captures evidence and a summary, and optionally runs authenticated access and rollback. |
| `deployment-verification.options.yml.example` | Safe template for the orchestrator's non-secret runtime options. |

Run from the deployment user's `container/` directory; the firewall script can run from any account with `sudo`.

The orchestrator can be run by a sudo-capable operator from this directory. It
resolves the target user's `~/container` and rootless Podman context, runs
deployment checks as that user, runs host checks as the operator, and writes a
concise report to `summary.txt` in a timestamped run directory under
`~/container-data/deployment-verification/`, next to the rest of the deployment's
writable paths and outside the replaceable checkout. The container mounts only
`projects/`, `shared/`, `logs/`, `output/`, `backups/`, `tmp/`, and `state/`, so
that directory stays off the container's filesystem. Detailed check output is
stored in separate evidence files. The current options file is copied into the run
directory as `deployment-verification.options.yml` alongside the report. Pass
`--evidence-dir` to use that directory exactly; an `evidence_dir` value in the
options file is treated as the parent directory for the timestamped run.

```bash
cp ./scripts/verify/deployment-verification.options.yml.example \
  ~/config/deployment-verification.options.yml
# Edit ~/config/deployment-verification.options.yml, then run:
./scripts/verify/run_deployment_verification.sh \
  --options-file ~/config/deployment-verification.options.yml
```

The file is read with `yq` before command-line parsing. Explicit command-line
options override values from the YAML file. Keep passwords, tokens, and other
credentials out of the file; the authenticated check prompts for passwords
separately.

To avoid a pre-existing project for endpoint containment, pass
`--disposable-project-template` with a directory containing `shapeshifter.yml`.
The orchestrator creates a unique project through the API, registers its
authorization resource, loads the template, and deletes the project and its
temporary creator role in an exit cleanup step. It uses loopback trusted-proxy
identities and does not create nginx users or passwords. The template shipped
with these scripts is `disposable-project/shapeshifter.yml`.

Add `--authenticated` together with `--principal-a`, `--principal-b`,
`--project-a`, and `--project-b` to run the interactive principal-isolation
check. Passwords are still prompted by the underlying check and are never
passed as orchestrator arguments. Add `--rollback` with `--rollback-image`,
`--authorization-backup`, and `--manifest` only during the approved rollback
window. If the target's user service is active, the orchestrator stops it for
rollback and restarts it only after rollback verification succeeds.

```bash
# Firewall and network exposure (needs sudo for the firewall listing)
./scripts/verify/verify_firewall.sh            # port 8012, auto-detect LAN IP
./scripts/verify/verify_firewall.sh 8013 172.18.134.53

# Container mounts, environment, and image (run as the deployment user)
sudo -u test-shape-shifter.sead.se -H bash ./scripts/verify/verify_container_config.sh

# PostgreSQL grants and the SQLite authorization store (run as the deployment user)
./scripts/verify/verify_postgres_grants.sh \
  --database sead_staging --role sead_ro --schema public \
  --sqlite "$DATA_DIR/state/authorization.sqlite3"

# Log sweep for the last 24h (run as the deployment user; sudo includes nginx logs)
./scripts/verify/verify_logs.sh --since 24h --db-log /var/log/postgresql/postgresql.log

# Credential rotation record (run as the deployment user). First run lists the
# credentials and their LABELs and exits non-zero while any row is pending.
./scripts/verify/verify_credential_rotation.sh
# After rotating, re-run recording one decision per LABEL to complete the record:
./scripts/verify/verify_credential_rotation.sh \
  --rotated pgpass:localhost:5432:sead_staging:sead_ro \
  --rotated env:SEAD_PASSWORD \
  --declined "env:SIMS_API_TOKEN=rotated by SIMS team, ticket 1234"

# Endpoint containment (run as the deployment user against the loopback backend;
# use an existing, disposable project so a broken check cannot write to real data).
./scripts/verify/verify_endpoint_containment.sh --project <existing-project>

# Endpoint containment with a temporary project; cleanup is automatic.
./scripts/verify/run_deployment_verification.sh \
  --options-file ~/config/deployment-verification.options.yml \
  --disposable-project-template ./scripts/verify/disposable-project

# Authenticated access and cross-resource isolation through the proxy (run as the
# deployment user). Passwords come from PRINCIPAL_A_PASSWORD / PRINCIPAL_B_PASSWORD
# or from a terminal prompt. Projects must be granted to exactly one principal each.
PRINCIPAL_A_PASSWORD=... PRINCIPAL_B_PASSWORD=... ./scripts/verify/verify_authenticated_access.sh \
  --base-url https://test-shape-shifter.sead.se \
  --principal-a alice --principal-b bob \
  --project-a project-alice --project-b project-bob

# Rollback exercise (mutates the deployment; run only in the approved window).
# The image must already exist locally, identified by an immutable tag or digest.
./scripts/verify/rollback_exercise.sh \
  --image localhost/shape-shifter@sha256:<recorded-digest> \
  --authorization-backup "$DATA_DIR/backups/authorization-20260916-120000.sqlite3" \
  --manifest "$CONFIG_DIR/authorization-manifest.yml" \
  --evidence-dir "$DATA_DIR/backups/rollback-20260917" \
  --yes
```

`verify_postgres_grants.sh` authenticates to PostgreSQL via `~/.pgpass`; pass `--host`, `--port`, and `--username` when the database is not on the local socket. `verify_firewall.sh` prints the cross-host `nc` commands to run from a second machine; that step cannot run from the host itself.
