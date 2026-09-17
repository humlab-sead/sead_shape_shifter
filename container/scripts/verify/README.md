# Deployment verification scripts

Read-only checks for the Shape Shifter deployment on this host. Each script exits non-zero on a failed check and never changes rules, services, containers, images, or configuration. Record each script's output with the date and host.

| Script | Verifies |
| --- | --- |
| `verify_firewall.sh` | The backend binds loopback only, no firewall rule exposes the backend port, and the reverse proxy is the only external entry point. |
| `verify_container_config.sh` | The running container's loopback-only port, bind mounts, environment variable names (never values), and image labels and history. |
| `verify_postgres_grants.sh` | The read-only PostgreSQL role's grants in the release database and the authorization SQLite store's ownership and mode. |
| `verify_logs.sh` | The container, nginx, and PostgreSQL logs for credentials, connection strings, SQL text, and filesystem paths (candidate scan for operator review). |
| `verify_credential_rotation.sh` | The backend credentials that were reachable during the LAN-exposure window, listed by name (values never printed), plus the per-credential rotation or approved-exception record. |

Run from the deployment user's `container/` directory; the firewall script can run from any account with `sudo`.

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
```

`verify_postgres_grants.sh` authenticates to PostgreSQL via `~/.pgpass`; pass `--host`, `--port`, and `--username` when the database is not on the local socket. `verify_firewall.sh` prints the cross-host `nc` commands to run from a second machine; that step cannot run from the host itself.
