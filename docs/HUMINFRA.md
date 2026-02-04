# Huminfra Tool Development Proposal

## Tool project title: Shape Shifter
## Node: Humlab Umeå university

## Abstract (200-300 words)
Shape Shifter is an open-source tool for cleaning, restructuring, and documenting tabular research datasets in a transparent, reproducible way. It was initially developed within the Swedigarch infrastructure. It targets a common pain point in humanities research workflows: data are often assembled from heterogeneous sources (spreadsheets, exports from catalogues/databases, CSV files), then repeatedly transformed in ad-hoc ways that are hard to review, reproduce, or share. Shape Shifter provides a configuration-driven transformation pipeline (extract → filter → link/join → reshape/unnest → map → export) and an editor UI for building and validating that configuration.

In ongoing use, the tool is being applied to import archaeological data (1) from the Arbodat MS Access database into the SEAD database, and (2) from Excel files delivered by other data providers. These cases illustrate the intended role: turning heterogeneous tabular inputs into a documented, repeatable transformation that can be re-run when new deliveries arrive.

The system can be used as an alternative or complement to tools like OpenRefine. It emphasizes explicit, versionable project files (YAML) that capture transformation choices, plus validation and error messages that help users correct common issues. The system includes a UI for editing project configuration (which can also be edited in a text editor), and components for loading data from various sources and exporting to common targets (CSV/Excel and databases).

The architecture is extensible: new loaders and export targets can be added following established patterns. The configuration-first approach supports collaboration by sharing and reviewing project files (for example via version control); real-time collaborative editing is not a current feature. The system also supports OpenRefine-like reconciliation of data to external resources or target databases, when such services are available.

For Huminfra, the value is a maintainable tool that makes data preparation steps explicit (in a project file), so that transformations can be reviewed and re-run. The aim is a practical, supportable workflow rather than a new algorithm.

## Project implementation (200-300 words)
Work will focus on maintainability, usability, and interoperability rather than large feature expansion. The codebase is a mono-repo with a Python transformation engine (Core), a FastAPI backend for project editing/preview/validation, and a Vue 3 + Vuetify frontend for interactive editing. Development tasks will be prioritized around stability and improving core workflows needed for real imports (e.g., MS Access and Excel): project editing (including joins/foreign keys), YAML round-tripping, and validation that supports real-world humanities datasets without being overly strict.

Planned implementation activities:
- Quality and reliability: tighten automated tests for critical user flows and add regression tests for known error scenarios.
- Error and validation handling: make validation issues actionable with clear user-facing guidance and consistent error reporting.
- Editor UX improvements: improve change tracking, schema-guided editors, and clearer feedback during validation and preview.
- Interoperability: document and stabilize the project file format; keep export targets and integration points (CSV/Excel/DB) predictable.
- Deployment and operations: provide reproducible deployment guidance (Docker) suitable for node-level hosting.

## Target Audience
Primary users are humanities researchers, research engineers, and data stewards who routinely prepare tabular datasets for analysis, publication, or integration into databases. Secondary users include staff and infrastructure units that need a lightweight, locally deployable tool to normalize dataset exports (spreadsheets/CSV/database extracts) into consistent, documented formats. The tool supports these needs by making transformations explicit, reviewable, and repeatable through project files and validation.

## Collaboration and Partners
A practical collaboration model would involve:
- One node leading core maintenance (testing, releases, architecture decisions)
- One or more nodes contributing usability and testing (user studies with researchers, training feedback, validation requirements)
- One or more nodes contributing deployment guidance, packaging, and training materials

## Timeline and Project Scope
A realistic scope is a short-to-mid-term maintenance and consolidation phase (12–18 months), with milestones:
1. Months 1–3: baseline review, test hardening, and prioritization of UX/validation issues.
2. Months 4–9: targeted UX improvements, stabilize YAML round-tripping, and improve error messages and documentation.
3. Months 10–18: deployment hardening, integration guidance for the Huminfra toolset context, training materials, and adding minor features driven by user needs.


## Additional comments
Key risks are long-term maintenance burden and heterogeneous user data. Mitigations: conservative scope, strong regression tests, a clear project-file specification, and a continuous feedback loop via collaborating nodes.

The tool is best positioned as a “dataset mangling and normalization” component within a larger toolset, not as a one-size-fits-all platform. Hosting is feasible at node level via Docker; coordination on authentication and integration can be addressed incrementally depending on Huminfra’s platform direction.
