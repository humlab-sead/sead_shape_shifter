# Shape Shifter Documentation

## Overview

This directory contains comprehensive documentation for the Shape Shifter data transformation framework and its Project Editor UI.

## Main Documentation

These are the primary system documentation files:

### User Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)**
  - Getting started with Shape Shifter
  - Working with projects
  - Managing entities and relationships
  - Dual-mode entity editing (Form and YAML)
  - Validation workflows
  - Performance optimization
  - Tips, troubleshooting, and FAQ

### System Requirements & Architecture

- **[REQUIREMENTS.md](REQUIREMENTS.md)**
  - 33 functional requirements (FR-1 to FR-33)
  - 15 non-functional requirements (NFR-1 to NFR-15)
  - User personas and use cases
  - Success criteria and constraints
  - Comprehensive glossary

- **[DESIGN.md](DESIGN.md)**
  - System architecture (Vue3 + FastAPI)
  - Backend and frontend architecture details
  - Design patterns and best practices
  - API design and data flow
  - Security considerations
  - Deployment architecture

### Project

- **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** 
  - Complete YAML configuration reference
  - Entity definitions and all properties
  - **Foreign Key Constraints** - Complete validation system with cardinality, match requirements, data quality constraints
  - **Append Project** - Union/concatenation of multiple data sources (SQL, fixed, data)
  - **Project Validation** - 9 validation specifications with detailed error reporting
  - Data sources and transformations
  - Unnest operations (wide to long format)
  - Special syntax (@value, @include, @load)
  - Complete examples and best practices
  - Troubleshooting guide

- **[DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](DATA_PROVIDER_SUBMISSION_LIFECYCLE.md)**
  - Durable lifecycle policy for provider-submitted data changes
  - Ownership-first update rules and one-live-version history invariants
  - Allowed, restricted, and blocked change classes
  - Minimum state model and state-transition policy contract

### Development

- **[DEVELOPMENT.md](DEVELOPMENT.md)**
  - Development environment setup
  - System architecture deep-dive
  - Backend development with Python/FastAPI
  - Frontend development with Vue3
  - Testing strategies and procedures
  - API development guide
  - Code organization and patterns
  - Best practices and conventions
  - Troubleshooting and debugging
  - Contributing guidelines

- **[OPERATIONS.md](OPERATIONS.md)**
  - Environments and operational assumptions
  - Configuration and secrets model
  - Data layout and mounted paths
  - Build artifacts and image tagging
  - Deployment flow and deploy scripts
  - CI pipeline and release process
  - Post-deployment verification and smoke checks
  - Rollback procedure
  - Health checks, observability, and log management
  - Backup and recovery

- **[proposal-writing-guide.instructions.md](../.github/instructions/proposal-writing-guide.instructions.md)**
  - Rules for writing short, problem-focused design proposals
  - Keeps proposal documents precise, concrete, and decision-oriented
  - Moved to `.github/instructions/` so it loads automatically when editing proposals

- **[templates/PROPOSAL_TEMPLATE.md](templates/PROPOSAL_TEMPLATE.md)**
  - Default template for new design proposals
  - Provides a lean structure with optional sections for more complex decisions

### Testing

- **[TESTING.md](TESTING.md)**
  - Testing philosophy and strategy
  - Backend testing with pytest
  - Frontend testing with Vitest
  - Cross-browser testing procedures
  - Integration testing checklists
  - Manual testing procedures
  - Performance testing
  - Accessibility testing
  - Test data management
  - CI/CD integration

## Supplementary Documentation

### Design Proposals

Proposal documents are grouped by status:

- **[proposals/](proposals/)**: active and backlog proposals under discussion
- **[proposals/future/](proposals/future/)**: deferred proposals kept for later work
- **[proposals/done/](proposals/done/)**: completed or decided proposals
- **[proposals/onhold/](proposals/onhold/)**: paused proposal work

Current proposals:

- **[proposals/BUGSCEP_PILOT_PROJECT.md](proposals/BUGSCEP_PILOT_PROJECT.md)**
  - Documents the current BugsCEP pilot and the next implementation slices for continued migration work.

- **[proposals/BRANCH_SCOPED_CONSUMERS_FOR_MIXED_BRANCH_PARENTS.md](proposals/BRANCH_SCOPED_CONSUMERS_FOR_MIXED_BRANCH_PARENTS.md)**
  - Proposes explicit branch-scoped consumption for downstream entities that read mixed-branch parent rows.

