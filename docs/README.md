# Shape Shifter Documentation

## Overview

This directory contains comprehensive documentation for the Shape Shifter data transformation framework and its Project Editor UI.

## Main Documentation

These are the primary system documentation files:

### User Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** (7,500+ lines)
  - Getting started with Shape Shifter
  - Working with projects
  - Managing entities and relationships
  - Dual-mode entity editing (Form and YAML)
  - Validation workflows
  - Performance optimization
  - Tips, troubleshooting, and FAQ

### System Requirements & Architecture

- **[REQUIREMENTS.md](REQUIREMENTS.md)** (5,900+ lines)
  - 33 functional requirements (FR-1 to FR-33)
  - 15 non-functional requirements (NFR-1 to NFR-15)
  - User personas and use cases
  - Success criteria and constraints
  - Comprehensive glossary

- **[ARCHITECTURE.md](ARCHITECTURE.md)** (1,000+ lines)
  - System architecture (Vue3 + FastAPI)
  - Backend and frontend architecture details
  - Design patterns and best practices
  - API design and data flow
  - Security considerations
  - Deployment architecture

### Project

- **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** (2,500+ lines) **★ COMPREHENSIVE CONSOLIDATED GUIDE**
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

### Development

- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** (10,000+ lines)
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

### Testing

- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** (3,800+ lines)
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

### Reconciliation Features

- **[RECONCILIATION_SETUP_GUIDE.md](RECONCILIATION_SETUP_GUIDE.md)**
  - Entity reconciliation setup
  - Source configuration
  - Mapping and matching strategies
  - API integration

### Design Proposals

- **[proposals/AI_PROJECT_ADVISOR_PROPOSAL.md](proposals/AI_PROJECT_ADVISOR_PROPOSAL.md)**
  - Proposal for a project advisor with Shape Shifter and SEAD/SIMS knowledge
  - Scope, architecture, context model, safety boundaries, and phased delivery

- **[proposals/QUERY_FILTER_ENGINE_SELECTION.md](proposals/QUERY_FILTER_ENGINE_SELECTION.md)**
  - Proposes adding an explicit `engine` field to `type: query` filters for advanced pandas query behavior
  - Recommends `engine: python` over prefix forms like `query: "python:..."`

- **[proposals/USER_FACING_RELEASE_NOTES_STRATEGY.md](proposals/USER_FACING_RELEASE_NOTES_STRATEGY.md)**
  - Recommends keeping the technical `CHANGELOG.md` while adding curated user-facing release notes
  - Covers both the documentation strategy and the semantic-release workflow for publishing shorter GitHub Release summaries

- **[proposals/ENTITY_LEVEL_LOCKING.md](proposals/ENTITY_LEVEL_LOCKING.md)**
  - Shape Shifter currently has optimistic locking at the project level for the entire project.
  - The most frequent use case in the UI, is where a user opens, edits, and saves one entity at a time.
  - This proposal introduces optimistic locking at an entity level increasing collaborative work.

### Done Proposals

- **[proposals/done/FK_LOOKUP_NULL_KEY_DEFAULT_BEHAVIOR.md](proposals/done/FK_LOOKUP_NULL_KEY_DEFAULT_BEHAVIOR.md)**
  - Defines the Phase 1 lookup-join default for null handling in alternative-key foreign key joins.
  - Recommends leaving the FK unresolved instead of raising when lookup-style joins have missing alternative keys.

- **[proposals/FK_NULL_KEY_POLICY_MODEL.md](proposals/FK_NULL_KEY_POLICY_MODEL.md)**
  - Placeholder for a future Phase 2 proposal about an explicit missing-key policy model.
  - Outlines the open design questions for a broader user-facing null-key strategy.

- **[proposals/VUETIFY_4_MIGRATION_RESUME_PLAN.md](proposals/VUETIFY_4_MIGRATION_RESUME_PLAN.md)**
  - Records the current Vuetify 4 migration findings, including what is safe and unsafe to pre-apply.
  - Captures the resume plan, affected files, and recommended execution order for the eventual frontend upgrade.

- **[proposals/RAW_SOURCE_DATA_EXPLORER_PROPOSAL.md](proposals/RAW_SOURCE_DATA_EXPLORER_PROPOSAL.md)**
  - Proposes evolving Schema Explorer into a stronger raw source data investigation tool.
  - Recommends a phased path from AG Grid-based loaded-row preview to larger fetches, server-driven exploration, and column profiling.

- **[proposals/COMPLEX_ENTITY_MODELING_ERGONOMICS.md](proposals/COMPLEX_ENTITY_MODELING_ERGONOMICS.md)**
  - Proposes new modeling ergonomics for complex target-schema scenarios such as merged parent entities, lookup/fact pairs, and branch-aware downstream entities.
  - Recommends computed columns, branch-scoped consumers, target-aware validation, and comment-preserving YAML saves as the highest-value improvements.

- **[proposals/done/INTRODUCE_TINY_DSL_IN_EXTRA_COLUMNS.md](proposals/done/INTRODUCE_TINY_DSL_IN_EXTRA_COLUMNS.md)**
  - Proposes a small, safe DSL layered on top of `extra_columns` for lightweight derived-value transforms.
  - Positions the feature relative to `translate`, `replacements`, and Proposal 3 in the complex-entity ergonomics work.

- **[proposals/done/TINY_DSL_EXTRA_COLUMNS_IMPLEMENTATION_SKETCH.md](proposals/done/TINY_DSL_EXTRA_COLUMNS_IMPLEMENTATION_SKETCH.md)**
  - Companion technical design sketch for implementing the tiny DSL in `extra_columns`.
  - Describes proposed classes, function signatures, parser shape, pandas execution model, and test strategy.

- **[proposals/done/STAGED_FILTER_EXECUTION.md](proposals/done/STAGED_FILTER_EXECUTION.md)**
  - Proposes stage-aware filter execution so filters can run after linking or unnesting when needed.
  - Preserves the current default early-filter behavior while adding explicit later pipeline stages.

- **[proposals/done/MATERIALIZED_DEPENDENCY_VISUALIZATION.md](proposals/done/MATERIALIZED_DEPENDENCY_VISUALIZATION.md)**
  - Documents the implemented dependency-graph support for showing frozen historical source dependencies on materialized fixed entities.
  - Covers the backend extractor, frozen edge metadata, Cytoscape styling, and validation coverage.

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

## Archived Documentation

Previously consolidated source documents are available in the [archive/](archive/) directory for historical reference.

## Quick Navigation

### I want to

**Use Shape Shifter:**
- Start here: [USER_GUIDE.md](USER_GUIDE.md)
- Configure transformations: [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)

**Develop on Shape Shifter:**
- Start here: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- Architecture overview: [ARCHITECTURE.md](ARCHITECTURE.md)
- Backend integration: [BACKEND_INTEGRATION.md](BACKEND_INTEGRATION.md)

**Test Shape Shifter:**
- Testing procedures: [TESTING_GUIDE.md](TESTING_GUIDE.md)
- Project validation: [CONFIGURATION_GUIDE.md - Project Validation section](CONFIGURATION_GUIDE.md#project-validation)

**Understand Requirements:**
- Feature requirements: [REQUIREMENTS.md](REQUIREMENTS.md)
- System architecture: [ARCHITECTURE.md](ARCHITECTURE.md)

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
