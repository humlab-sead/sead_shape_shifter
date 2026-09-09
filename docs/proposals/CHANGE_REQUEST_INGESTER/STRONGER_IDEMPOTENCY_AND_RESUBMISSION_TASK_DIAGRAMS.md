# Stronger Idempotency And Re-submission Design Diagrams

## Status

- Document type: supporting design specification
- Status: Proposed; scope and open contract decisions remain pending
- Task plan: [Stronger Idempotency And Re-submission](STRONGER_IDEMPOTENCY_AND_RESUBMISSION_TASK_PLAN.md)
- Preceding phase: [SEAD Change Request Submission Metadata](REFACTOR_SEAD_SUBMISSION_METADATA_TASK_PLAN.md)

## Purpose

These diagrams position stronger idempotency and re-submission handling within the SEAD change request ingester. They distinguish current ingester responsibilities from proposed components and show where source validation, durable run identity, prior-run lookup, target comparison, guarded artifacts, and retry handling belong.

The diagrams specify the intended design direction. Names and storage technology for the durable run store remain `TBD` until the re-submission contract is accepted.

## System Position

The change extends the existing ingester pipeline. It does not replace normalization, target-model planning, SIMS allocation, reconciliation, lifecycle policy, artifact rendering, or SCCS deployment.

```mermaid
flowchart LR
    Operator[Operator or API client]

    subgraph Existing[Existing SEAD change request ingester]
        direction LR
        Input[Resolve inputs and add submission rows]
        Plan[Plan rows from target metadata]
        Identity[Resolve identities]
        Project[Project PK and FK values]
        Collision[Check target collisions]
        Render[Render deploy artifact]
        Result[Write artifact and return result]
    end

    subgraph Proposed[Proposed idempotency extension]
        direction LR
        SourceCheck[Normalize comparison values and check duplicates]
        RunStore[Claim idempotency key and load checkpoint]
        Compare[Compare prior run and target state]
        Classify[Apply lifecycle outcomes]
        Guard[Add deployment guards]
    end

    SIMS[(SIMS)]
    Reconciliation[(Reconciliation service)]
    TargetRead[(SEAD target read model)]
    SCCS[SCCS deployment]
    TargetWrite[(SEAD target database)]

    Operator --> Input
    Input --> Plan
    Plan --> SourceCheck
    SourceCheck --> RunStore
    RunStore --> Identity
    Identity <--> SIMS
    Identity <--> Reconciliation
    Identity --> Project
    Project --> Compare
    Compare <--> TargetRead
    Compare --> Classify
    Classify --> Collision
    Collision --> Render
    Render --> Guard
    Guard --> Result
    Result --> Operator
    Operator --> SCCS
    SCCS --> TargetWrite
    TargetWrite -. deployment acknowledgement TBD .-> RunStore

    classDef existing fill:#eef4ff,stroke:#5b7db1,color:#1f2f46;
    classDef proposed fill:#fff7d6,stroke:#b58b18,color:#30270d;
    classDef external fill:#e9f6ec,stroke:#5d9a6f,color:#213629;
    classDef actor fill:#f0f0f0,stroke:#777777,color:#2f2f2f;

    class Input,Plan,Identity,Project,Collision,Render,Result existing;
    class SourceCheck,RunStore,Compare,Classify,Guard proposed;
    class SIMS,Reconciliation,TargetRead,SCCS,TargetWrite external;
    class Operator actor;
```

The proposed run store is the authority for the idempotency key, processing state, prior Binding Set, allocated target IDs, generated package identity, and external side-effect checkpoints. It must be consulted before new SIMS allocation. Target data remains authoritative for rows already deployed to SEAD.

## Proposed Request Sequence

This sequence shows the intended order for a first run, exact rerun, compatible retry, or conflicting reuse. Source validation and the idempotency claim occur before external identity work.

