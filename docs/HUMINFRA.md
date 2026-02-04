# Huminfra Tool Development Proposal

## Tool project title: Shape Shifter
## Node: Humlab Umeå university

## Abstract (200-300 words)
Shape Shifter is an open-source tool for cleaning, restructuring, and documenting tabular research datasets in a transparent, reproducible way. It was initially developed within the Swedigarch infrastructure. It targets a common pain point in humanities research workflows: data are often assembled from heterogeneous sources (spreadsheets, exports from catalogues/databases, CSV files), then repeatedly transformed in ad-hoc ways that are hard to review, reproduce, or share. Shape Shifter provides a configuration-driven transformation pipeline (extract → filter → link/join → reshape/unnest → map → export) and an editor UI for building and validating that configuration.

The system can be viewed as a lightweight alternative or complement to tools like OpenRefine, emphasizing explicit, versionable project files (YAML) that capture decisions, and validation and error guidance aimed at reducing user friction. The system includes a UI for editing project configuration (which can also be edited in a text editor), and components for loading data from various sources and exporting to common targets (CSV/Excel and databases).

The architecture is extensible: new loaders and export targets can be added following established patterns. The configuration-first approach supports collaboration via version control and sharing of project files; real-time collaborative editing could be explored in the future. The system also supports OpenRefine-like reconciliation of data to external resources or target databases, when such services are available.

The expected contribution to Huminfra is a maintainable component in the broader Huminfra toolset: a shared service that can be deployed by participating nodes, used in training, and integrated into local infrastructures. The innovation is not a novel algorithm, but a practical “configuration as scholarship” approach—making transformation steps inspectable and auditable—while keeping the system lightweight enough for institutional adoption and long-term maintenance.

## Project implementation (200-300 words)
Work will focus on maintainability, usability, and interoperability rather than large feature expansion. The codebase is a mono-repo with a Python transformation engine (Core), a FastAPI backend for project editing/preview/validation, and a Vue 3 + Vuetify frontend for interactive editing. Development tasks will be prioritized around stability and reducing user friction in core workflows: project editing (including joins/foreign keys), YAML round-tripping, and validation that supports real-world humanities datasets without being overly strict.

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
