# Security Hardening Follow-up — Phase Plan

Sequences the approved [Security Hardening Follow-up](SECURITY_HARDENING_FOLLOWUP.md) proposal against the September 2026 findings ledger. Ledger IDs (S1, A1, 16, 22a, ...) refer to `secrets/FINDINGS.md`, which is local and untracked; the proposal carries the approved scope. Related deployment record: [Deployment Verification Handoff](../done/CENTRALIZED_AUTHORIZATION_CUTOVER/DEPLOYMENT_VERIFICATION_HANDOFF.md).

## Summary

Deliver the remediation in seven phases ordered by the ledger's severity ranking. Phase 1 closes the CRITICAL request-path defects — anonymous file disclosure, environment-value reads, and out-of-root project writes — because they need no pending decision and are reachable today. The other CRITICAL item, root execution of deployment-user-writable bootstrap configuration (16), lands in phase 2, which is the earliest position the proposal allows: it fixes a named decision (who provisions root-owned configuration) ahead of any bootstrap rollout.

Later phases repair authorization mutation integrity and audit actors, remaining permission and state-consistency defects, response masking and output safety, build provenance and deployment paths, and finally the verification gates, so a green result again means the promised check ran.

## Problem

Unresolved ledger defects allow untrusted input to reach files, environment values, SQL, and project configuration through routes that appear protected; root bootstrap executes deployment-user-writable shell text; manifest application can leave a half-applied authorization store; and several deployment checks can exit 0 without exercising their stated condition. The plan must close these in dependency order without breaking namespaced locators, approved global role semantics, the documented log policy, or the approved PostgreSQL rotation exception.

## Scope

This plan covers implementation sequencing for all scoped ledger IDs (S1, A1, A1b, A2, B1/B1b/B1c/B2, G, D, 11-14, 16-21, 22a-22c, 23-27, 30, 31, 34, 35) and the migration of reviewed regression cases into maintained tests.

It does not include task-level file inventories, exact commands, or test names (phase task plans own those); reopening the fixed C1/C2 ingester gate or item 15; reclassifying the approved PostgreSQL rotation exception (32) or the documented global log-access policy (29 route classification); or release scheduling.

## Current Position

- The ledger was measured at `dev @ 54c05d0d`; the proposal records no `src/`, `backend/`, `frontend/`, or `container/` implementation change since. Spot checks at this checkout confirm the SPA catch-all joins the request path onto the dist directory without containment (`backend/app/main.py`), `GIT_REF` still defaults to `main` (`container/Makefile`), lifecycle audit rows still hardcode the actor `system` (`backend/app/authorization/repository.py`), and the verification bundle prints a warning and continues when `nginx -t` is skipped (`container/scripts/verify/complete_test_deployment_verification.sh`).
- PR #501 merged `dev` into `main` as `2.2.0`, so the pre-hardening half of item 11 is retired; the unpinned moving-default build remains.
- Items C1, C2, 15 are fixed and retained as guards; 33 is green; 32 is decided policy. The route-classification test exists but no CI workflow runs it (`.github/workflows/` holds only `release.yml`).
- The ledger's external test package lives in `secrets/` and is not a CI asset; its root-only tests must not run on a workstation.
- Fixed decisions carried from the proposal: preserve `namespace:project` locators by containing the mapped path, not banning colons; keep the global `project_maintainer` role as documented; do not require `read_logs` on log routes but do limit sensitive log content; constrain dangerous ingester inputs behind the existing `run_ingesters` gate.
- The two decisions gating phase 2 are recorded below (D-1, D-2). The phase 5 decisions (SQL read forms; masked-YAML edit contract) remain open.

## Recorded Decisions

### D-1 (2026-09-24): Configuration ownership and root-script placement

**Decision**

Root provisions and rotates the bootstrap configuration; the deployment account never reads it. Each environment gets its own root-owned directory, isolated from every other environment and from the deployment-writable checkout, and convenience sudo is removed rather than relocated.

