# Shape Shifter Documentation

This directory contains the active guides, references, deployment runbooks, and proposal records for Shape Shifter.

## Main Guides

| Document | Purpose |
|---|---|
| [USER_GUIDE.md](USER_GUIDE.md) | Use the Project Editor to create projects, manage entities, validate data, and export results. |
| [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) | YAML configuration reference for entities, data sources, transformations, relationships, directives, and validation. |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Local setup, development workflow, architecture pointers, testing, and contribution practices. |
| [TESTING.md](TESTING.md) | Test strategy, test levels, fixtures, browser checks, and manual verification. |
| [OPERATIONS.md](OPERATIONS.md) | Runtime configuration, deployment, health checks, backups, recovery, and rollback. |

## Architecture And Requirements

| Document | Purpose |
|---|---|
| [DESIGN.md](DESIGN.md) | System architecture, data flow, API boundaries, security, and design decisions. |
| [DIAGRAMS.md](DIAGRAMS.md) | System, workflow, sequence, state, deployment, and registry diagrams. |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Functional and non-functional requirements, personas, use cases, constraints, and success criteria. |
| [GLOSSARY.md](GLOSSARY.md) | Definitions for Shape Shifter terms used across import, transformation, validation, and export. |
| [SQL_SAFETY_POLICY.md](SQL_SAFETY_POLICY.md) | Rules for SQL execution, query validation, and database safety. |

## Security And Data Contracts

| Document | Purpose |
|---|---|
| [AUTHORIZATION.md](AUTHORIZATION.md) | Authorization principals, resources, roles, actions, denial behavior, and enforcement coverage. |
| [AUTHORIZATION_ROUTE_INVENTORY.md](AUTHORIZATION_ROUTE_INVENTORY.md) | API route inventory and authorization classification status. |
| [DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](DATA_PROVIDER_SUBMISSION_LIFECYCLE.md) | Lifecycle policy for provider-submitted data changes and version history. |
| [TARGET_MODEL_GUIDE.md](TARGET_MODEL_GUIDE.md) | Target model concepts, authoring guidance, and validation workflow. |
| [TARGET_MODEL_SCHEMA_REFERENCE.md](TARGET_MODEL_SCHEMA_REFERENCE.md) | Generated target-model schema reference. |

## Deployment

| Document | Purpose |
|---|---|
| [container/README.md](../container/README.md) | Supported Podman deployment quick start, configuration, lifecycle commands, and diagnostics. |
| [container/DEPLOYMENT.md](../container/DEPLOYMENT.md) | Deployment-host setup, environment deployment, reverse proxy, systemd, and multi-environment procedures. |

## Proposals

Proposal documents are grouped by status:

| Location | Contents |
|---|---|
| [proposals/](proposals/) | Active proposals and current implementation decisions. |
| [proposals/future/](proposals/future/) | Deferred proposals kept for later work. |
| [proposals/done/](proposals/done/) | Completed or decided proposals and archived records. |
| [proposals/onhold/](proposals/onhold/) | Paused proposal work. |

Current proposal entry points:

| Document | Purpose |
|---|---|
| [BUGSCEP_PILOT_PROJECT.md](proposals/BUGSCEP_PILOT_PROJECT.md) | BugsCEP pilot status and next implementation slices. |
| [BRANCH_SCOPED_CONSUMERS_FOR_MIXED_BRANCH_PARENTS.md](proposals/BRANCH_SCOPED_CONSUMERS_FOR_MIXED_BRANCH_PARENTS.md) | Branch-scoped consumption for mixed-branch parent rows. |
| [RECONCILIATION_FUTURE_IMPROVEMENTS.md](proposals/RECONCILIATION_FUTURE_IMPROVEMENTS.md) | Future reconciliation improvements. |
| [RULESYNC_AGENT_INSTRUCTIONS_UNIFICATION.md](proposals/RULESYNC_AGENT_INSTRUCTIONS_UNIFICATION.md) | Unification of agent instructions and rulesync behavior. |
| [CHANGE_REQUEST_INGESTER/](proposals/CHANGE_REQUEST_INGESTER/) | Change-request ingester design, implementation plans, and follow-up records. |
| [SHAPESHIFTER_PROJECT_AI_ADVISOR/](proposals/SHAPESHIFTER_PROJECT_AI_ADVISOR/) | Project advisor proposal and implementation-readiness documents. |

## Supporting Material

| Location | Contents |
|---|---|
| [presentations/](presentations/) | Presentations for development teams, archaeologists, and stakeholders. |
| [other/](other/) | Specialized extension and implementation guides. |
| [templates/](templates/) | Templates for proposals and other project documents. |
| [whats-new/](whats-new/) | User-facing release notes and publishing templates. |
| [archive/](archive/) | Historical implementation notes and feature-specific records. |

## Navigation

- **Use Shape Shifter:** [USER_GUIDE.md](USER_GUIDE.md) and [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)
- **Develop:** [DEVELOPMENT.md](DEVELOPMENT.md), [DESIGN.md](DESIGN.md), and [TESTING.md](TESTING.md)
- **Operate:** [OPERATIONS.md](OPERATIONS.md), [container/README.md](../container/README.md), and [container/DEPLOYMENT.md](../container/DEPLOYMENT.md)
- **Understand requirements:** [REQUIREMENTS.md](REQUIREMENTS.md) and [GLOSSARY.md](GLOSSARY.md)
- **Configure relationships:** [Foreign Key Constraints](CONFIGURATION_GUIDE.md#foreign-key-constraints) and [Append Project](CONFIGURATION_GUIDE.md#append-project-unionconcatenation)
- **Validate projects:** [Project Validation](CONFIGURATION_GUIDE.md#project-validation)

Archived documents are retained for historical reference and may describe behavior that no longer exists. Use the active documents above for current behavior.