```mermaid
sequenceDiagram
    autonumber
    actor Operator
    participant Ingester as SEAD CR ingester
    participant Source as Source validator
    participant Runs as Durable run store
    participant SIMS
    participant Recon as Reconciliation
    participant Target as SEAD target
    participant Renderer as Artifact renderer
    participant SCCS

    Operator->>Ingester: Submit source and idempotency key
    Ingester->>Ingester: Resolve inputs, derive submission rows, plan rows
    Ingester->>Source: Normalize comparison values and validate row keys
    Source-->>Ingester: Valid rows or duplicate diagnostics

    alt Source conflict
        Ingester-->>Operator: Blocked result, no external side effects
    else Source valid
        Ingester->>Runs: Atomically claim key and load checkpoint
        alt Key owned by concurrent run
            Runs-->>Ingester: In-progress ownership
            Ingester-->>Operator: Retry or in-progress result
        else Key conflicts with stored request
            Runs-->>Ingester: Identity or content conflict
            Ingester-->>Operator: Blocked result
        else New or compatible run
            Runs-->>Ingester: New claim or resumable checkpoint
            opt Identity work not checkpointed
                Ingester->>SIMS: Allocate and confirm Binding Set
                Ingester->>Recon: Resolve existing target identities
                Ingester->>Runs: Save identity checkpoint
            end
            Ingester->>Target: Read comparison rows and baselines
            Target-->>Ingester: Consistent target state
            Ingester->>Ingester: Apply equivalence and lifecycle rules
            alt Blocked or pending review
                Ingester->>Runs: Save classified outcome
                Ingester-->>Operator: Diagnostics, no artifact
            else Exact no-op
                Ingester->>Runs: Save no-op completion
                Ingester-->>Operator: Successful no-op result
            else Accepted change
                Ingester->>Renderer: Render accepted rows and target guards
                Renderer-->>Ingester: Guarded inline or copy-CSV package
                Ingester->>Runs: Save package checkpoint
                Ingester-->>Operator: Package and outcome summary
                Operator->>SCCS: Deploy package
                SCCS->>Target: Check guards and apply atomically
                Target-->>SCCS: Applied or stale-package failure
                SCCS-->>Runs: Record deployment acknowledgement (TBD)
                Runs->>SIMS: Associate change request once
            end
        end
    end
```

The deployment acknowledgement mechanism is unresolved. It must use an existing SCCS, API, or operator workflow and must not require an unplanned change to SCCS internals.

## Row Classification Activity

Source duplicates and target overlap are different checks. Source duplicate handling prevents unnecessary external identity work. Target comparison determines whether a valid row is new, unchanged, update-eligible, review-routed, or blocked.

```mermaid
flowchart TD
    Start([Planned source row]) --> Normalize[Normalize comparison values]
    Normalize --> Key{Complete row key?}
    Key -->|No| BlockKey[Block: incomplete identity metadata]
    Key -->|Yes| Duplicate{Same key in source?}
    Duplicate -->|Identical| DuplicateRule[Apply accepted collapse or rejection rule]
    Duplicate -->|Conflicting| BlockSource[Block: conflicting source rows]
    Duplicate -->|No| Claim[Claim submission idempotency key]
    DuplicateRule --> Claim

    Claim --> Prior{Prior run found?}
    Prior -->|Conflicting request| BlockPrior[Block: idempotency conflict]
    Prior -->|Compatible checkpoint| Reuse[Reuse Binding Set and target IDs]
    Prior -->|No| Resolve[Resolve or allocate identities]
    Reuse --> Compare[Read target row and baseline]
    Resolve --> Compare

    Compare --> Match{Target comparison}
    Match -->|Absent| New[New data]
    Match -->|Equivalent| NoOp[No-op]
    Match -->|Provider-owned mutable change| Update[Allowed update]
    Match -->|Review required| Review[Pending review]
    Match -->|Conflict or indeterminate| BlockTarget[Blocked]

    New --> Emit[Include in guarded package]
    Update --> Emit
    NoOp --> Exclude[Exclude from DML]
    Review --> Stop[Return diagnostics, no artifact]
    BlockKey --> Stop
    BlockSource --> Stop
    BlockPrior --> Stop
    BlockTarget --> Stop

    classDef process fill:#eef4ff,stroke:#5b7db1,color:#1f2f46;
    classDef decision fill:#fff7d6,stroke:#b58b18,color:#30270d;
    classDef accepted fill:#e3f5e8,stroke:#51966a,color:#20382a;
    classDef stopped fill:#ffe4e1,stroke:#bd6a5c,color:#49241e;
    classDef terminal fill:#eeeeee,stroke:#7f7f7f,color:#2f2f2f;

    class Normalize,DuplicateRule,Claim,Reuse,Resolve,Compare process;
    class Key,Duplicate,Prior,Match decision;
    class New,Update accepted;
    class BlockKey,BlockSource,BlockPrior,Review,BlockTarget,Stop stopped;
    class NoOp,Emit,Exclude terminal;
```