- One directory per environment at `/var/lib/shape-shifter/<domain>/` (root:www-data, mode 0750; the parent is root:root 0755), keyed by domain to match the existing host accounts and `/data/<user>` layout. It holds that environment's `authorization.env` (root:root 0600), per-principal secret files under `secrets/` (root:root 0700/0600), the htpasswd file and `groups.d/` membership (root:www-data 0640, the only files nginx opens), and the reviewed manifest copy (root:root 0600; `authorization.sh` pipes it into the container at import time, so no daemon reads it in place). Deployment configuration (`backend.env`, `deployment.env`, `.pgpass`) stays in `~/config` owned by the deployment user, unchanged.
- The vhost template gains per-environment auth paths: `auth_basic_user_file /var/lib/shape-shifter/__DOMAIN__/htpasswd;` and a membership include from the same directory. The shared `map $remote_user $authz_groups` block must also become per-environment (a distinct variable name per vhost), because two rendered vhosts defining the same map variable fail `nginx -t`. This is required anyway once production and staging join the host.
- Bootstrap keeps its root run but reads configuration as data only: a strict `KEY=VALUE` reader replaces `source`, and a preflight asserts the file and every parent directory are root-owned and not group- or world-writable, checked on the resolved path so a symlink or directory replacement fails the check instead of bypassing it. Bootstrap takes the domain (hence the environment directory) as an argument instead of defaulting `CONFIG_DIR` below the checkout.
- Root's remaining work in bootstrap is the two www-data-readable writes (htpasswd file, groups file) inside the environment directory. The podman and authorization orchestration it currently performs through `sudo -u` moves to a deployment-user-run flow, which also removes the literal `TARGET_PATH` from the root path (head-start on item 23).
- Relocate to `/usr/local/sbin/shape-shifter/` through the release step: `bootstrap-authentication-and-authorization.sh` and `install_nginx_reverse_proxy.sh`. These are the only scripts whose text root must execute, and both are shared across environments and parameterized by domain.
- De-root rather than relocate: `deploy_single_environment.sh`, `install_systemd_service.sh`, `sync-to-deploy`, and `run_deployment_verification.sh` use root only to become the deployment user; they will require `sudo -u <deploy-user>` capability instead of a root gate. The verification bundle's only root need is `nginx -t`, covered by one sudoers entry.

**Why**

A script-by-script audit found the genuinely root-only operations are small and file-shaped (the htpasswd and groups writes, vhost install and reload, `nginx -t`, firewall listing); the other root gates exist for convenience. Root-owned directories inside the deployment user's tree do not qualify: the user owns the parent and can replace the directory. The required property is that no directory in an executed path is writable below root, which `/var/lib` and `/usr/local` satisfy without new install machinery beyond the release step. A single project-owned tree under `/var/lib` keeps each environment's credentials in one place — rotating or decommissioning an environment touches one directory — and keeps `/etc` free of project files. The host nginx runs unconfined (no AppArmor profile for nginx is installed), so it can read its auth files outside `/etc/nginx`; if a confinement profile is added later, it must cover these paths or the two files move under `/etc/nginx/` with the template updated.

**Consequence for the current host**

Today the htpasswd file (`/etc/nginx/htpasswd/shape-shifter`) and the groups include (`/etc/nginx/authz/groups.d/*.conf`) are shared by name across environments, and the wildcard include would merge every environment's memberships into any vhost that includes the directory. The per-environment layout fixes this before staging and production are onboarded; migrating `test-shape-shifter.sead.se` to it is part of phase 2.

**Residual risk accepted**

The deployment account still holds its own configuration and database credentials. This decision removes the guaranteed escalation from "operator follows the documented `sudo` runbook" to "attacker needs a real root exploit"; it does not reduce the deployment account's existing exposure.

### D-2 (2026-09-24): Per-principal secret migration and rotation

**Decision**

Each named principal gets an independent secret stored as a file at `/var/lib/shape-shifter/<domain>/secrets/<user>` (root:root, mode 0600), in preference to per-principal variables in the shared env file. The same principal may hold a different secret per environment; each environment rotates independently.

**Origin**: the shared `AUTH_PASSWORD` was an intentional cutover measure, not an oversight — one secret to distribute kept the authorization rollout low-friction. That window has closed: with per-principal grants and audit live, a shared secret now means any principal can authenticate as another and leave audit records under their name, and offboarding one account forces re-handoff of all of them. The per-principal files retire the measure while keeping handoff friction small (generate-and-print once; rotate one file per change).

- Bootstrap generates each secret on first run and prints it once for individual handoff; rotating one principal rewrites one file.
- A principal listed in `AUTH_USERS` with no secret file is a hard failure; no principal falls back to any shared value.
- The shared `AUTH_PASSWORD` is retired: bootstrap refuses to run while it is present in the root configuration, and migration is a fresh generation for every principal, because the shared value already circulated through handoffs. Deterministic transforms of it and in-script literals are rejected the same way.
- `verify_credential_rotation.sh` gains per-principal checks; `authorization.env.example` and `container/DEPLOYMENT.md` document the new layout.

