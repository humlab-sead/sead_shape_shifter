# Security Hardening Follow-up

## Status

- Proposed change request
- Scope: unresolved application, authorization, deployment, and verification defects reported in the local, untracked `secrets/FINDINGS.md` ledger.
- Goal: prevent unauthorized reads and writes, preserve authorization integrity, and make deployment checks report what they actually verified.

## Summary

Approve a coordinated remediation of the unresolved defects in the September 2026 findings ledger. Start with root-executed configuration and request-controlled filesystem access, then repair authorization mutations and deployment defaults, and finally make verification gates fail when their promised checks did not run. The later cutover documentation records successful checks for a particular deployed image; it does not change the underlying implementation.

## Problem

Untrusted input reaches files, environment values, SQL, and project configuration through routes that appear to be protected by authentication or resource grants. Project locators can also escape their storage root or alias another project's file. Separately, root bootstrap executes a file writable by the deployment account, authorization manifest application can leave partial changes, and shared tester credentials make audit identities unreliable. Several deployment checks can return success without exercising their stated condition. These defects can undermine the release checks even when the recorded deployment passed them.

## Scope

- Close unresolved ledger items S1, A1, A1b, A2, B1/B1b/B1c/B2, G, D, 11-14, 16-21, 22a-22c, 23-27, 30, 31, 34, and 35, subject to the policy decisions below. The existing ingester action gate (C1/C2) is not reopened; constrain dangerous ingester inputs behind that gate. Item 11 is reduced by the `2.2.0` merge to `main`: only the unpinned moving-default build remains, not the pre-hardening image.
- Preserve legitimate namespaced (`namespace:project`) project locators and existing authorized workflows.
- Keep the separately approved PostgreSQL credential-rotation and host-log exceptions visible in deployment records, not reclassified as implementation fixes.

## Non-Goals

- Rework the intentional global `project_maintainer` role or revoke its existing grants.
- Require `read_logs` on log routes without a new policy decision; global authenticated log access is documented policy. This proposal does not treat ledger item 29's route classification as a confirmed defect, but does address sensitive log content.
- Implement manifest reconciliation as revocation, or require exports to include child resources. Those are different contracts.
- Count the fixed C1/C2 and 15, or the passing 33 guard, as outstanding work. Item 32 is an approved rotation exception, not a pending code fix.

## Current Behavior

No `src/`, `backend/`, `frontend/`, or `container/` implementation files changed between the ledger's `54c05d0d` reference and this proposal's checkout. Spot checks confirm that the SPA route returns `frontend_dist / full_path` without containment, bootstrap sources `CONFIG_DIR/authorization.env` before its root check, every `AUTH_USERS` entry receives `AUTH_PASSWORD`, `container/Makefile` defaults `GIT_REF` to `main`, and lifecycle audit records use the actor `system`. The SQL validator rejects known operation keywords but does not restrict read queries to approved operations. The other listed defects are reported by the ledger; their exact reproduction, severity, and fixes must be verified against current code during planning. The ledger's external test package is local to `secrets/` and is not a tracked CI asset.

PR #501 merged `dev` into `main` as `2.2.0`, so `main` now carries `proxy_auth.py`, `backend/app/authorization/`, and `src/sql_policy.py`. This retires the pre-hardening half of ledger item 11: a `GIT_REF=main` build no longer produces the authorization-less application the ledger described. The remaining concern is that a moving default still tracks whatever `main` holds at build time, so a fresh host build is not pinned to a reviewed release. The merge did not change any other scoped defect.

The completed [deployment handoff](../done/CENTRALIZED_AUTHORIZATION_CUTOVER/DEPLOYMENT_VERIFICATION_HANDOFF.md) records a `dev` image, a loopback-only backend, an approved PostgreSQL rotation exception, and one-direction access checks. These are deployment-specific results, not fixes for the moving `main` build default or for verification-script false positives.

## Proposed Design

### Protect request-controlled data and files

Resolve project names and all mapped file paths under their designated roots after mapping; reject traversal, absolute names, symlink escapes, and collisions with existing project files before any write. Apply the same containment rule to SPA files. Treat unknown entity mapper types as unsupported, not as a pass-through to file loaders. Restrict environment substitution to explicit, approved variables at the configuration-mapping boundary for both preview requests and stored YAML. Authorize the shared source named in the request body, not an unrelated locator, while preserving fail-closed behavior. Invalidate shared application state after backup restore.

Mask stored connection secrets consistently across project, data-source, and raw-YAML responses, including update echoes. Remove unsafe HTML rendering paths, guard CSV exports against formulas, and supply a CSP and production API configuration for every supported frontend build path. Use a SQL execution policy that permits only explicitly supported read operations, backed by least-privilege database credentials; a short list of forbidden function names is insufficient. Constrain ingester source and output paths and destination database selection independently of the now-enforced `run_ingesters` action.
Limit exception details and diagnostic logging so global logs cannot expose credentials, configuration values, or sensitive request data to authenticated readers.

