# SEAD Change Request Diagrams

This document gives a high-level view of the core runtime flow in the `sead_change_request` ingester.

The diagrams follow the current implementation in `ingester.py` and `preparation.py`:

- `validate_tables()` and `ingest_tables()` are the public table entry points; they copy and sanitize the supplied frames before reusing the bundle workflow
- the public `validate()` and `ingest()` methods reject the retired file input before any preparation
- the private `_validate_bundle()` and `_ingest_bundle()` methods reuse the same preparation path for an already prepared `SourceTableBundle`
- the preparation path stops after identity resolution and PK/FK target projection
- `_ingest_bundle()` continues with collision checks, package assembly, artifact rendering, and bundle emission

## Public Table Input Flow

This sequence shows how normalized tables reach the shared workflow.

```mermaid
sequenceDiagram
    autonumber
    actor Caller
    participant Ingester as SeadChangeRequestIngester
    participant Adapter as Input resolution adapter
    participant Bundle as _validate_bundle() or _ingest_bundle()

    Caller->>Ingester: validate_tables(tables, source_name) or ingest_tables(tables, source_name, validate_first)
    Ingester->>Adapter: _build_source_bundle(tables, source_name)
    note over Adapter: copy each DataFrame,<br/>sanitize caller-visible column labels,<br/>keep entity names, values, dtypes, and timezones
    alt Invalid mapping
        Adapter-->>Ingester: SourceBundleError
        Ingester-->>Caller: structured ValidationResult or IngestionResult failure
    else Bundle built
        Adapter-->>Ingester: SourceTableBundle
        Ingester->>Bundle: validate or ingest
        Bundle-->>Caller: ValidationResult or IngestionResult
    end
```

## Retired File Input Flow

This sequence shows the only behavior available through the public protocol methods.

```mermaid
sequenceDiagram
    autonumber
    actor Caller
    participant Ingester as SeadChangeRequestIngester
    participant Result as ValidationResult or IngestionResult

    Caller->>Ingester: validate(source) or ingest(source, validate_first)
    note over Ingester: no source read, project load, SIMS call,<br/>target check, or bundle write
    Ingester->>Result: structured input failure
    Result-->>Caller: is_valid=false or success=false
```

A `Path` or `str` also fails inside the source resolver before `config.extra` is read, so a
path-shaped source cannot select `source_bundle` or `tables`.

## Shared Preparation Flow

This sequence shows the common path reused by the table methods and the private bundle methods.

```mermaid
sequenceDiagram
    autonumber
    actor Caller
    participant Ingester as SeadChangeRequestIngester
    participant Inputs as Input resolution
    participant Planning as Table planning
    participant Prep as prepare_change_request()
    participant Orch as Identity orchestration
    participant Resolve as Identity resolution
    participant Project as PK/FK target projection
    participant Confirm as Pending confirmation report

    Caller->>Ingester: validate_tables(tables) or _validate_bundle(bundle) or _ingest_bundle(bundle)
    Ingester->>Inputs: resolve_inputs(config, bundle)
    Inputs-->>Ingester: ResolvedInputs
    Ingester->>Planning: plan_bundle(bundle, target_model.entities)
    Planning-->>Ingester: PlannedBundle
    Ingester->>Prep: prepare_change_request(inputs, planned)
    Prep->>Orch: orchestrate_identity_assignments(...)
    Orch-->>Prep: assignments and Binding Set state
    Prep->>Resolve: resolve_planned_tables(...)
    Resolve-->>Prep: IdentityResolutionResult
    Prep->>Project: project_target_ids(...)
    Project-->>Prep: TargetProjectionResult

    alt Binding Set is not confirmed and rows remain blocked
        Prep->>Confirm: build_pending_confirmation_report(...)
        Confirm-->>Prep: PendingConfirmationReport
    end

    Prep-->>Ingester: PreparationResult
```

## Validate Flow

This sequence shows how `_validate_bundle()` turns the shared preparation result into a `ValidationResult`.

```mermaid
sequenceDiagram
    autonumber
    actor Caller
    participant Ingester as SeadChangeRequestIngester
    participant Prep as Shared preparation flow
    participant Result as ValidationResult

    Caller->>Ingester: validate_tables(tables) or _validate_bundle(bundle)
    Ingester->>Prep: _prepare_change_request(bundle)
    Prep-->>Ingester: PreparationResult

    alt Input resolution fails
        Ingester->>Result: build invalid result from InputResolutionError
    else Planning or target projection adds errors
        Ingester->>Result: include diagnostics as validation errors
    else Identity resolution is blocked
        Ingester->>Result: include blocked-row diagnostics and pending report
    else Validation succeeds
        Ingester->>Result: include warnings, infos, and pending report if present
    end

    Result-->>Caller: ValidationResult
```

## Ingest Flow

This sequence shows the full ingestion path after validation has passed.

```mermaid
sequenceDiagram
    autonumber
    actor Caller
    participant Ingester as SeadChangeRequestIngester
    participant Validate as _validate_bundle()
    participant Prep as Shared preparation flow
    participant Collisions as Collision checks
    participant Package as Change package builder
    participant Render as Deploy artifact renderer
    participant SIMS as SIMS client
    participant Files as Bundle writer

    Caller->>Ingester: ingest_tables(tables, validate_first) or _ingest_bundle(bundle, validate_first)

    alt validate_first is true
        Ingester->>Validate: _validate_bundle(bundle)
        Validate-->>Ingester: ValidationResult
        alt Validation failed
            Ingester-->>Caller: Failed IngestionResult
        end
    end

    Ingester->>Prep: _prepare_change_request(bundle)
    Prep-->>Ingester: PreparationResult

    alt Planned errors, blocked rows, or target projection diagnostics
        Ingester-->>Caller: Failed IngestionResult
    else Preparation succeeded
        opt collision_checker is configured
            Ingester->>Collisions: check_projected_collisions(...)
            Collisions-->>Ingester: CollisionCheckResult
        end

        alt collision conflicts found
            Ingester-->>Caller: Failed IngestionResult
        else no conflicts
            Ingester->>Package: build_change_request_package(...)
            Package-->>Ingester: ChangeRequestPackage
            Ingester->>Render: build_deploy_artifact(...)
            Render-->>Ingester: DeployArtifact

            opt Binding Set UUID and CR name are present
                Ingester->>SIMS: associate_change_request(...)
                SIMS-->>Ingester: association recorded
            end

            Ingester->>Files: write_artifact_bundle(...)
            Files-->>Ingester: artifact directory path
            Ingester-->>Caller: Successful IngestionResult
        end
    end
```

## Deploy Rendering Rules

`inline_insert`, `copy_csv`, and `inline_staging` render the same prepared values:

- a `date` target renders the normalized calendar date only
- a timezone-naive timestamp target keeps the normalized calendar and clock fields and drops timezone metadata without conversion
- an explicitly timezone-aware target type fails with `ValueError` before the bundle writer runs
