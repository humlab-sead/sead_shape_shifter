# SEAD Change Request Diagrams

This document gives a high-level view of the core runtime flow in the `sead_change_request` ingester.

The diagrams follow the current implementation in `ingester.py` and `preparation.py`:

- `validate()` and `ingest()` both reuse the same preparation path
- the preparation path stops after identity resolution and PK/FK target projection
- `ingest()` continues with collision checks, package assembly, artifact rendering, and bundle emission

## Shared Preparation Flow

This sequence shows the common path reused by both `validate()` and `ingest()`.

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

    Caller->>Ingester: validate(source) or ingest(source)
    Ingester->>Inputs: resolve_inputs(config, source)
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

This sequence shows how `validate()` turns the shared preparation result into a `ValidationResult`.

```mermaid
sequenceDiagram
    autonumber
    actor Caller
    participant Ingester as SeadChangeRequestIngester
    participant Prep as Shared preparation flow
    participant Result as ValidationResult

    Caller->>Ingester: validate(source)
    Ingester->>Prep: _prepare_change_request(source)
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
    participant Validate as validate()
    participant Prep as Shared preparation flow
    participant Collisions as Collision checks
    participant Package as Change package builder
    participant Render as Deploy artifact renderer
    participant SIMS as SIMS client
    participant Files as Bundle writer

    Caller->>Ingester: ingest(source, validate_first)

    alt validate_first is true
        Ingester->>Validate: validate(source)
        Validate-->>Ingester: ValidationResult
        alt Validation failed
            Ingester-->>Caller: Failed IngestionResult
        end
    end

    Ingester->>Prep: _prepare_change_request(source)
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