## Phase Plan

### Phase 1: Contain request-controlled file and environment disclosure

**Goal**

Close the CRITICAL request-path defects so untrusted route and project inputs can no longer read or write outside approved roots or expose environment values.

**Focus**

- SPA catch-all containment (S1)
- Environment substitution restricted to an approved variable list at the configuration-mapping boundary, for both request-supplied and stored project YAML (A1, A1b)
- Unknown entity mapper types rejected as unsupported instead of passing `options.filename` through to file loaders (A2)
- Project-name resolution: containment of the mapped path under `PROJECTS_DIR` against traversal, absolute names, and aliasing another project's file (B1, B1b, B1c, B2)
- Isolated reproduction environment (disposable container or VM) for the ledger's root-only tests, required before any later phase executes them

**Depends On**

- No pending decision; fixed colon-locator constraint from the proposal

**Outputs**

- Contained project and file resolution usable by every later phase
- Disposable reproduction environment for bootstrap and deployment-script tests (phases 2, 6, 7)

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) The SPA route serves only files under the frontend dist directory; absolute-path and `..` arms are rejected.
- `PH1-AC-2` (from `P-AC-1`) `${VAR}` expansion in request-supplied and stored entity config reaches only approved variables; unapproved names neither expand nor return values in preview rows.
- `PH1-AC-3` (from `P-AC-1`) An entity type missing from the mapper factory fails as unsupported before any file read.
- `PH1-AC-4` (from `P-AC-1`) Project creation cannot write outside `PROJECTS_DIR` via traversal, an absolute name, or a colon locator aliasing another project's file, and `namespace:project` locators continue to work.
- `PH1-AC-5` (from `P-AC-8`) The ledger's root-only bootstrap tests run in the disposable environment with the host verified untouched.

**Validation Milestones**

- `VM-1.1` Direct API tests assert rejection and the filesystem effect, not only status codes (covers `PH1-AC-1`-`PH1-AC-4`).
- `VM-1.2` Namespaced-locator parity check against existing authorized workflows (covers `PH1-AC-4`).
- `VM-1.3` Reproduction-environment run reports host paths unchanged by mode, owner, and mtime (covers `PH1-AC-5`).

**Task-Plan Handoff**

- Source: `P-AC-1`, ledger section 1. Fixed: contain the mapped path at the service boundary; keep colon locators; environment substitution resolves only at the mapper boundary per repository convention. Blocking questions: none.

**Readiness**

Ready for a task plan

### Phase 2: Remove root execution of deployment-user-writable configuration and shared credentials

**Goal**

Make the bootstrap path root-safe and give every named principal an independent credential, closing the remaining CRITICAL item (16) and its HIGH companion (27).

**Focus**

- Bootstrap no longer sources deployment-user-writable shell text as root: data-only configuration or root-owned credentials with ownership and path checks that survive symlink or directory replacement (16)
- Per-principal secrets replacing the single `AUTH_PASSWORD`, with a migration and rotation path for the existing shared secret (27)
- Administrator passwords removed from child-process argv at the two cited sites (26)

**Depends On**

- `D-1` and `D-2` recorded above (configuration ownership; per-principal secret migration)
- Phase 1 output: disposable environment for root-only tests

**Outputs**