### Make authorization and deployment changes recoverable

Do not source deployment-user-writable shell text as root. Use data-only configuration or provision root-controlled credentials with ownership and path checks that cannot be bypassed by symlinks or directory replacement. Assign independent secrets to named principals and define how to migrate and rotate the existing shared secret. Validate the entire manifest, including top-level keys and role names, before applying it. Apply it as one transaction or use a demonstrated recovery procedure that restores the previous store on any failure; take a backup before cutover.

Write exported and staged manifests to owner-only, unpredictable files with cleanup that runs on failure. Require the authenticated actor for project and shared-source lifecycle mutations, rather than silently writing `system`. Pin the release source and external JAR downloads to reviewed, verifiable artifacts. Make deployment configuration paths resolve from documented locations, preserve the deployment user's executable search path, detect retired credential files during upgrades, and reject missing compose mount inputs before starting a container. Avoid passing administrator passwords in process arguments.

### Make verification results trustworthy

Fail the bundle if `nginx -t` did not execute. Reject every non-loopback listener for the protected backend port in the automated firewall check; keep ruleset inspection as an explicit separate gate where required. Return a distinct non-success result when authenticated access checked no isolation direction. Run the route-classification test in a CI job triggered for relevant changes. Retain manual exceptions as named exceptions with owners and a recorded disposition, never as successful automated checks.

## Risks And Tradeoffs

- Replacing shared passwords and tightening project-path validation require coordinated deployment and existing-project compatibility checks; rejecting `:` outright would break supported locators.
- Masked raw-YAML output may break clients that expect a round-trip editing payload. Define a privileged editing workflow without exposing secrets to readers before changing response shapes.
- A strict SQL allowlist may exclude legitimate queries; establish supported query forms with data owners before rollout. Database permissions remain necessary even after parser enforcement.
- Root-only configuration may conflict with a deployment account that currently writes `~/config`. Decide who provisions and rotates it before changing the bootstrap script.
- Do not execute the ledger's root-only script tests on a workstation: its own harness documents paths that escape its stubs. Reproduce those tests only in an isolated disposable environment.

## Testing And Validation

Move useful regression cases from the local ledger into maintained tests after reviewing their claims and isolation. Test direct API behavior and filesystem effects, not only status codes or source-text patterns. Use a disposable container or VM for bootstrap and deployment checks; use a separate database connection to prove failed manifest applications preserve the prior store. Test path normalization, symlinks, absolute names, namespaced aliases, unknown entity types, stored versus request-supplied variables, role-scoped data leaks, masked responses, supported SQL, and honest verification exit codes. Include frontend browser and CSV-export cases, build provenance, and the documented upgrade path. Re-run focused tests and broader backend/frontend checks before recording a release disposition.

## Acceptance Criteria

- `P-AC-1` Untrusted route and project inputs cannot read or write outside approved roots, expose environment values, or alias another project's file; existing namespaced locators continue to work.
- `P-AC-2` Preview, restore, shared-source authorization, ingester execution, project responses, and global logs enforce their intended permissions and state consistency, with no secret returned to an unauthorized reader.
- `P-AC-3` Supported read queries run; unsafe SQL forms and unauthorized database/file access fail before execution, with database privileges independently constrained.
- `P-AC-4` Root bootstrap cannot execute deployment-user-writable code; each principal has an independent credential, and authenticated actors appear in every lifecycle audit record.
- `P-AC-5` Invalid manifests change nothing, failed applications preserve or restore the previous store, and imported/exported inventory remains owner-only with no failure residue.
- `P-AC-6` A fresh build uses a reviewed source ref and verified external dependencies; documented configuration, upgrade, and build paths either work or fail clearly without losing credentials.
- `P-AC-7` Verification exits nonzero for skipped mandatory checks, non-loopback backend listeners, and unverified isolation; route-classification runs automatically for relevant changes.
- `P-AC-8` HTML, CSV, CSP, and frontend production configuration checks cover every supported build route; local-only regression tests are reviewed and moved into maintainable isolated coverage.

## Planning Handoff

A phase plan should first decide the deployment-account/root configuration ownership, per-principal secret migration, supported SQL read forms, and the privileged edit contract for masked YAML. Preserve `namespace:project`, approved global role semantics, the documented log policy, and the approved PostgreSQL rotation exception. Plan an isolated reproduction of root-only tests before implementation, and require regression results plus a recorded disposition for every scoped ledger ID. Resolve deployment ownership and credential migration before bootstrap rollout; resolve SQL and raw-YAML contracts before changing those APIs.

## Final Recommendation

Approve this remediation scope and create a phase plan that separates immediate containment from credential and manifest migration, then verification and release checks. Do not use the earlier green deployment record as a substitute for fixing and testing the underlying code.