Target-ID presence is only a comparison candidate. It does not by itself prove that a row is unchanged or authorize an update.

## Durable Run State

The run store must preserve enough state to resume after interruption without repeating completed identity or association side effects. State names may change when the storage contract is accepted, but the transitions and checkpoints are required.

```mermaid
stateDiagram-v2
    direction LR

    [*] --> Received : Accept request
    Received --> Validated : Source checks pass
    Received --> Blocked : Source checks fail
    Validated --> Claimed : Claim key
    Validated --> InProgress : Another worker owns key
    Validated --> Blocked : Stored request conflicts
    Claimed --> IdentitiesReady : Resolve identities
    IdentitiesReady --> Classified : Compare target state
    Classified --> PendingReview : Review required
    Classified --> Blocked : Unsafe conflict
    Classified --> NoOp : No target change
    Classified --> PackageReady : Accepted changes
    PackageReady --> Applied : Guards pass and deploy
    PackageReady --> Stale : Target state changed
    Applied --> Associated : Associate SIMS change request
    Associated --> Complete : Save completion
    NoOp --> Complete : Save no-op completion

    Received --> Retryable : Interrupted
    Claimed --> Retryable : Interrupted
    IdentitiesReady --> Retryable : Interrupted
    Classified --> Retryable : Interrupted
    PackageReady --> Retryable : Interrupted
    Applied --> Retryable : Interrupted
    Retryable --> Claimed : Resume last checkpoint

    note right of Retryable
        Resume from durable state.
        Do not allocate replacement IDs.
    end note

    note right of Applied
        Deployment acknowledgement
        mechanism is TBD.
    end note

    classDef active fill:#eef4ff,stroke:#5b7db1,color:#1f2f46;
    classDef waiting fill:#fff7d6,stroke:#b58b18,color:#30270d;
    classDef success fill:#e3f5e8,stroke:#51966a,color:#20382a;
    classDef stopped fill:#ffe4e1,stroke:#bd6a5c,color:#49241e;
    classDef neutral fill:#eeeeee,stroke:#7f7f7f,color:#2f2f2f;

    class Received,Validated,Claimed,IdentitiesReady,Classified,PackageReady,Applied,Associated active;
    class InProgress,PendingReview,Retryable waiting;
    class NoOp,Complete success;
    class Blocked,Stale stopped;
```

`Blocked` and `Stale` require a corrected request or a fresh preflight. `PendingReview` resumes only after the existing lifecycle review process allows it. `Retryable` resumes from the last durable checkpoint rather than restarting all work.

## Design Constraints

- Existing lifecycle outcomes remain authoritative: `new_data`, `no_op`, `allowed_update`, `pending_review`, and `blocked`.
- Source duplicate checks complete before SIMS allocation, Binding Set mutation, or change-request association.
- A compatible retry reuses its prior Binding Set and target-ID assignments.
- Concurrent requests for one idempotency key cannot allocate or apply independently.
- Inline INSERT and copy-CSV packages use the same row plan and equivalent deployment guards.
- Target-state guard failure is atomic and produces a stale-package result rather than partial target writes.
- SIMS change-request association occurs once at the accepted completion point.
- The design does not add functional rollback or change SCCS internals.

## Open Design Decisions

The task plan tracks the decisions that must be resolved before implementation. The diagrams depend most directly on:

1. The stable idempotency key and content-equivalence rules.
2. The authoritative durable run store and retention period.
3. The exact durable state names and ownership or lease mechanism.
4. The all-no-op result form.
5. The deployment guard representation for inline and copy-CSV packages.
6. The deployment acknowledgement that marks a package as applied before one-time SIMS association.