- Root-controlled credential provisioning usable by the deployment-path repairs in phase 6
- Per-principal identities that make audit actors meaningful in phase 3

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-4`) Bootstrap refuses to execute configuration not owned per the decided root-ownership rule, fails with a clear message, and the documented provisioning path works end to end.
- `PH2-AC-2` (from `P-AC-4`) Each named principal authenticates with an independent secret; the shared value is retired, and no principal silently falls back to it.
- `PH2-AC-3` (from `P-AC-4`) No deployment flow passes an administrator password in a child process's arguments.

**Validation Milestones**

- `VM-2.1` End-to-end bootstrap runs in the disposable environment, including a control proving a compliant file is still executed (covers `PH2-AC-1`).
- `VM-2.2` Impersonation check: one principal's secret cannot authenticate as another through the nginx `$remote_user` path (covers `PH2-AC-2`).
- `VM-2.3` Process-argument scan during the cleanup flow finds no password (covers `PH2-AC-3`).

**Task-Plan Handoff**

- Source: `P-AC-4`, ledger items 16, 27, 26. Fixed: never source user-writable shell text as root; reject deterministic transforms of the shared secret and in-script literals. Decisions `D-1` and `D-2` fix the layout (per-environment `/var/lib/shape-shifter/<domain>/`, data-only reader with ownership preflight, two scripts relocated, four scripts de-rooted, per-principal secret files with generate-and-print migration). Blocking questions: none.

**Readiness**

Ready for a task plan

### Phase 3: Make authorization changes recoverable and audits attributable

**Goal**

Ensure an invalid or failed manifest changes nothing, imported and exported inventories stay owner-only, and every lifecycle mutation names its authenticated actor.

**Focus**

- Full-manifest validation, including top-level keys and role names, before any write (22b, 22c)
- One-transaction application or a demonstrated restore of the previous store on any failure, with a backup taken before cutover (22a)
- Owner-only, unpredictable staging and export files with cleanup that runs on failure (18, 24)
- Authenticated actor required for project and shared-data-source lifecycle mutations; unthreaded calls raise instead of recording `system` (30)

**Depends On**

- Phase 2 output: per-principal identities so actor attribution is meaningful

**Outputs**

- Recoverable manifest application for the cutover and any later import
- Trustworthy lifecycle audit records for phase 7's verification checks

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-5`) A manifest with an unknown top-level key or a role no policy rule knows is rejected before any write, with nonzero exit.
- `PH3-AC-2` (from `P-AC-5`) A mid-apply failure observed from a separate database connection leaves the prior store intact or restores it.
- `PH3-AC-3` (from `P-AC-5`) Exported and staged manifests are owner-only and unpredictable, and a failed run leaves no residue; a re-export does not silently downgrade an existing file's mode.
- `PH3-AC-4` (from `P-AC-4`) Project and shared-data-source lifecycle rows name the authenticated principal; no write path reaches the `system` default; a forged identity header cannot name an actor the application did not authenticate.

**Validation Milestones**

- `VM-3.1` Failed-apply test against a second live connection proves store preservation (covers `PH3-AC-1`-`PH3-AC-2`).
- `VM-3.2` Filesystem checks on export/staging paths cover mode, name unpredictability, and failure residue (covers `PH3-AC-3`).
- `VM-3.3` Four audit-actor arms: project lifecycle, shared-source lifecycle, forged header, structural no-default check (covers `PH3-AC-4`).

**Task-Plan Handoff**

- Source: `P-AC-4`, `P-AC-5`, ledger items 22a-22c, 18, 24, 30. Fixed: transaction-or-demonstrated-restore, both acceptable; backup before cutover is mandatory. Known limit to carry: with proxy auth on, the header is the app's identity, so nginx remains the control there. Blocking questions: none.

**Readiness**

Ready for a task plan

### Phase 4: Close remaining permission and state-consistency defects

**Goal**

Make preview, restore, shared-source authorization, ingester inputs, and global logs enforce their intended permissions and state.

**Focus**

- Authorize the shared source named in the request body, not the locator, keeping fail-closed behavior (D)
- Invalidate shared application state after backup restore so cache-backed routes serve restored content (G)
- Constrain ingester source paths, output folders, and destination database selection independently of the enforced `run_ingesters` action
- Limit exception details and diagnostic logging so global logs cannot expose credentials, configuration values, or another tenant's request data

**Depends On**

- Phase 1 output: contained file resolution reused by shared-source and ingester path checks

**Outputs**

