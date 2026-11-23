# Reconciliation workflow diagrams

These diagrams show how source-row keys and target-record IDs move through reconciliation. `local_key_value` identifies a source row; `target_id` identifies a record in the target system. The reconciliation catalog stores candidate results from ranked candidate matching and review decisions. The mapping sidecar stores links that normalization applies.

See the [reconciliation improvement backlog](./RECONCILIATION_IMPROVEMENTS_BACKLOG.md) for proposed workflow improvements.

## Ranked candidate matching

```mermaid
sequenceDiagram
    actor Reviewer
    participant View as Reconciliation view
    participant API as Shape Shifter API
    participant Authority as Authority Service
    participant Catalog as Reconciliation catalog

    Reviewer->>View: Select Find Candidates for a source row
    View->>API: Send local_key_value and source-row search values
    API->>Authority: Request candidates using the configured matching strategy
    Authority-->>API: Return scored candidate URI and target_id values
    API->>Catalog: Save candidates under local_key_value
    API-->>View: Show scored candidates in the candidate grid
    Note over View,Catalog: Matching strategy ranks candidates. local_key_value keeps the source row identity.
```

## Interactive Search/Browse

```mermaid
sequenceDiagram
    actor Reviewer
    participant View as Review workspace
    participant API as Shape Shifter API
    participant Authority as Authority Service

    alt Search
        Reviewer->>View: Enter search text and optional context
        View->>API: Send reviewer-entered search request
        API->>Authority: Search for matching records
        Authority-->>API: Return matching records, possibly ranked
        API-->>View: Show search results
    else Browse
        Reviewer->>View: Select Browse
        View->>API: Request the complete eligible list
        API->>Authority: Load list within advertised limits
        Authority-->>API: Return complete list or too-large result
        API-->>View: Show list or explicit size message
    end
    Note over Reviewer,Authority: The workflow starts from reviewer input or browsing. Search may also rank results.
```

## Accept a candidate

```mermaid
sequenceDiagram
    actor Reviewer
    participant View as Reconciliation view
    participant API as Shape Shifter API
    participant Catalog as Reconciliation catalog

    Reviewer->>View: Select a candidate
    View->>API: Save local_key_value, candidate URI, and target_id
    API->>Catalog: Store accepted decision
    API-->>View: Return saved review state
    Note over Catalog: The decision is saved, but normalized output does not change until export.
```

## Mark a row New

```mermaid
sequenceDiagram
    actor Reviewer
    participant View as Reconciliation view
    participant API as Shape Shifter API
    participant Catalog as Reconciliation catalog

    Reviewer->>View: Mark row New
    View->>API: Save New decision for local_key_value
    API->>Catalog: Store explicit decision without target_id
    API-->>View: Return saved review state
    Note over Reviewer,Catalog: An empty search result does not mark a row New. The reviewer makes this decision.
```

## Export accepted decisions

```mermaid
sequenceDiagram
    actor Reviewer
    participant View as Reconciliation view
    participant API as Shape Shifter API
    participant Authority as Authority Service
    participant Catalog as Reconciliation catalog
    participant Mapping as Mapping sidecar

    Reviewer->>View: Select Export to Mapping
    View->>API: Export accepted decisions
    API->>Catalog: Read accepted decisions by local_key_value
    API->>Authority: Verify candidate URI and target_id
    Authority-->>API: Return verification outcome
    API->>Mapping: Apply exportable local_key_value → target_id links
    API-->>View: Return per-row export results
    Note over Catalog,Mapping: The catalog stores decisions. The sidecar stores links that normalization applies.
```

## Add a manual link

```mermaid
sequenceDiagram
    actor Reviewer
    participant View as Reconciliation view
    participant API as Shape Shifter API
    participant Mapping as Mapping sidecar

    Reviewer->>View: Enter local_key_value and target_id
    View->>API: Add Manual Link
    API->>Mapping: Write a manual link directly
    Mapping-->>API: Save link
    API-->>View: Confirm saved link
    Note over API,Mapping: Manual links are trusted and are not checked against the Authority Service.
```

## Clear a decision or sidecar mapping (R32)

TBD: This diagram describes the proposed R32 workflow, not current behavior.

```mermaid
sequenceDiagram
    actor Reviewer
    participant View as Reconciliation view
    participant API as Shape Shifter API
    participant Catalog as Reconciliation catalog
    participant Mapping as Mapping sidecar

    Reviewer->>View: Select project, entity, target field, and business key
    View->>API: Load records for the selected key
    API->>Catalog: Read decision
    Catalog-->>API: Decision or none
    API->>Mapping: Read link or New approval
    Mapping-->>API: Sidecar entry or none
    API-->>View: Return matching records
    View-->>Reviewer: Show records and affected files, and disable unavailable actions
    Reviewer->>View: Choose Clear decision, Delete sidecar mapping, or Clear both
    View-->>Reviewer: Show changes and ask for confirmation
    Note over Reviewer,View: Deleting a manual or protected link requires explicit sidecar-delete confirmation.
    Reviewer->>View: Confirm action

    alt Clear decision
        View->>API: Clear decision for key
        API->>Catalog: Delete decision
        Catalog-->>API: Deletion result
        Note over Catalog,Mapping: The sidecar entry remains unchanged.
    else Delete sidecar mapping
        View->>API: Delete sidecar entry for key
        API->>Mapping: Delete link or New approval
        Mapping-->>API: Deletion result
        Note over Catalog,Mapping: The decision remains. A later export may recreate the entry.
    else Clear both
        View->>API: Clear decision and sidecar entry for key
        API->>Catalog: Delete decision
        Catalog-->>API: Deletion result
        API->>Mapping: Delete link or New approval
        Mapping-->>API: Deletion result
    end

    API-->>View: Return individual deletion results
    alt Any deletion succeeds
        View->>API: Refresh row and outstanding-change state
        API-->>View: Return current state
    end
    View-->>Reviewer: Show what was removed and what remains, including failures
    Note over API,Mapping: Other keys and specifications remain unchanged.
```

## Run normalization

```mermaid
sequenceDiagram
    participant Runner as Normalization workflow
    participant Normalizer
    participant Mapping as Mapping sidecar

    Runner->>Normalizer: Normalize entity
    Normalizer->>Mapping: Read current links by source key
    Mapping-->>Normalizer: Return local_key_value → target_id links
    Normalizer-->>Runner: Write mapped target IDs to output public_id
    Note over Normalizer: Core foreign-key links continue to use local system_id values.
```