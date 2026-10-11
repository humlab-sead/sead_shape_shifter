# SEAD Runtime Verification Handoff

## Status

- Proposed requirements for handover to SEAD operations
- Related proposal: [Container Setup Simplification](./CONTAINER_SETUP_SIMPLIFICATION.md)
- Goal: Define the runtime checks operations must provide without prescribing their tools or implementation

## Purpose

Shape Shifter should not own checks for the wider SEAD runtime, such as credential rotation, host log review, database account review, and network exposure. SEAD operations should implement these checks with its established tools and procedures.

This handoff states the outcomes those checks must provide. It does not select a repository, product, schedule, or runbook format. The exact operations owner and authoritative location remain to be agreed. Do not keep duplicate active copies of operational checks in Shape Shifter and an operations toolkit.

Application behavior tests and release validation remain with Shape Shifter. Operations may add deployment checks where they verify runtime configuration or integration with the SEAD environment.

## Requirements

| ID | Area | Priority | Required outcome |
|---|---|---|---|
| `OPS-REQ-1` | Database accounts | Must | Each database account has a documented purpose and only the privileges needed for that purpose. An account used only for reporting or read access must be effectively read-only: it cannot write, create objects, administer roles or databases, own relevant objects, or gain extra privileges through role membership or `PUBLIC`. |
| `OPS-REQ-2` | Application database access | Must | Do not assume every application database account can be read-only. If an application function requires writes, document the account and its required operations, grant only those privileges, and keep it separate from read-only reporting access where practical. |
| `OPS-REQ-3` | Authorization data | Must | Protect the authorization database and its backups from access by project users and unrelated services. Limit file access to the deployment identity and required administrators. Report permission or ownership changes that weaken this protection. |
| `OPS-REQ-4` | Account and grant review | Must | Maintain an inventory of deployment and application principals, their roles, project or resource grants, purpose, and owner. Identify stale, excessive, or ownerless access and provide a controlled removal or review process. |
| `OPS-REQ-5` | Credential lifecycle | Must | Maintain a credential inventory by name and owner, including application, proxy, database, and external-service credentials. Apply the rotation and exception process set by SEAD policy; record status and approved exceptions without recording credential values in reports. |
| `OPS-REQ-6` | Log review | Must | Scan relevant application, proxy, database, and host logs for exposed credentials, connection strings, sensitive SQL, and unintended filesystem or environment details. Review matches and record findings or documented false positives. Reports and retained evidence must not reproduce secret values. |
| `OPS-REQ-7` | Network exposure | Must | Confirm that the application backend is reachable only through its intended local interface and approved proxy path. Check host firewall policy and verify external reachability from a separate host where required. Report unexpected listeners or paths that bypass the proxy. |
| `OPS-REQ-8` | Proxy identity | Must | Confirm that the proxy authenticates requests as configured, forwards only the verified identity, and does not trust an identity header supplied directly by an untrusted client. Requests without valid authentication must not reach protected application behavior. |
| `OPS-REQ-9` | Application authorization | Must | Verify that an authenticated principal can perform actions allowed by its grants and is denied actions and resources outside those grants. Include project isolation checks for distinct principals. Use disposable test identities and resources; do not modify real user grants or project data as part of a routine check. |
| `OPS-REQ-10` | Test-resource cleanup | Must | If a deployment check creates temporary principals, grants, or projects, scope them to that check, make cleanup reliable on success and failure, and report cleanup failures. Destructive cleanup of non-test resources must be a separate, explicitly approved operation. |
| `OPS-REQ-11` | Container configuration | Must | Confirm the deployed image and runtime settings match the approved deployment: intended network binding, data mounts, service identity, and secret handling. Do not expose secret values in check output. |
| `OPS-REQ-12` | Health and recovery | Must | Provide a way to confirm service health after deployment and recovery. A rollback procedure must identify the image version or digest and required data backups, preserve authorization data consistently, and verify service health after restoration. |
| `OPS-REQ-13` | Safe defaults | Must | Routine verification must not change firewall rules, service state, images, configuration, database grants, authorization records, or project data. Any check that changes state must be a separate, explicit operation with a stated scope, confirmation where impact warrants it, and a recovery path. |
| `OPS-REQ-14` | Results and ownership | Must | Record the check date, target environment, application/image version where relevant, result, operator or automation identity, and follow-up owner. Store evidence in the approved operations record. Exclude passwords, tokens, connection strings, and other secret values. |
| `OPS-REQ-15` | Check cadence | Should | Define when each check runs—for example after deployment, during access review, or under the SEAD security schedule. Use the applicable SEAD policy; this handoff does not prescribe intervals. |
| `OPS-REQ-16` | Tool choice | Should | Reuse existing SEAD monitoring, security, database, and deployment tooling when it can meet these outcomes. Add a script only when it provides a check not already covered or removes meaningful manual work; avoid wrappers that only dispatch to other checks. |

## Ownership Boundary

- Shape Shifter owns application authorization policy and automated tests for its endpoint and service behavior.
- Shape Shifter release automation owns source and archive release-policy checks.
- The host release manager must validate downloaded archives using trusted checks, not a verifier supplied by the candidate archive.
- SEAD operations owns deployed checks for identity integration, application-user grants, database accounts, secrets, logs, network exposure, runtime configuration, and recovery.
- Operations chooses the tools, schedule, alerting, evidence store, and escalation path, subject to the requirements above.

## Implementation Acceptance

The handover is complete when:

- An operations-owned source or service is identified as the authoritative home for runtime checks.
- Each `Must` requirement has a named check or documented operational procedure and a responsible owner.
- Routine checks are non-mutating; state-changing procedures are separately invoked and documented.
- Operators can run the supported checks without relying on files shipped inside a replaceable Shape Shifter release.
- Active Shape Shifter documentation points operators to the authoritative operations guidance, and no duplicate operational checker remains active in the application release.

Until the operations owner and authoritative home are agreed, the handover is a proposal, not an implemented operating procedure.