- **[proposals/done/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md](proposals/done/TARGET_MODEL_CONFORMANCE_ENHANCEMENTS.md)**
  - Records the completed conformance backlog rollout and the deferred follow-up that moved out of the active proposal set.

- **[proposals/CHANGE_REQUEST_INGESTER/](proposals/CHANGE_REQUEST_INGESTER/)**
  - Groups the active change-request ingester design and follow-up proposal documents.

Future proposals:

- **[proposals/future/AI_PROJECT_ADVISOR_PROPOSAL.md](proposals/future/AI_PROJECT_ADVISOR_PROPOSAL.md)**
  - Proposal for a grounded project advisor with Shape Shifter and SEAD/SIMS knowledge.

- **[proposals/future/COMMENT_PRESERVING_SAVE_PATH.md](proposals/future/COMMENT_PRESERVING_SAVE_PATH.md)**
  - Proposes preserving YAML comments across ordinary project saves so local modeling rationale is not lost during editor round trips.

- **[proposals/future/COMMENT_PRESERVING_SAVE_PATH_IMPLEMENTATION_SKETCH.md](proposals/future/COMMENT_PRESERVING_SAVE_PATH_IMPLEMENTATION_SKETCH.md)**
  - Companion technical sketch for implementing the comment-preserving save proposal.

- **[proposals/future/FIXED_ENTITY_TYPE_CONVENTION_ENHANCEMENTS.md](proposals/future/FIXED_ENTITY_TYPE_CONVENTION_ENHANCEMENTS.md)**
  - Tracks deferred work around fixed-entity type conventions.

- **[proposals/future/FK_NULL_KEY_POLICY_MODEL.md](proposals/future/FK_NULL_KEY_POLICY_MODEL.md)**
  - Placeholder for a later phase proposal about an explicit missing-key policy model.

- **[proposals/future/NATIVE_APPLICATION_AUTHENTICATION.md](proposals/future/NATIVE_APPLICATION_AUTHENTICATION.md)**
  - Records native application authentication as a possible follow-up to the current nginx identity and application authorization controls.

- **[proposals/future/QUERY_FILTER_ENGINE_SELECTION.md](proposals/future/QUERY_FILTER_ENGINE_SELECTION.md)**
  - Defers a narrow extension to allow explicit pandas query-engine selection (`engine: python`) on `type: query` filters.

- **[proposals/future/PENDING_IMPROVEMENTS.md](proposals/future/PENDING_IMPROVEMENTS.md)**
  - Collects proposal ideas that remain deferred but not yet closed.

- **[proposals/future/UNIFIED_FILE_BACKED_ENTITY_TYPE.md](proposals/future/UNIFIED_FILE_BACKED_ENTITY_TYPE.md)**
  - Proposes replacing separate file-backed entity types with one `type: file` model plus format selection.

### Done Proposals

- **[proposals/done/](proposals/done/)**
  - Browse completed and decided proposal documents.

- **[proposals/done/BOUNDARY_BASED_PROJECT_PERSISTENCE.md](proposals/done/BOUNDARY_BASED_PROJECT_PERSISTENCE.md)**
  - Proposes narrower project-save boundaries as a foundation for later collaboration and persistence improvements.

- **[proposals/done/DERIVED_VALUE_ERGONOMICS_FOLLOW_THROUGH.md](proposals/done/DERIVED_VALUE_ERGONOMICS_FOLLOW_THROUGH.md)**
  - Records the completed follow-through work around `extra_columns` derived values.

- **[proposals/done/FK_LOOKUP_NULL_KEY_DEFAULT_BEHAVIOR.md](proposals/done/FK_LOOKUP_NULL_KEY_DEFAULT_BEHAVIOR.md)**
  - Defines the current default behavior for null handling in lookup-style foreign-key joins.

- **[proposals/done/MATERIALIZED_DEPENDENCY_VISUALIZATION.md](proposals/done/MATERIALIZED_DEPENDENCY_VISUALIZATION.md)**
  - Documents the delivered dependency-graph support for frozen historical source dependencies.

- **[proposals/done/USER_FACING_RELEASE_NOTES_STRATEGY.md](proposals/done/USER_FACING_RELEASE_NOTES_STRATEGY.md)**
  - Covers the adopted strategy for user-facing release notes alongside the technical changelog.

