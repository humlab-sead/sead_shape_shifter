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
  - Auto-fix features
  - Performance optimization
  - Tips, troubleshooting, and FAQ

### System Requirements & Architecture

- **[UI_REQUIREMENTS.md](UI_REQUIREMENTS.md)** (5,900+ lines)
  - 33 functional requirements (FR-1 to FR-33)
  - 15 non-functional requirements (NFR-1 to NFR-15)
  - User personas and use cases
  - Success criteria and constraints
  - Comprehensive glossary

- **[UI_ARCHITECTURE.md](UI_ARCHITECTURE.md)** (1,000+ lines)
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

### Core Framework Features

- **[METADATA_GUIDE.md](METADATA_GUIDE.md)** 
  - Project metadata specifications  
  - Entity metadata management
  - Version tracking
  - Validation status
  - Best practices
  
### Reconciliation Features

- **[RECONCILIATION_SETUP_GUIDE.md](RECONCILIATION_SETUP_GUIDE.md)**
  - Entity reconciliation setup
  - Source configuration
  - Mapping and matching strategies
  - API integration

### Environment

- **[ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)**
  - Environment variable configuration
  - Data source setup
  - Security best practices

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

### I want to...

**Use Shape Shifter:**
- Start here: [USER_GUIDE.md](USER_GUIDE.md)
- Configure transformations: [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)

**Develop on Shape Shifter:**
- Start here: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- Architecture overview: [UI_ARCHITECTURE.md](UI_ARCHITECTURE.md)
- Backend integration: [BACKEND_INTEGRATION.md](BACKEND_INTEGRATION.md)

**Test Shape Shifter:**
- Testing procedures: [TESTING_GUIDE.md](TESTING_GUIDE.md)
- Project validation: [CONFIGURATION_GUIDE.md - Project Validation section](CONFIGURATION_GUIDE.md#project-validation)

**Understand Requirements:**
- Feature requirements: [UI_REQUIREMENTS.md](UI_REQUIREMENTS.md)
- System architecture: [UI_ARCHITECTURE.md](UI_ARCHITECTURE.md)

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
