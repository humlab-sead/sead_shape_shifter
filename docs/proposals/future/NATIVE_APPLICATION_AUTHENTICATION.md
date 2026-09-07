# Native Application Authentication

## Status

- Future proposal / not yet approved
- Related work: [Critical Security Mitigations](../MITIGATE_SECURITY_ISSUES/MITIGATE_SECURITY_ISSUES.md)
- Authorization system: [Centralized Authorization System](../MITIGATE_SECURITY_ISSUES/CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- Implemented authorization reference: [AUTHORIZATION.md](../../AUTHORIZATION.md)
- Goal: evaluate native application authentication after the current nginx identity and application authorization controls are complete

## Purpose

This document records native application authentication as possible future work. It keeps that longer-term decision separate from the immediate security changes.

No native authentication implementation is proposed or required by the current security phase.

## Current Phase Requirement

Phase 1 continues to use nginx as the authentication provider. Nginx must pass a verified identity to FastAPI, direct untrusted access to the backend must be blocked, and FastAPI must enforce authentication, resource authorization, and session ownership.

Native application authentication is not a dependency for completing those controls. Resource authorization must remain separate from the authentication mechanism so a future change does not require redesigning access rules.

## Candidate Scope

If this proposal is developed, it should cover:

1. the user and service-account identity model,
2. login, logout, session, and token behavior,
3. password, external identity-provider, or passkey support,
4. account recovery and identity administration,
5. multi-factor authentication requirements,
6. migration from nginx-provided identity,
7. audit logging, secret storage, rate limiting, and abuse protection,
8. deployment and rollback behavior while both authentication paths may exist.

## Out Of Scope For Now

This document does not define:

1. a selected authentication protocol or identity provider,
2. account or credential schemas,
3. API or frontend changes,
4. migration tasks,
5. implementation acceptance criteria.

## Questions To Answer Before Approval

1. What limitation of nginx authentication requires native authentication?
2. Which user, administrator, automation, and service-account flows must be supported?
3. Should the application store credentials or delegate authentication to an external identity provider?
4. How will existing nginx identities map to application identities without changing resource ownership?
5. How will sessions or tokens be revoked, rotated, audited, and protected?
6. Can nginx authentication remain available as a rollback path during migration?

## Trigger For Reopening This Topic

Revisit this proposal when the Phase 1 nginx identity and application authorization controls are complete and one or more of these conditions applies:

1. deployments need authentication without nginx,
2. required login, account, or service-account flows cannot be supported by the proxy contract,
3. a supported identity provider requires direct application integration,
4. operational experience shows that native authentication would reduce security or maintenance risk.

## Relationship To Phase 1

Phase 1 must remain independently releasable and must not wait for this proposal. It should preserve a replaceable authentication entry point while enforcing authorization against a stable application identity.

Future native authentication must preserve or strengthen the Phase 1 security properties: unauthenticated requests are rejected, resource access is authorized, sessions belong to an authenticated identity, and authentication events can be audited.

The [Centralized Authorization System](../MITIGATE_SECURITY_ISSUES/CENTRALIZED_AUTHORIZATION_SYSTEM.md) defines the stable principal contract, stored grants, resource ownership, policy decisions, and service enforcement that native authentication must preserve. Native authentication may change how a principal is established, but it must not replace or bypass those authorization controls. Any identity migration must map existing principal IDs explicitly without broadening access.