### Other Documents

- **[presentations/PRESENTATION.md](presentations/PRESENTATION.md)**
  - Marp slide deck: general system overview for the SEAD development team

- **[presentations/PRESENTATION_ARCHAEOLOGISTS.md](presentations/PRESENTATION_ARCHAEOLOGISTS.md)**
  - Marp slide deck: Shape Shifter overview for archaeologists and domain experts

- **[presentations/EXECUTIVE_SUMMARY.md](presentations/EXECUTIVE_SUMMARY.md)**
  - Short non-technical summary of Shape Shifter for stakeholders

- **[other/DSL_EXTENSIBILITY_GUIDE.md](other/DSL_EXTENSIBILITY_GUIDE.md)**
  - Extension guide for adding new expression types or functions to the tiny DSL after the initial implementation.
  - Covers AST, parser, validator, evaluator, and backend update points.

### What's New

- **[whats-new/README.md](whats-new/README.md)**
  - User-facing release notes index and publishing guidance

- **[whats-new/TEMPLATE.md](whats-new/TEMPLATE.md)**
  - Reusable template for concise, non-technical release summaries

## Archived Documentation

Historical implementation notes and feature-specific documentation have been moved to [archive/](archive/) including:
- Entity state management implementations
- Server state refactoring notes  
- Schema refactoring details
- Hash-based cache invalidation
- Driver schema registry
- Split pane implementations
- YAML editor feature specs
- Frontend session management
- Reconciliation revision notes

These are preserved for reference but may contain outdated information.

## Quick Navigation

### I want to

**Use Shape Shifter:**
- Start here: [USER_GUIDE.md](USER_GUIDE.md)
- Configure transformations: [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)

**Develop on Shape Shifter:**
- Start here: [DEVELOPMENT.md](DEVELOPMENT.md)
- Architecture overview: [DESIGN.md](DESIGN.md)
- Operations and deployment: [OPERATIONS.md](OPERATIONS.md)

**Test Shape Shifter:**
- Testing procedures: [TESTING.md](TESTING.md)
- Project validation: [CONFIGURATION_GUIDE.md - Project Validation section](CONFIGURATION_GUIDE.md#project-validation)

**Understand Requirements:**
- Feature requirements: [REQUIREMENTS.md](REQUIREMENTS.md)
- System architecture: [DESIGN.md](DESIGN.md)

**Configure Relationships:**
- Foreign keys & constraints: [CONFIGURATION_GUIDE.md - Foreign Key Constraints section](CONFIGURATION_GUIDE.md#foreign-key-constraints)
- Union/concatenation: [CONFIGURATION_GUIDE.md - Append Project section](CONFIGURATION_GUIDE.md#append-project-unionconcatenation)

**Validate Projects:**
- Comprehensive validation guide: [CONFIGURATION_GUIDE.md - Project Validation section](CONFIGURATION_GUIDE.md#project-validation)

## Documentation Standards

All main documentation follows these principles:

- **Complete**: Comprehensive coverage of features and use cases
- **Accurate**: Up-to-date with current implementation
- **Clear**: Written for the target audience (users, developers, testers)
- **Project-Agnostic**: Free of sprint/phase-specific references
- **Maintainable**: Structured for long-term maintenance
- **Searchable**: Clear headings, table of contents, and cross-references

## Contributing to Documentation

When updating documentation:

1. **Update the relevant main guide** rather than creating new files
2. **Maintain consistency** with existing structure and style
3. **Update this README** if adding new documentation files
4. **Test examples** to ensure they work with current code
5. **Update cross-references** if moving or renaming content
6. **Remove outdated information** rather than marking as deprecated

## Version History

- **v0.2.0** (2025-12-31): Configuration → Project refactoring
  - Renamed "configuration" to "project" throughout
  - Archived implementation-specific documentation
  - Updated API endpoints and class names
  - Consolidated active documentation
  
- **v0.1.0** (2025-12-14): Initial consolidated documentation
  - Created 6 main system documentation files
  - Consolidated 10+ source documents
  - Established documentation structure

## Support

For questions or issues:

- **GitHub Issues**: Report bugs or request features
- **Discussions**: Ask questions and share ideas
- **Documentation Issues**: Report inaccuracies or suggest improvements

---

**Last Updated**: December 31, 2025  
**Documentation Version**: 2.0
