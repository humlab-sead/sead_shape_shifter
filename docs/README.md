# Shape Shifter Documentation

## Overview

This directory contains comprehensive documentation for the Shape Shifter data transformation framework and its Configuration Editor UI.

## Main Documentation

These are the primary system documentation files:

### User Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** (7,500+ lines)
  - Getting started with Shape Shifter
  - Working with configurations
  - Managing entities and relationships
  - Dual-mode entity editing (Form and YAML)
  - Validation workflows
  - Auto-fix features
  - Performance optimization
  - Tips, troubleshooting, and FAQ

- **[YAML_EDITOR_FEATURE.md](YAML_EDITOR_FEATURE.md)** (600+ lines) **★ NEW FEATURE**
  - Dual-mode editing (Form ↔ YAML)
  - Monaco Editor integration
  - Real-time YAML validation
  - Bidirectional synchronization
  - User workflows and best practices
  - Implementation details
  - Testing procedures

### System Requirements & Architecture

- **[UI_REQUIREMENTS.md](UI_REQUIREMENTS.md)** (5,900+ lines)
  - 33 functional requirements (FR-1 to FR-33)
  - 15 non-functional requirements (NFR-1 to NFR-15)
  - User personas and use cases
  - Success criteria and constraints
  - Comprehensive glossary

- **[UI_ARCHITECTURE.md](UI_ARCHITECTURE.md)** (1,000+ lines)
  - System architecture (React 18 + FastAPI)
  - Backend and frontend architecture details
  - Design patterns and best practices
  - API design and data flow
  - Security considerations
  - Deployment architecture

### Configuration

- **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** (2,500+ lines) **★ COMPREHENSIVE CONSOLIDATED GUIDE**
  - Complete YAML configuration reference
  - Entity definitions and all properties
  - **Foreign Key Constraints** - Complete validation system with cardinality, match requirements, data quality constraints
  - **Append Configuration** - Union/concatenation of multiple data sources (SQL, fixed, data)
  - **Configuration Validation** - 9 validation specifications with detailed error reporting
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
  - Frontend development with React
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

- **[VALIDATION_IMPROVEMENTS.md](VALIDATION_IMPROVEMENTS.md)** (242 lines)
  - Configuration validation specifications  
  - SQL data validation
  - Entity existence checks
  - Circular dependency detection
  - Validation error reporting
  - **Note**: See [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) for comprehensive constraint and validation documentation

### Advanced Features

- **[YAML_EDITOR_FEATURE.md](YAML_EDITOR_FEATURE.md)** (600+ lines) **★ NEW**
  - Dual-mode entity editor (Form/YAML)
  - Monaco Editor integration with syntax highlighting
  - Real-time validation and error reporting
  - Bidirectional sync between Form and YAML
  - User workflows for beginners and advanced users
  - Component architecture and implementation
  - Testing strategies

- **[ENTITY_STATE_MANAGEMENT.md](ENTITY_STATE_MANAGEMENT.md)** (800+ lines)
  - Entity state architecture
  - Three-layer state management (Pinia → API → YAML files)
  - State synchronization patterns
  - Component interactions
  - Best practices and troubleshooting

- **[BACKEND_INTEGRATION.md](BACKEND_INTEGRATION.md)** (321 lines)
  - Backend architecture overview
  - Package dependency structure
  - Model adapters and REST API integration
  - Installation procedures
  - Development vs production setup

## Project Documentation

Development-related documentation organized by phase:

### Phase 1

See [phase1/README.md](phase1/README.md) for Phase 1 planning documents.

### Phase 2

See [phase2/README.md](phase2/README.md) for Phase 2 development sprints and implementation details.

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
- Configuration validation: [CONFIGURATION_GUIDE.md - Configuration Validation section](CONFIGURATION_GUIDE.md#configuration-validation)

**Understand Requirements:**
- Feature requirements: [UI_REQUIREMENTS.md](UI_REQUIREMENTS.md)
- System architecture: [UI_ARCHITECTURE.md](UI_ARCHITECTURE.md)

**Configure Relationships:**
- Foreign keys & constraints: [CONFIGURATION_GUIDE.md - Foreign Key Constraints section](CONFIGURATION_GUIDE.md#foreign-key-constraints)
- Union/concatenation: [CONFIGURATION_GUIDE.md - Append Configuration section](CONFIGURATION_GUIDE.md#append-configuration-unionconcatenation)

**Validate Configurations:**
- Comprehensive validation guide: [CONFIGURATION_GUIDE.md - Configuration Validation section](CONFIGURATION_GUIDE.md#configuration-validation)
- Validation improvements: [VALIDATION_IMPROVEMENTS.md](VALIDATION_IMPROVEMENTS.md)

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

**Last Updated**: December 14, 2025  
**Documentation Version**: 1.0
