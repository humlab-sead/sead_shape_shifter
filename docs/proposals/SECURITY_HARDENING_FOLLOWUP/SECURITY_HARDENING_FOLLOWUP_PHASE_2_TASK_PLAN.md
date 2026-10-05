# Security Hardening Follow-up - Phase 2 Task Plan

Repository-verified task plan for **Phase 2: Remove root execution of deployment-user-writable configuration and shared credentials**.

Source: [Security Hardening Follow-up](SECURITY_HARDENING_FOLLOWUP.md) and [Phase Plan](SECURITY_HARDENING_FOLLOWUP_PHASE_PLAN.md#phase-2-remove-root-execution-of-deployment-user-writable-configuration-and-shared-credentials). The phase plan records decisions `D-1` and `D-2`; this document covers only Phase 2.

## Phase Summary

- **Goal:** Make root bootstrap safe, isolate authentication by environment and principal, and remove administrator passwords from child-process arguments (ledger 16, 27, 26).
- **Readiness:** **Draft.** The phase plan says "Ready for a task plan," but its root-only reviewed manifest and deploy-user-run import have no specified handoff. Resolve the question below before marking this plan Validated or executing the manifest migration. Other work can be reviewed against the fixed decisions.
- **Dependencies:** Phase 1's disposable reproduction environment; `D-1` (per-domain root-owned tree, data-only root scripts, separate nginx paths and reduced sudo) and `D-2` (independent secrets and retirement of `AUTH_PASSWORD`). Do not run the ledger's root-only tests on the host.
- **Preserve:** Deployment-user-owned `~/config` for `backend.env`, `deployment.env`, and `.pgpass`; nginx's trusted `X-Authenticated-User` and `X-Authenticated-Groups` contract; existing deployment-user Podman and systemd ownership. Phase 3 owns manifest atomicity and lifecycle audit-actor repair; phase 6 owns the remaining deployment defaults and PATH behavior.

Acceptance criteria:

- [ ] `PH2-AC-1` (from `P-AC-4`): Bootstrap rejects configuration that fails the decided root ownership rule with a clear error; the documented compliant provisioning path succeeds end to end.
- [ ] `PH2-AC-2` (from `P-AC-4`): Named principals authenticate with independent secrets; no shared password or silent fallback remains.
- [ ] `PH2-AC-3` (from `P-AC-4`): No deployment flow puts an administrator password in child argv.

## Repository Findings

**Repository basis:** `security-hardening-phase-1` at `732c77d0`, 2026-09-24. Unrelated working-tree changes (`uv.lock`, untracked `docs/ai/` note and `gitleaks-report.json`) were not used as implementation inputs. Graphify's scoped query returned general deployment-document nodes, not the controlling scripts; all findings below come from current files.

| Source | Observed behavior | Consequence for plan |
|---|---|---|
| `container/scripts/deploy/bootstrap-authentication-and-authorization.sh` | Sources `CONFIG_DIR/authorization.env` before checking EUID, writes a fixed `/etc/nginx/htpasswd/shape-shifter` and a fixed groups file, then uses `sudo -u` to grant roles and import the manifest | Split root file operations from deploy-user operations; reject unsafe inputs before writes; parameterize every auth artifact by domain |
| `container/scripts/authorization.sh::import_manifest` | Requires a readable path, redirects that file into `podman exec -i ... tee`, then runs `migrate --manifest` | A deployment-user-run importer cannot open the root:root 0600 manifest chosen by `D-1` without an explicit trusted handoff |
| `container/scripts/deploy/install_nginx_reverse_proxy.sh` and `nginx-shape-shifter.conf.template` | Installer sources `../load-env.sh` and renders a template beside the checkout; template has a shared groups map, wildcard include, commented-out Basic-auth directives and a shared upstream name | Relocate all root-consumed code and template inputs together; render environment-specific map, upstream and file paths and verify multiple active vhosts with `nginx -t` |
| `container/scripts/deploy/deploy_single_environment.sh`, `install_systemd_service.sh`, `sync-to-deploy`; `container/scripts/verify/run_deployment_verification.sh` | First two require root mainly to call `sudo -u`; sync script targets the deployment account; verifier asks for sudo then uses `sudo -u` | Replace unnecessary root invocation while keeping the target-user workflow; review the multi-environment caller `deploy_all_environments.sh` |
| `container/scripts/verify/complete_test_deployment_verification.sh`, `verify_authenticated_access.sh` | Cleanup passes `-u "$ADMIN_USER:$admin_password"`; authenticated access passes `-u "$user:$pass"`. Bundle can skip `nginx -t` with a warning | Use stdin or a protected transient credential source for curl; do not confuse Phase 2's sudoers change with Phase 7's skipped-check exit-status repair |
| `container/scripts/setup.sh`, `verify_credential_rotation.sh`, `container/resources/authorization.env.example`, `container/DEPLOYMENT.md`, `container/README.md`, `docs/OPERATIONS.md` | Setup and docs assume auth files under deploy-owned `~/config`; rotation checker reads that `authorization.env` | Align setup messaging, rotation checks, and operator instructions with per-domain root provisioning |
| `docs/testing/SECURITY_LEDGER_REPRODUCTION.md`, `secrets/FINDINGS.md` (local, untracked) | Ledger test 16 exercises non-root-owned input and a root-owned control; test 27 rejects the shared value and silent fallback; no ledger test is named for 26 | Maintain reviewable regressions in tracked tests; run external ledger tests only in a disposable environment and never commit `secrets/` |

## Scope

**In:** Host bootstrap provisioning and ownership checks, per-domain nginx authentication, per-principal secret migration, necessary script relocation and de-rooting, credential-safe curl calls, operational instructions, and isolated tests. New test and install targets below are **NEW**; their paths are planned, not existing code.

**Out:** Live-host changes during plan creation; moving application config into root storage; Phase 3 manifest transaction semantics; Phase 6 release pinning/PATH repairs beyond removing the root bootstrap's override; Phase 7 verification exit-status policy. Keep external ledger fixtures untracked.

## Work Breakdown

### Area 1: Install trusted host scripts and per-domain nginx inputs

**Objective:** Root never executes or renders content from the deploy-writable checkout and one environment cannot overwrite another's authentication files.

**Affected code:** `container/scripts/deploy/bootstrap-authentication-and-authorization.sh`, `install_nginx_reverse_proxy.sh`, `nginx-shape-shifter.conf.template`, `container/DEPLOYMENT.md`; `tests/deployment/test_phase2_auth.sh` (**NEW**).

**Dependencies:** Fixed `D-1` layout; test VM for filesystem and nginx checks.

- [ ] `T2.1` **Install root-owned code and template:** Document operator-run copy/install commands for the two root-executed scripts **and** the vhost template from a reviewed release artifact into `/usr/local/sbin/shape-shifter/`. Root must copy the files as data, not execute an installer script in the replaceable checkout. Specify root-owned non-writable ancestors, atomic replacement, version/rollback procedure, and how a release refresh updates these copies without executing code from `~/container`. Audit `install_nginx_reverse_proxy.sh`'s source of `load-env.sh`: a root-owned script must not source the deploy checkout; take validated port/domain input as data instead. Avoid `sudo tar` extraction through an attacker-replaceable deploy-owned path as the privileged installer. Validate with `V-1`, `V-4`.
- [ ] `T2.2` **Scope nginx configuration to a domain:** Render an allowlisted domain and numeric upstream port; point Basic auth and the group include at `/var/lib/shape-shifter/<domain>/`; give the `map` and upstream unique nginx names per site. Replace the wildcard group include with that environment's file, and ensure the active site enables authentication where expected. Verify both existing test and additional staging/production-style vhosts load together; no shared principal or group path remains. Validate with `V-2`, `V-4`.

**Completion evidence:** Root-installed copies, not checkout files, supply vhost code and template; multiple vhosts pass `nginx -t` and use separate auth paths.

### Area 2: Provision data-only root configuration and independent credentials

**Objective:** A compromised deployment account cannot make root execute input or read another environment's credentials; password rotation is per principal.

**Affected code:** `container/scripts/deploy/bootstrap-authentication-and-authorization.sh`, `container/scripts/verify/verify_credential_rotation.sh`, `container/resources/authorization.env.example`, `container/scripts/setup.sh`; `tests/deployment/test_phase2_auth.sh` (**NEW**).

**Dependencies:** `T2.1`; manifest handoff decision before replacing the import flow.

- [ ] `T2.3` **Constrain bootstrap inputs:** Take a validated domain and resolve only `/var/lib/shape-shifter/<domain>/` under root-controlled parents. Reject symlinks, non-root owners, and group/world writable ancestors or input files before opening or writing; use a strict literal `KEY=VALUE` parser with an explicit key set, no shell evaluation/expansion, and reject `AUTH_PASSWORD` outright. Validate roster names and paths (no slash/traversal) and all required values before any htpasswd change. Keep `~/config` for deploy configuration only. Validate with `V-1`, `V-4`.
- [ ] `T2.4` **Provision independent secrets safely:** Define first-run initialization separately from steady-state bootstrap: generate strong random secret files root:root 0600 under `secrets/` for each named principal (including the admin), print each only at controlled first handoff, and never echo it on a rerun. A missing existing principal file fails instead of regenerating or using a shared value; explicit rotation rewrites only that principal and its htpasswd entry. Write htpasswd and group membership atomically with owner root:www-data 0640 under the per-domain root:www-data 0750 tree; keep `secrets/` root-only. Migrate the test environment with fresh secrets and a rollback copy restricted to root. Validate with `V-1`, `V-2`, `V-3`.
- [ ] `T2.5` **Move role grants and manifest import to the deployment-user flow:** Remove root bootstrap's `target_run` and hard-coded `TARGET_PATH`. Preserve the existing Podman-role operations and reviewed-manifest import using a concrete, documented trusted manifest handoff. Do not silently make a root-only file deploy-readable or import an unreviewed deploy-owned file. This task is blocked until the handoff in Risks And Open Questions is fixed in `D-1`. Validate with `V-1`, `V-2`.

**Completion evidence:** The first run installs isolated credentials, a rerun neither regenerates nor reveals them, malicious inputs fail before any root effect, and the chosen import flow uses the reviewed manifest.

### Area 3: Remove convenience root and password argv exposure

**Objective:** Deploy-user tasks run with that user's authority, and verification never places plaintext credentials in child arguments.

**Affected code:** `container/scripts/deploy/deploy_single_environment.sh`, `deploy_all_environments.sh`, `install_systemd_service.sh`, `sync-to-deploy`, `container/scripts/verify/run_deployment_verification.sh`, `complete_test_deployment_verification.sh`, `verify_authenticated_access.sh`; `tests/deployment/test_phase2_auth.sh` (**NEW**).

**Dependencies:** `T2.1` for release instructions; separate executable-test environment for `V-3`.

- [ ] `T2.6` **De-root user workflows:** Remove root gates and root-to-user wrappers where they only dispatch deploy-user tasks; make caller requirements explicit for `deploy_single_environment.sh`, `install_systemd_service.sh`, `sync-to-deploy`, and verifier. Update `deploy_all_environments.sh`'s caller instructions. Preserve `sudo -u <deploy-user>` only when an operator must switch user. Supply a narrow `nginx -t` sudoers rule for the verification bundle; do not grant broad root shell or fix skipped-check reporting here (Phase 7). Validate with `V-3`, `V-4`.
- [ ] `T2.7` **Keep credentials out of curl argv:** Replace both `curl -u user:password` uses with stdin-based curl config or equivalent supported input that never puts the password in argv, command traces, temp files, or logs. Exercise the real authenticated and cleanup paths and assert the request still works and child argv never contains the secret. Validate with `V-3`, `V-4`.

**Completion evidence:** A deploy-user workflow runs without a root shell, and both verification callers authenticate with no password in child argv.

### Area 4: Document and rehearse the cutover

**Objective:** Operators can provision, migrate, verify, rotate, and roll back test, staging, and production independently.

**Affected documentation/scripts:** `container/DEPLOYMENT.md`, `container/README.md`, `docs/OPERATIONS.md`, `container/resources/authorization.env.example`, `container/scripts/setup.sh`, `container/scripts/verify/verify_credential_rotation.sh`.

**Dependencies:** Areas 1-3 and the trusted manifest handoff decision.

- [ ] `T2.8` **Publish and rehearse the procedure:** Document the host (not container) paths, root/deploy-user commands, per-domain installation and migration order, one-time handoff and rotation, how to validate the active nginx site before/after reload, and how to retain a root-only rollback copy without putting old shared passwords back into service. Update setup and rotation checker so they no longer expect auth inputs under `~/config`; preserve the deployment-only `load-env.sh` contract. Rehearse test before staging/production and record per-domain results. Validate with `V-1`, `V-2`, `V-5`.

**Completion evidence:** The disposable deployment reproduces provisioning and migration using only the documented commands; paths and expected permissions match the live nginx configuration.

## Acceptance-Criteria Coverage

| Criterion | Tasks | Validation | Expected result |
|---|---|---|---|
| `PH2-AC-1` (`P-AC-4`) | `T2.1`, `T2.3`, `T2.5`, `T2.8` | `V-1`, `V-4`, `V-5` | Host-owned input succeeds; writable, replaced or symlinked paths fail without root effects; documented end-to-end bootstrap/import succeeds |
| `PH2-AC-2` (`P-AC-4`) | `T2.2`, `T2.4`, `T2.5`, `T2.8` | `V-1`, `V-2` | Different principals and environments have different secrets and group headers; no shared fallback |
| `PH2-AC-3` (`P-AC-4`) | `T2.6`, `T2.7` | `V-3`, `V-4` | Child argv during actual cleanup/access contains no administrator password |

## Validation And Testing

Run privileged, nginx and external-ledger checks **only** in a disposable VM/full-stack test environment with no writable host mounts, using [the reproduction guide](../../testing/SECURITY_LEDGER_REPRODUCTION.md). The Phase 1 slim environment proves host isolation but does not by itself provide nginx, Podman and the database needed for end-to-end `VM-2.1`-`VM-2.3`. The untracked ledger package is optional corroboration, not the only regression coverage.

| ID | Check and exact method | Covers | Expected result | Baseline (2026-09-24) |
|---|---|---|---|---|
| `V-1` | `tests/deployment/test_phase2_auth.sh` (**NEW**), executed as root **in the disposable environment** against staged scripts and fixture users. Cases: root-owned good file; deploy-owned file; symlink/ancestor rename; injected shell text; first-run init; rerun after missing secret; trusted manifest/role flow. Optionally run ledger `test_16_bootstrap_refuses_env_file_not_owned_by_root` and `test_27_bootstrap_gives_each_named_principal_its_own_secret` through operator-supplied `RUN.sh` inside that environment. Compare before/after host path owner, mode, mtime. | `PH2-AC-1`, `PH2-AC-2`; `VM-2.1` | Only compliant provisioning changes files; unsafe inputs exit nonzero and do not run; no host effects | Not run: new test and full-stack VM not yet provisioned; external tests must not run on workstation |
| `V-2` | In the disposable full-stack environment install two rendered nginx vhosts, then `nginx -t`; authenticate principals A/B to each site's Basic-auth endpoint with the independent handed-off secrets and compare `$remote_user`-derived identity and `X-Authenticated-Groups` behavior through `container/scripts/verify/verify_authenticated_access.sh` or a dedicated isolated probe in `tests/deployment/test_phase2_auth.sh` (**NEW**). Check cross-principal and cross-domain rejection. | `PH2-AC-2`; `VM-2.2` | Correct credentials succeed only for their own principal/environment; wrong credentials return 401; no group bleed | Not run: no staged per-domain files/full-stack VM |
| `V-3` | `tests/deployment/test_phase2_auth.sh` (**NEW**) invokes both actual curl sites with a stubbed `curl` that records argv safely (sentinel credentials, never real secrets), checks authentication still receives usable input, and checks deploy-user invocation; full-stack VM exercise of cleanup verifies response. | `PH2-AC-3`; `VM-2.3` | Neither child argv includes the sentinel, cleanup still works | Not run: test not yet written; current `-u user:password` sites observed |
| `V-4` | From repo root: `bash -n` on each touched `.sh` file and `container/scripts/deploy/sync-to-deploy`; `shellcheck -S warning` on the same set, plus nginx template render and `nginx -t` inside disposable VM. | All; script/config regressions | No new shell diagnostics or malformed vhosts | Baseline Fail: `shellcheck -S warning` on current eight-script set reports two `SC1007` warnings in `sync-to-deploy`; syntax and nginx checks not run |
| `V-5` | From repo root: `scripts/check_doc_links.sh`; manually compare the deployment/operations commands and paths to the created files and `stat` output in the disposable VM. | `PH2-AC-1`, `PH2-AC-2`; docs | Links pass; root/deploy commands, file ownership and rotation instructions match the tested system | Not run for new plan; existing docs describe deploy-owned authorization inputs |

## Deliverables

| Result | Exact target | Tasks | Completion evidence |
|---|---|---|---|
| Privileged install and per-domain vhost | `container/DEPLOYMENT.md` (operator install commands); `container/scripts/deploy/install_nginx_reverse_proxy.sh`; `container/scripts/deploy/nginx-shape-shifter.conf.template` | `T2.1`, `T2.2` | Installed root-owned copies and independent nginx configuration |
| Bootstrap and deploy-user authorization | `container/scripts/deploy/bootstrap-authentication-and-authorization.sh`; `container/scripts/authorization.sh` (only if the chosen handoff requires its input contract to change) | `T2.3`-`T2.5` | Strict preflight, independent secrets, reviewed policy imported |
| Unprivileged deployment and safe verification | `container/scripts/deploy/deploy_single_environment.sh`, `deploy_all_environments.sh`, `install_systemd_service.sh`, `sync-to-deploy`; `container/scripts/verify/run_deployment_verification.sh`, `complete_test_deployment_verification.sh`, `verify_authenticated_access.sh` | `T2.6`, `T2.7` | Deploy-user flow runs; no password in argv |
| Regression and rotation checks | `tests/deployment/test_phase2_auth.sh` (**NEW**); `container/scripts/verify/verify_credential_rotation.sh` | `T2.3`, `T2.4`, `T2.7`, `T2.8` | Isolated negative/control tests and per-principal rotation report |
| Operator documentation and template | `container/DEPLOYMENT.md`; `container/README.md`; `docs/OPERATIONS.md`; `container/resources/authorization.env.example`; `container/scripts/setup.sh` | `T2.8`, `T2.4` | Tested per-domain provisioning and rollback instructions |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| 1. Trusted host code and nginx | Not started | Disposable VM | Verify template and sourced-file ownership |
| 2. Bootstrap and credentials | Blocked | Area 1; manifest handoff | Resolve reviewed-manifest read contract before `T2.5` |
| 3. De-root and curl | Not started | Area 1 for deployment docs | Can be implemented separately |
| 4. Cutover | Blocked | Areas 1-3 | Rehearse on test first |

## Definition Of Done

- [ ] `PH2-AC-1` has passing unsafe-path and compliant-control results (`V-1`), plus operator installation and root-script provenance (`V-4`, `V-5`).
- [ ] `PH2-AC-2` has passing cross-principal and cross-environment authentication results (`V-2`); no fallback/shared secret remains and rotation affects only one principal.
- [ ] `PH2-AC-3` has passing process-argv checks on both curl sites (`V-3`); the deploy-user flows run without an unnecessary root gate.
- [ ] The reviewed manifest is imported through the explicitly approved handoff; no deploy-writable script or template is executed, sourced or rendered as root.
- [ ] All planned files, regressions, documentation and rollback steps are complete; `V-1`-`V-5` results and per-domain migration dispositions are recorded, including any exceptions.
- [ ] No unresolved decision affects implementation or validation. If current code or environment conflicts with these verified inputs, stop and report the difference before changing design or scope.

## Risks And Open Questions

**Blocking: reviewed-manifest handoff (`D-1`).** The decision puts `authorization-manifest.yaml` at root:root 0600 in `/var/lib/shape-shifter/<domain>/` and says root bootstrap's remaining work is the two nginx-readable writes. But `container/scripts/authorization.sh::import_manifest` uses `< "$manifest_path"`, which a deployment-user-run process cannot read. Choose and record one contract before executing `T2.5`: a root-controlled one-time import that passes the reviewed bytes to the deployment user's Podman process without exposing the root-only file, or an explicitly reviewed deploy-readable copy with a verification step that prevents a substituted policy. Update `D-1` if the selected path changes its stated limit on root work; then mark this plan Validated. Do not use an unreadable path, weaken mode 0600, or quietly import a different file.

**Other concrete risks:** The existing vhost template also contains commented Basic-auth lines and a common upstream name; verify the effective rendered site, not just the template. A sudoers rule for `nginx -t` is separate from Phase 7's obligation to fail when that check is skipped. Secret handoff must not appear in terminal logs or unattended build output; use a controlled operator session for first-run provisioning. Historical shared passwords remain compromised for the purpose of rotation even after deletion from the new config.