- Enforced request-level permissions feeding the verification checks in phase 7

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-2`) A shared-source request is authorized against the body's source reference; a mismatch fails closed.
- `PH4-AC-2` (from `P-AC-2`) After restore, every cache-backed route serves the restored content without a per-route reload.
- `PH4-AC-3` (from `P-AC-2`, `P-AC-3`) An authorized ingester run cannot read arbitrary sources, remove paths outside its output root, or target a database outside the approved set.
- `PH4-AC-4` (from `P-AC-2`) Log downloads and error responses for an authenticated reader of one project contain no credentials, absolute-path configuration values, or other tenants' request data.

**Validation Milestones**

- `VM-4.1` API tests with two role-scoped principals prove authorization follows the body reference and isolation holds in log content (covers `PH4-AC-1`, `PH4-AC-4`).
- `VM-4.2` Restore-then-read sequence across both compared routes (covers `PH4-AC-2`).
- `VM-4.3` Ingester input-constraint cases for source, output, and database selection (covers `PH4-AC-3`).

**Task-Plan Handoff**

- Source: `P-AC-2`, `P-AC-3`, ledger items D, G, C1 residual behavior, 29 content. Fixed: the `run_ingesters` gate is not reopened; the log route's role classification is not changed. Blocking questions: none.

**Readiness**

Ready for a task plan

### Phase 5: Enforce output safety, response masking, and the SQL read allowlist

**Goal**

Return no secret to an unauthorized reader, remove unsafe frontend output paths, and admit only explicitly supported read queries.

**Focus**

- Consistent masking of stored connection secrets across project, data-source, raw-YAML, and update-echo responses (14a)
- Remove unsafe HTML rendering, guard CSV exports against formula injection, supply CSP and production API configuration on every supported frontend build path (14b)
- Replace the SQL denylist posture with an explicit read-operation allowlist, backed by least-privilege database credentials (13)

**Depends On**

- Required decision: the privileged editing contract for masked raw-YAML (round-trip expectations)
- Required decision: supported SQL read forms, established with data owners

**Outputs**

- Stable masked response shapes and a validated SQL policy for the release checks in phase 7

**Acceptance Criteria**

- `PH5-AC-1` (from `P-AC-2`) A credential placed in project YAML does not return from the update echo, project read, data-source list, or raw-YAML routes.
- `PH5-AC-2` (from `P-AC-8`) No shipped frontend path renders untrusted HTML, CSV exports neutralize `=+-@` payloads, a CSP is present, and every supported build path carries production API configuration.
- `PH5-AC-3` (from `P-AC-3`) File-access and write-capable SQL forms (`pg_read_file`, `lo_import`, `dblink`, `SELECT INTO`, and their relatives) fail before execution under the allowlist, and the database role's privileges are independently confirmed as the second constraint.

**Validation Milestones**

- `VM-5.1` Round-trip masking tests across all four response routes (covers `PH5-AC-1`).
- `VM-5.2` Browser and export checks across each frontend build path (covers `PH5-AC-2`).
- `VM-5.3` Allowlist cases run against a live driver call boundary plus a privilege probe on the database role (covers `PH5-AC-3`).

**Task-Plan Handoff**

- Source: `P-AC-2`, `P-AC-3`, `P-AC-8`, ledger items 14a, 14b, 13. Fixed: a forbidden-name list is explicitly insufficient; database privileges remain necessary after parser enforcement. Blocking questions: masked-YAML edit contract; supported SQL read forms. Do not change those API response shapes before the contract is recorded.

**Readiness**

Requires a named decision (masked-YAML edit contract; supported SQL read forms)

### Phase 6: Pin build provenance and repair deployment paths

**Goal**

Make a fresh host build use reviewed, verifiable artifacts, and make documented configuration, upgrade, and build paths work or fail clearly without losing credentials.

**Focus**

- Pin the release source ref replacing the moving `main` default (11, remaining half)
- Version- and digest-pin the external JAR downloads staged into the build context (12)
- Detect the retired backend credential file during upgrade instead of stranding it (17)
- Align deployment configuration path resolution with the documented layout (19, 21)
- Reject missing compose mount inputs before container start (20)
- Preserve the deployment user's executable search path instead of replacing it with a literal list (23)

**Depends On**

- Phase 2 output: bootstrap and credential provisioning changes land in the same scripts, so path and PATH repairs follow them
- Phase 1 output: disposable environment for deployment-script checks

**Outputs**

- A buildable, pinned release source for the phase 7 verification bundle

**Acceptance Criteria**

- `PH6-AC-1` (from `P-AC-6`) A default fresh build resolves to a pinned reviewed ref, and external JAR fetches verify against a recorded version and digest.
- `PH6-AC-2` (from `P-AC-6`) The documented invocation works from the documented layout; an upgrade reports, migrates, or clearly fails on the retired credential file — never strands it silently; compose refuses missing mount inputs before start; the deployment user keeps its own PATH.

**Validation Milestones**

- `VM-6.1` Build-provenance check in the disposable environment confirms the ref and digests actually used (covers `PH6-AC-1`).
- `VM-6.2` Upgrade-path matrix with outcomes classified migrated / deleted / reported / stranded, where only stranded fails (covers `PH6-AC-2`).

**Task-Plan Handoff**

- Source: `P-AC-6`, ledger items 11, 12, 17, 19, 20, 21, 23. Fixed: item 11 is reduced to the moving-default half after the `2.2.0` merge. Constraint: the same PATH literal exists in the verification bundle script and must be fixed with the bootstrap site. Blocking questions: none.

**Readiness**

Ready for a task plan

### Phase 7: Make verification gates honest and retire the ledger

**Goal**

Ensure every automated gate fails when its promised check did not run, and move the ledger's regression coverage into maintained tests with a recorded disposition per scoped ID.

**Focus**

- Fail the bundle when `nginx -t` did not execute (25)
- Reject any non-loopback listener for the protected backend port by allowlisting listening addresses, letting an un-parsed ruleset decide the outcome (31)
- Return a distinct non-success when authenticated access verified zero isolation directions (35)
- Run the route-classification test in a CI job triggered for relevant changes (34)
- Review and move useful ledger regression cases into maintained isolated tests; retain manual exceptions as named exceptions with a recorded disposition, never as successful automated checks

**Depends On**

- Phases 1-6 outputs: the gates in this phase certify the fixes made in the earlier phases
- Required decision (carried, not blocking this phase's design): disposition wording for the PostgreSQL rotation exception (32) and the log-policy citation (29) as named exceptions

**Outputs**

- A verification bundle whose exit status can be trusted for the release disposition

**Acceptance Criteria**

- `PH7-AC-1` (from `P-AC-7`) The bundle exits nonzero when `nginx -t` was skipped.
- `PH7-AC-2` (from `P-AC-7`) The firewall check fails for a backend listening on a LAN or bridge address even when loopback is also bound, across all three arms.
- `PH7-AC-3` (from `P-AC-7`) Authenticated-access verification exits nonzero when no isolation direction was checked, distinguishable from both pass and fail.
- `PH7-AC-4` (from `P-AC-7`) A CI job executes the route-classification test on changes that could alter route authentication.
- `PH7-AC-5` (from `P-AC-8`) Every scoped ledger ID has a maintained regression test or a named exception with a recorded disposition, and no root-only case runs outside the disposable environment.

**Validation Milestones**

- `VM-7.1` Exit-status arms for each gate, each with a control so rewording alone cannot pass (covers `PH7-AC-1`-`PH7-AC-4`).
- `VM-7.2` Disposition review: mapped ledger ID to test or exception, re-running focused tests plus broader backend and frontend checks before recording the release disposition (covers `PH7-AC-5`).

**Task-Plan Handoff**

- Source: `P-AC-7`, `P-AC-8`, ledger items 25, 31, 34, 35, section 5-6 limits. Fixed: ruleset inspection stays a separate explicit gate; the dropped role-lookup arm stands as a positive control. Constraint: the ledger harness rewrites positional arguments only — migrated tests must not inherit redirection or `sed -i` gaps. Blocking questions: none.

**Readiness**

Ready for a task plan

## Cross-Phase Rules

- Reproduce root-only and deployment-script tests only in the disposable environment from phase 1; never on a workstation.
- Contain the mapped path at the service boundary; never ban colons outright — `namespace:project` locators are a shipped convention.
- The `run_ingesters` gate stays as fixed; constrain inputs behind it rather than reopening C1/C2.
- Keep the documented global log-access policy and the approved PostgreSQL rotation exception; address their content and visibility, not their classification.
- A green deployment record is not evidence of a code fix; each phase validates its own changes.
- Resolve a blocking decision and record it in this plan before starting the phase it gates.
- Keep documentation aligned with each shipped fix so the next ledger pass measures code, not prose.

## Validation Strategy

- Phase 1 and 3-5: unit and direct API tests asserting filesystem and database effects, not status codes or source-text patterns; role-scoped principals for isolation claims; a separate database connection to prove failed manifest applications preserve the prior store.
- Phase 2 and 6: end-to-end script runs inside the disposable environment, each with a control proving the shipped code path executed; upgrade outcomes classified migrated / deleted / reported / stranded.
- Phase 5 and 7: frontend browser and CSV-export cases; build-provenance checks; exit-status arms with controls for every verification gate.
- Phase 7 closeout: re-run focused tests for each ledger ID, then broader backend and frontend suites, before recording a release disposition.
- Exact commands, test files, fixtures, and assertions belong in each phase task plan.

## Final Recommendation

Start the phase 1 task plan immediately — it carries six of the seven CRITICAL items and needs no decision. The phase 2 gate is now open: `D-1` and `D-2` are recorded, so its task plan can start while the remaining decision (SQL read forms with the masked-YAML edit contract) runs in parallel so phase 5 is not idle. Hold phase 7 last so its gates certify the accumulated fixes, and do not close any ledger ID without a maintained regression test or a named exception.
