# SEAD Shape Shifter

Shape Shifter is a declarative data transformation framework with a Python processing engine, a FastAPI service, and a Vue-based Project Editor. It helps data managers and developers transform diverse source data into target schemas through YAML project definitions, validation, relationship handling, and export workflows.

The project was developed for archaeological data integration with the Strategic Environmental Archaeology Database (SEAD), but its transformation pipeline is designed for other structured-data workflows as well.

## Capabilities

- Extract data from CSV, Excel, PostgreSQL, SQLite, and MS Access sources.
- Process entities through the fixed pipeline: Extract, Filter, Link, Unnest, Translate, and Store.
- Validate project structure, data quality, dependencies, foreign keys, and target-model constraints.
- Edit projects through the Vue Project Editor or its YAML editor.
- Preview entities, inspect dependencies, reconcile values, and dispatch validated results.
- Extend loaders, transforms, validators, and ingesters through the project registries.

## Quick Start

The supported container deployment uses rootless Podman and serves the frontend and backend together.

```bash
git clone https://github.com/humlab-sead/sead_shape_shifter.git
cd sead_shape_shifter/container
make setup
make build
make up
make healthcheck
```

Open the application at <http://localhost:8012/>. The API documentation is at <http://localhost:8012/api/v1/docs>, and the health endpoint is <http://localhost:8012/api/v1/health>.

See [container/README.md](container/README.md) for deployment prerequisites, configuration, lifecycle commands, and diagnostics. See [container/DEPLOYMENT.md](container/DEPLOYMENT.md) for deployment hosts, NGINX, systemd, and multiple environments.

## Prerequisites

- Python 3.13 or newer for local development.
- Java Runtime Environment for MS Access support through UCanAccess.
- `uv` for Python environments and commands.
- `pnpm` for frontend development.

## Documentation

- [User Guide](docs/USER_GUIDE.md): create projects, manage entities, validate data, and export results.
- [Configuration Guide](docs/CONFIGURATION_GUIDE.md): YAML fields, data sources, transformations, relationships, and validation rules.
- [Design](docs/DESIGN.md): architecture, data flow, API boundaries, and design decisions.
- [Operations](docs/OPERATIONS.md): runtime settings, deployment invariants, backups, verification, and rollback.
- [Development](docs/DEVELOPMENT.md): local setup, development commands, conventions, and contribution workflow.
- [Testing](docs/TESTING.md): test strategy and validation procedures.
- [Diagrams](docs/DIAGRAMS.md): system, workflow, sequence, state, deployment, and registry diagrams.
- [Documentation Index](docs/README.md): complete documentation map.
- [Agent Guide](AGENTS.md): repository architecture and coding conventions.

## API

The backend serves the Project Editor and exposes the REST API under `/api/v1`. The health endpoint is available without proxy authentication; deployed environments must put the remaining API and UI behind the configured trusted proxy.

## License And Acknowledgments

This project is part of the SEAD initiative at Humlab, Umeå University. Developed by the SEAD Project Team.

Report issues and request changes through the [GitHub repository](https://github.com/humlab-sead/sead_shape_shifter).
