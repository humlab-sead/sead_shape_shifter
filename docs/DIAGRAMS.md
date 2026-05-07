# Shape Shifter - System Diagrams

Diagrams showing Shape Shifter's architecture, workflow, and capabilities.

---

## 1. The Problem: Data Integration Chaos

```mermaid
flowchart LR
    subgraph "Data Providers"
        P1[Provider A<br/>Excel]
        P2[Provider B<br/>Access DB]
        P3[Provider C<br/>CSV Files]
        P4[Provider D<br/>Database]
    end

    subgraph "Manual Pain Points"
        M1[Manual Column Mapping]
        M2[Inconsistent Formats]
        M3[Error-Prone Transforms]
        M4[ID Lookup Nightmares]
        M5[Weeks of Work]
        M6[Hard to Reproduce]
    end

    subgraph "SEAD"
        S[Standard Schema<br/>Valid IDs · Clean Data<br/>Documented Provenance]
    end

    P1 --> M1
    P2 --> M2
    P3 --> M3
    P4 --> M4
    M1 --> M5
    M2 --> M5
    M3 --> M5
    M4 --> M6
    M5 --> S
    M6 --> S

    classDef provider fill:#f5f5f5,stroke:#aaa,color:#333;
    classDef pain fill:#ffe0e0,stroke:#d64545,color:#4a1f1f;
    classDef goal fill:#dff7e8,stroke:#2e9f5b,color:#1d3a29;

    class P1,P2,P3,P4 provider;
    class M1,M2,M3,M4,M5,M6 pain;
    class S goal;
```

---

## 2. The Solution: Shape Shifter Integration Platform

```mermaid
flowchart LR
    subgraph "Data Sources"
        DS1[Provider A<br/>Excel]
        DS2[Provider B<br/>Access DB]
        DS3[Provider C<br/>CSV Files]
        DS4[Provider D<br/>Database]
    end

    subgraph "Shape Shifter Platform"
        direction TB
        SS1[Configure Once<br/>Declarative YAML]
        SS2[Automatic Validation<br/>Multi-Level Checks]
        SS3[Identity Reconciliation<br/>Auto-Match + Review]
        SS4[Transformation Engine<br/>Reproducible Pipeline]
        SS5[Preview and Verify<br/>Before Commit]
    end

    subgraph "SEAD"
        SEAD[Validated Data<br/>Resolved IDs<br/>Documented Lineage<br/>Ready to Import]
    end

    DS1 --> SS1
    DS2 --> SS1
    DS3 --> SS1
    DS4 --> SS1

    SS1 --> SS2
    SS2 --> SS3
    SS3 --> SS4
    SS4 --> SS5
    SS5 --> SEAD

    classDef source fill:#f5f5f5,stroke:#aaa,color:#333;
    classDef platform fill:#e8f4fd,stroke:#4a90d9,color:#1a3a5c;
    classDef goal fill:#dff7e8,stroke:#2e9f5b,color:#1d3a29;

    class DS1,DS2,DS3,DS4 source;
    class SS1,SS2,SS3,SS4,SS5 platform;
    class SEAD goal;
```

---

## 3. Complete User Workflow

```mermaid
flowchart TB
    subgraph "1 Setup Phase"
        A1[Create Project]
        A2[Configure<br/>Data Sources]
        A3[Define<br/>Entities]
    end
    
    subgraph "2 Configuration Phase"
        B1[Set Up<br/>Relationships]
        B2[Configure<br/>Transformations]
        B3[Add<br/>Filters]
    end
    
    subgraph "3 Validation Phase"
        C1[Run<br/>Validation]
        C2[Review<br/>Errors]
        C3[Resolve<br/>Issues]
    end
    
    subgraph "4 Reconciliation Phase"
        D1[Configure<br/>Reconciliation]
        D2[Auto-Match<br/>Identities]
        D3[Review &<br/>Accept]
    end
    
    subgraph "5 Dispatch Phase"
        E1[Configure<br/>Target]
        E2[Preview<br/>Results]
        E3[Dispatch<br/>to SEAD]
    end
    
    A1 --> A2 --> A3
    A3 --> B1 --> B2 --> B3
    B3 --> C1 --> C2 --> C3
    C3 --> D1 --> D2 --> D3
    D3 --> E1 --> E2 --> E3
    
    C2 -.->|Errors Found| B1
    C2 -.->|No Errors| D1
```

---

## 4. System Architecture

```mermaid
flowchart TB
    subgraph "Frontend Layer (Vue 3 + Vuetify)"
        UI1[Projects View]
        UI2[Entity Manager]
        UI3[Dependency Graph<br/>Cytoscape.js]
        UI4[Validation Panel]
        UI5[Reconciliation Editor]
        UI6[Dispatch Console]
        UI7[YAML Editor<br/>Monaco]
    end
    
    subgraph "State Management (Pinia)"
        ST1[Project Store]
        ST2[Entity Store]
        ST3[Validation Store]
        ST4[Data Source Store]
        ST5[Ingester Store]
    end
    
    subgraph "Backend Services (FastAPI)"
        SVC1[Project Service]
        SVC2[Validation Service]
        SVC3[ShapeShift Service<br/>3-Tier Cache]
        SVC4[Reconciliation Service]
        SVC5[Ingester Registry]
        SVC6[Schema Service]
    end
    
    subgraph "Core Engine (Python)"
        CORE1[Configuration Loader]
        CORE2[Data Loaders]
        CORE3[Constraint Validators]
        CORE4[Transformation Pipeline]
        CORE5[Dispatchers]
    end
    
    subgraph "External Systems"
        EXT1[Data Sources<br/>PostgreSQL, Access, CSV]
        EXT2[Reconciliation Services<br/>OpenRefine Protocol]
        EXT3[Target Systems<br/>SEAD Clearinghouse]
    end
    
    UI1 --> ST1
    UI2 --> ST2
    UI3 --> ST2
    UI4 --> ST3
    UI5 --> ST2
    UI6 --> ST5
    UI7 --> ST1
    
    ST1 --> SVC1
    ST2 --> SVC2
    ST3 --> SVC2
    ST4 --> SVC6
    ST5 --> SVC5
    
    SVC1 --> CORE1
    SVC2 --> CORE3
    SVC3 --> CORE4
    SVC4 --> EXT2
    SVC5 --> CORE5
    SVC6 --> CORE2
    
    CORE2 --> EXT1
    CORE4 --> EXT1
    CORE5 --> EXT3

    classDef graph fill:#e8f4fd,stroke:#4a90d9,color:#1a3a5c;
    classDef cache fill:#fdf3e8,stroke:#d48a2a,color:#4a2800;
    classDef pipeline fill:#f5e8fd,stroke:#8a4ab0,color:#3a1060;

    class UI3 graph;
    class SVC3 cache;
    class CORE4 pipeline;
```

---

## 5. Tabbed Project Interface

```mermaid
flowchart TB
    subgraph "Project Detail View"
        direction LR
        
        subgraph "Tabs"
            direction TB
            T1[📋 Entities]
            T2[🔗 Dependencies]
            T3[✅ Validation]
            T4[🔄 Reconciliation]
            T5[📤 Dispatch]
            T6[📝 YAML]
        end
        
        subgraph "Entities Tab"
            E1[Entity List]
            E2[Create/Edit Forms]
            E3[Preview Data]
        end
        
        subgraph "Dependencies Tab"
            D1[Interactive Graph]
            D2[Hierarchical View]
            D3[Force-Directed Layout]
        end
        
        subgraph "Validation Tab"
            V1[Run All Validations]
            V2[Error Summary]
            V3[Issue Review]
        end
        
        subgraph "Reconciliation Tab"
            R1[Form Editor]
            R2[Auto-Reconcile]
            R3[Review Grid]
        end
        
        subgraph "Dispatch Tab"
            DI1[Select Ingester]
            DI2[Configure Target]
            DI3[Validate & Send]
        end
        
        T1 -.-> E1 & E2 & E3
        T2 -.-> D1 & D2 & D3
        T3 -.-> V1 & V2 & V3
        T4 -.-> R1 & R2 & R3
        T5 -.-> DI1 & DI2 & DI3
    end
```

---

## 6. Data Transformation Pipeline

```mermaid
flowchart LR
    subgraph "Input"
        I1[Multiple<br/>Data Sources]
    end
    
    subgraph "Extract"
        E1[SQL Query]
        E2[CSV Load]
        E3[Excel Read]
        E4[Fixed Values]
    end
    
    subgraph "Filter"
        F1[Post-Load<br/>Filters]
        F2[exists_in<br/>Checks]
    end
    
    subgraph "Link"
        L1[Foreign Key<br/>Resolution]
        L2[Constraint<br/>Validation]
        L3[Surrogate ID<br/>Generation]
    end
    
    subgraph "Unnest"
        U1[Wide to Long<br/>Transform]
        U2[Melt<br/>Operations]
    end
    
    subgraph "Translate"
        TR1[Column<br/>Mapping]
        TR2[Extra<br/>Columns]
    end
    
    subgraph "Store"
        S1[Excel]
        S2[CSV]
        S3[Database]
        S4[Dispatcher]
    end
    
    I1 --> E1 & E2 & E3 & E4
    E1 --> F1
    E2 --> F1
    E3 --> F1
    E4 --> F1
    
    F1 --> F2
    F2 --> L1
    L1 --> L2
    L2 --> L3
    L3 --> U1
    U1 --> U2
    U2 --> TR1
    TR1 --> TR2
    TR2 --> S1 & S2 & S3 & S4

    classDef extract fill:#e8f4fd,stroke:#4a90d9,color:#1a3a5c;
    classDef link fill:#fde8d0,stroke:#d48a2a,color:#4a2800;
    classDef unnest fill:#fff7d6,stroke:#d6a300,color:#2b2b2b;
    classDef translate fill:#f5e8fd,stroke:#8a4ab0,color:#3a1060;

    class E1 extract;
    class L1 link;
    class U1 unnest;
    class TR1 translate;
```

---

## 7. Reconciliation Workflow

```mermaid
flowchart TB
    subgraph "Your Data"
        YD[Unique Values<br/>e.g., 500 taxon names]
    end
    
    subgraph "Auto-Reconciliation"
        AR1[Send to<br/>Reconciliation Service]
        AR2[Fuzzy Matching<br/>+ Geographic Distance]
        AR3[Rank Candidates<br/>by Confidence]
    end
    
    subgraph "Threshold Processing"
        TP1{Confidence<br/>Score?}
        TP2[≥95%<br/>Auto-Accept<br/>✅]
        TP3[70-95%<br/>Flag for Review<br/>⚠️]
        TP4[<70%<br/>No Match<br/>❌]
    end
    
    subgraph "Human Review"
        HR1[Review Grid]
        HR2[Select Correct<br/>Candidate]
        HR3[Mark as<br/>Unmatchable]
        HR4[Add Notes]
    end
    
    subgraph "Results"
        R1[Saved Mappings<br/>in Project Config]
        R2[Reusable for<br/>Future Data]
        R3[Documented<br/>Decisions]
    end
    
    YD --> AR1
    AR1 --> AR2
    AR2 --> AR3
    AR3 --> TP1
    
    TP1 -->|High| TP2
    TP1 -->|Medium| TP3
    TP1 -->|Low| TP4
    
    TP2 --> R1
    TP3 --> HR1
    TP4 --> HR1
    
    HR1 --> HR2
    HR1 --> HR3
    HR1 --> HR4
    
    HR2 --> R1
    HR3 --> R1
    HR4 --> R1
    
    R1 --> R2
    R1 --> R3

    classDef autoAccept fill:#dff7e8,stroke:#2e9f5b,color:#1d3a29;
    classDef flagged fill:#fff7d6,stroke:#d6a300,color:#2b2b2b;
    classDef noMatch fill:#ffe0e0,stroke:#d64545,color:#4a1f1f;
    classDef result fill:#e8f4fd,stroke:#4a90d9,color:#1a3a5c;

    class TP2 autoAccept;
    class TP3 flagged;
    class TP4 noMatch;
    class R1 result;
```

---

## 8. Validation System Architecture

```mermaid
flowchart TB
    subgraph "Validation Types"
        V1[Structural<br/>Validation]
        V2[Data<br/>Validation]
        V3[Entity-Specific<br/>Validation]
    end
    
    subgraph "Structural Checks"
        S1[✓ YAML Syntax]
        S2[✓ Required Fields]
        S3[✓ Entity References]
        S4[✓ No Circular Deps]
        S5[✓ Naming Conventions]
    end
    
    subgraph "Data Checks"
        D1[✓ Columns Exist]
        D2[✓ Data Types Match]
        D3[✓ Foreign Keys Valid]
        D4[✓ Unique Constraints]
    end
    
    subgraph "Entity Checks"
        E1[✓ Cardinality Rules]
        E2[✓ Relationship Integrity]
        E3[✓ Query Execution]
    end
    
    subgraph "Results"
        R1[Error Reports]
        R2[Issue Review]
        R3[Manual Changes]
        R4[Re-Validate]
    end
    
    V1 --> S1 & S2 & S3 & S4 & S5
    V2 --> D1 & D2 & D3 & D4
    V3 --> E1 & E2 & E3
    
    S1 --> R1
    S2 --> R1
    S3 --> R1
    D1 --> R1
    D2 --> R1
    E1 --> R1
    
    R1 --> R2
    R2 --> R3
    R3 --> R4

    classDef review fill:#fdf3e8,stroke:#d48a2a,color:#4a2800;
    classDef success fill:#dff7e8,stroke:#2e9f5b,color:#1d3a29;

    class R2 review;
    class R4 success;
```

---

## 9. Caching Strategy (ShapeShift Service)

```mermaid
flowchart TB
    REQ[Preview Request<br/>for Entity]
    
    subgraph "3-Tier Cache Validation"
        T1{TTL Valid?<br/>< 5 minutes}
        T2{Project Version<br/>Changed?}
        T3{Entity Hash<br/>Changed?}
    end
    
    subgraph "Cache Actions"
        HIT[✅ Cache HIT<br/>Return Cached Result]
        MISS[❌ Cache MISS<br/>Regenerate Data]
    end
    
    subgraph "Regeneration"
        G1[Load Entity Config]
        G2[Execute Query]
        G3[Apply Transformations]
        G4[Calculate Hash]
        G5[Cache Result + Metadata]
    end
    
    REQ --> T1
    
    T1 -->|Expired| MISS
    T1 -->|Valid| T2
    
    T2 -->|Changed| MISS
    T2 -->|Same| T3
    
    T3 -->|Changed| MISS
    T3 -->|Same| HIT
    
    MISS --> G1
    G1 --> G2
    G2 --> G3
    G3 --> G4
    G4 --> G5
    
    HIT --> RET[Return to User]
    G5 --> RET

    classDef hit fill:#dff7e8,stroke:#2e9f5b,color:#1d3a29;
    classDef miss fill:#ffe0e0,stroke:#d64545,color:#4a1f1f;
    classDef cached fill:#e8f4fd,stroke:#4a90d9,color:#1a3a5c;

    class HIT hit;
    class MISS miss;
    class G5 cached;
```

---

## 10. Time Savings Comparison

```mermaid
gantt
    title Traditional vs Shape Shifter Data Integration Timeline
    dateFormat X
    axisFormat %H hours
    
    section Traditional Manual Process
    Export & Transform     :t1, 0, 24h
    Manual ID Lookups      :t2, after t1, 8h
    Error Correction       :t3, after t2, 8h
    QA & Validation        :t4, after t3, 8h
    
    section Shape Shifter (First Time)
    Configure Project      :s1, 0, 2h
    Run Reconciliation     :s2, after s1, 1h
    Execute & Validate     :s3, after s2, 5min
    
    section Shape Shifter (Repeat)
    Update & Re-Dispatch   :r1, 0, 15min
```

**Traditional:** ~48 hours per dataset  
**Shape Shifter (First Time):** ~3.5 hours  
**Shape Shifter (Repeat):** ~15 minutes  

---

## 11. Key Features Overview

```mermaid
mindmap
  root((Shape Shifter))
        Project Workspace
            Projects View
                Search and sorting
                Create, copy, delete
                Quick validation
            Project Safety
                Session awareness
                Version-checked saves
                Automatic backups
                Refresh and restore
            Configuration Surfaces
                YAML-first project config
                Raw YAML editor
                Metadata tab
                Files tab
                Data Sources tab
        Entity Modeling
            Supported Entity Types
                Derived entities
                SQL entities
                Fixed values
                CSV and Excel sources
            Entity Editor
                Form mode
                Split preview mode
                Preview-only mode
                Per-entity YAML tab
            Identity System
                system_id
                Business keys
                public_id
            Transformation Tools
                Foreign keys
                Filters
                Unnest
                Append
                Extra columns
                Replace rules
        Graph and Navigation
            Interactive dependency graph
            Source visibility
            Task status tracking
            Quick actions and notes
            Layout controls
            PNG export
        Validation System
            YAML validation
            Data validation
                Sample mode
                Complete mode
                Configurable sample size
            Validator coverage
                Column exists
                Natural key uniqueness
                Non-empty result
            Results workflow
                Grouped issues
                Copyable results
                Guided remediation
        Reconciliation
            OpenRefine protocol services
            Reconciliation specs
            Auto-reconcile
            Confidence scoring
            Review grid
            Reusable mappings
        Execution and Dispatch
            Execute dialog
            Export formats
                Excel
                ZIP CSV
                Folder CSV
                Database targets
            Run validation before execute
            Translation and FK export options
            Dispatch tab
            Ingester configuration
            SEAD delivery workflows
        Data Integration
            Shared data sources
            Schema introspection
            Query testing
            Project-local uploads
            Entity previews
            Dependency-aware caching
        Platform Qualities
            Declarative pipelines
            Reproducible transformations
            Extensible registries
            Multi-user protection
            Auditability and provenance
```

---

## 12. Use Case Feature Map

```mermaid
flowchart TB
    GOAL[User Goals in Shape Shifter]

    GOAL --> MP
    GOAL --> CPS
    GOAL --> EE
    GOAL --> ED
    GOAL --> VCD
    GOAL --> RV
    GOAL --> EXD

    subgraph ManageProjects[Manage Projects]
        direction TB
        MP[Project lifecycle]
        MP1[Create project]
        MP2[Open, copy, delete project]
        MP3[Save changes]
        MP4[Refresh project]
        MP5[Restore backup]
        MP6[Review session status]
        MP --> MP1
        MP --> MP2
        MP --> MP3
        MP --> MP4
        MP --> MP5
        MP --> MP6
    end

    subgraph ConfigureProjectStructure[Configure Project Structure]
        direction TB
        CPS[Project setup]
        CPS1[Edit project YAML]
        CPS2[Edit metadata]
        CPS3[Upload project files]
        CPS4[Connect shared data sources]
        CPS5[Create entity from source table]
        CPS --> CPS1
        CPS --> CPS2
        CPS --> CPS3
        CPS --> CPS4
        CPS4 --> CPS5
    end

    subgraph EditEntity[Edit Entity]
        direction TB
        EE[Entity editing]
        EE1[Define entity type]
        EE2[Configure source entity or data source]
        EE3[Select file, sheet, range, delimiter]
        EE4[Define identity fields]
        EE5[Specify transformations]
        EE6[Edit raw entity YAML]
        EE7[Preview entity output]
        EE --> EE1
        EE --> EE2
        EE --> EE3
        EE --> EE4
        EE --> EE5
        EE --> EE6
        EE --> EE7

        EE4 --> EE41[Set business keys]
        EE4 --> EE42[Set public_id]
        EE4 --> EE43[Keep system_id managed]

        EE5 --> EE51[Specify foreign keys]
        EE5 --> EE52[Specify filters]
        EE5 --> EE53[Specify Unnest]
        EE5 --> EE54[Specify append]
        EE5 --> EE55[Specify extra columns]
        EE5 --> EE56[Specify replace rules]
    end

    subgraph ExploreDependencies[Explore Dependencies]
        direction TB
        ED[Dependency exploration]
        ED1[View graph layout]
        ED2[Inspect source visibility]
        ED3[Review task status]
        ED4[Open notes and quick actions]
        ED5[Export graph image]
        ED --> ED1
        ED --> ED2
        ED --> ED3
        ED --> ED4
        ED --> ED5
    end

    subgraph ValidateConfigurationAndData[Validate Configuration and Data]
        direction TB
        VCD[Validation workflow]
        VCD1[Run YAML validation]
        VCD2[Run sample data validation]
        VCD3[Run complete data validation]
        VCD4[Tune sample size]
        VCD5[Review grouped issues]
        VCD6[Copy validation results]
        VCD --> VCD1
        VCD --> VCD2
        VCD --> VCD3
        VCD --> VCD4
        VCD --> VCD5
        VCD --> VCD6
    end

    subgraph ReconcileValues[Reconcile Values]
        direction TB
        RV[Reconciliation workflow]
        RV1[Configure reconciliation]
        RV2[Edit reconciliation YAML]
        RV3[Run auto-reconcile]
        RV4[Review confidence-ranked matches]
        RV5[Accept, adjust, or reject mappings]
        RV6[Save reusable mappings]
        RV --> RV1
        RV --> RV2
        RV --> RV3
        RV --> RV4
        RV --> RV5
        RV --> RV6
    end

    subgraph ExecuteAndDispatch[Execute and Dispatch]
        direction TB
        EXD[Delivery workflow]
        EXD1[Select output format]
        EXD2[Set file, folder, or database target]
        EXD3[Run validation before execute]
        EXD4[Apply translations]
        EXD5[Drop foreign key columns]
        EXD6[Download result file]
        EXD7[Dispatch via ingester config]
        EXD8[Deliver to SEAD workflow]
        EXD --> EXD1
        EXD --> EXD2
        EXD --> EXD3
        EXD --> EXD4
        EXD --> EXD5
        EXD --> EXD6
        EXD --> EXD7
        EXD --> EXD8
    end
```

---

## 13. User Personas & Use Cases

```mermaid
flowchart LR
    subgraph "Domain Data Manager"
        U1[📊 Archaeologist<br/>Limited Programming]
        UC1[Create Configurations<br/>Using Forms]
        UC2[Validate Data<br/>Before Submission]
        UC3[Preview Results<br/>Visually]
    end
    
    subgraph "Data Engineer"
        U2[🔧 Technical User<br/>SQL/Database Skills]
        UC4[Complex Queries<br/>& Transformations]
        UC5[Schema<br/>Introspection]
        UC6[Performance<br/>Optimization]
    end
    
    subgraph "Developer/Integrator"
        U3[💻 Software Dev<br/>API Integration]
        UC7[Programmatic<br/>Configuration]
        UC8[Pipeline<br/>Automation]
        UC9[Custom<br/>Validators]
    end
    
    U1 --> UC1 & UC2 & UC3
    U2 --> UC4 & UC5 & UC6
    U3 --> UC7 & UC8 & UC9
```
---

## 14. Component Architecture

```mermaid
flowchart TB
    subgraph Browser["Web Browser"]
        direction LR
        subgraph FE["Frontend (Vue 3 + Pinia)"]
            direction TB
            FE_VIEWS["Views\nProjects · Entity Editor\nDependency Graph · Validation\nReconciliation · YAML Editor"]
            FE_STORES["Pinia Stores\nproject · entity · validation\nsession · data-source"]
            FE_API["API Layer (Axios)\n/api/v1/*"]
            FE_VIEWS --> FE_STORES --> FE_API
        end
    end

    subgraph Container["Docker Container (port 8012)"]
        direction TB
        subgraph BE["Backend (FastAPI)"]
            direction TB
            BE_ROUTERS["Routers\nprojects · entities · preview\nvalidation · execute · ingesters\nreconciliation · sessions · logs"]
            BE_SERVICES["Services\nProjectService · ValidationService\nShapeShiftService · SchemaService\nReconciliationService · SessionService"]
            BE_MAPPERS["Mappers\nProjectMapper\n(env var + directive resolution)"]
            BE_CLIENTS["Clients\nSimsClient · ReconciliationClient"]
            BE_STATE["ApplicationState\n(lifespan singleton)"]
            BE_ROUTERS --> BE_SERVICES --> BE_MAPPERS
            BE_SERVICES --> BE_STATE
            BE_SERVICES --> BE_CLIENTS
        end

        subgraph CORE["Core (src/)"]
            direction TB
            CORE_NORM["ShapeShifter / ProcessState\n(orchestrator)"]
            CORE_LOADERS["DataLoaders\nsql · csv · xlsx · fixed"]
            CORE_VALID["Validators\nconstraint · cardinality · FK"]
            CORE_DISPATCH["Dispatchers\nexcel · csv · database"]
            CORE_SPEC["Specifications\n(DAG, references, identity)"]
            CORE_NORM --> CORE_LOADERS
            CORE_NORM --> CORE_VALID
            CORE_NORM --> CORE_DISPATCH
            CORE_SPEC --> CORE_NORM
        end

        BE_MAPPERS --> CORE_NORM
    end

    subgraph EXT["External Systems"]
        FS["File System\nYAML · logs · output · backups"]
        DB["Source Databases\nPostgreSQL · SQLite · MS Access"]
        SIMS["SIMS Service\n(identity resolution)"]
        RECON["Reconciliation Service\n(OpenRefine protocol)"]
    end

    FE_API -->|REST /api/v1| BE_ROUTERS
    CORE_LOADERS --> DB
    CORE_DISPATCH --> FS
    BE_SERVICES --> FS
    BE_CLIENTS --> SIMS
    BE_CLIENTS --> RECON

    classDef fe fill:#e8f4fd,stroke:#4a90d9,color:#1a3a5c;
    classDef be fill:#f0f7e6,stroke:#5a9e3a,color:#1a3c10;
    classDef core fill:#fdf3e8,stroke:#d48a2a,color:#4a2800;
    classDef ext fill:#f5f5f5,stroke:#999,color:#333;

    class FE_VIEWS,FE_STORES,FE_API fe;
    class BE_ROUTERS,BE_SERVICES,BE_MAPPERS,BE_CLIENTS,BE_STATE be;
    class CORE_NORM,CORE_LOADERS,CORE_VALID,CORE_DISPATCH,CORE_SPEC core;
    class FS,DB,SIMS,RECON ext;
```

---

## 15. Project Load – Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend (Pinia)
    participant BE as Backend
    participant PM as ProjectMapper
    participant FS as File System

    U->>FE: Select project
    FE->>BE: GET /api/v1/projects/{name}
    BE->>FS: Read YAML file
    FS-->>BE: Raw YAML content
    BE->>PM: to_api_config(raw_yaml, name)
    note over PM: Preserve ${ENV_VARS}<br/>and @directives unchanged
    PM-->>BE: Project (API model, unresolved)
    BE-->>FE: Project JSON
    FE->>FE: Store in projectStore
    FE-->>U: Render entity list and editor
```

---

## 16. Entity Preview – Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant ED as Monaco Editor
    participant FE as Frontend (Pinia)
    participant BE as Backend
    participant CACHE as ShapeShiftService (Cache)
    participant PM as ProjectMapper
    participant CORE as Core (ShapeShifter)
    participant DB as Source Database

    U->>ED: Edit entity YAML
    ED->>FE: onChange (debounced 300 ms)
    FE->>BE: POST /api/v1/preview
    BE->>CACHE: Check 3-tier cache
    alt Cache hit (TTL valid, version unchanged, hash unchanged)
        CACHE-->>BE: Cached preview rows
    else Cache miss
        CACHE->>PM: to_core(api_project)
        note over PM: Resolve ${ENV_VARS}<br/>and @directives
        PM-->>CACHE: Resolved core project
        CACHE->>CORE: preview(entity, limit)
        CORE->>DB: Execute query / load file
        DB-->>CORE: Raw data
        CORE-->>CACHE: Preview DataFrame
        CACHE->>CACHE: Store with TTL + hash
        CACHE-->>BE: Preview rows
    end
    BE-->>FE: Preview data (JSON)
    FE-->>U: Update split-view grid
```

---

## 17. Validation – Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend
    participant VS as ValidationService
    participant PM as ProjectMapper
    participant CORE as Core (Specifications)
    participant DB as Source Database

    U->>FE: Click "Check Project"
    FE->>BE: POST /api/v1/validate
    BE->>VS: validate(project_name, options)

    VS->>PM: to_core(api_project)
    PM-->>VS: Resolved core project

    VS->>CORE: Structural validation
    note over CORE: DAG cycle check<br/>entity references<br/>identity rules<br/>YAML schema
    CORE-->>VS: Structural issues

    VS->>CORE: Constraint validation
    note over CORE: FK definitions<br/>cardinality rules<br/>functional dependencies
    CORE-->>VS: Constraint issues

    opt Data validation enabled
        VS->>DB: Fetch sample rows
        DB-->>VS: Row sample
        VS->>CORE: Data validators (columns, types, FK values)
        CORE-->>VS: Data issues
    end

    VS-->>BE: ValidationResult (errors / warnings / info)
    BE-->>FE: ValidationResult JSON
    FE-->>U: Show grouped issues in validation panel
```

---

## 18. Execution – Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend
    participant PM as ProjectMapper
    participant CORE as ShapeShifter
    participant PROC as ProcessState
    participant DB as Source Database
    participant OUT as Output (File / DB)

    U->>FE: Click "Execute"
    FE->>BE: POST /api/v1/execute
    BE->>PM: to_core(api_project)
    note over PM: Resolve all env vars<br/>and directives
    PM-->>BE: Resolved core project
    BE->>CORE: normalize()
    CORE->>PROC: Topological sort entities
    PROC-->>CORE: Ordered entity list

    loop For each entity (dependency order)
        alt Entity type == "merged"
            CORE->>CORE: Collect branch DataFrames
            CORE->>CORE: Inject discriminator column
            CORE->>CORE: Propagate sparse FK columns
            CORE->>CORE: Concatenate branches
            CORE->>CORE: Apply post-merge transforms
        else Standard entity
            CORE->>DB: Extract (DataLoader.load())
            DB-->>CORE: Raw DataFrame
            CORE->>CORE: Filter → Link → Unnest → Translate
        end
    end

    CORE->>OUT: Store via Dispatcher (Excel / CSV / DB)
    OUT-->>CORE: Done
    CORE-->>BE: Execution result
    BE-->>FE: Result JSON
    FE-->>U: Show completion status
```

---

## 19. Project Save – Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant BE as Backend
    participant SS as SessionService
    participant FS as File System
    participant PM as ProjectMapper

    U->>FE: Save project
    FE->>BE: PUT /api/v1/projects/{name}
    BE->>SS: Check session version (optimistic lock)
    alt Version conflict
        SS-->>BE: Version mismatch
        BE-->>FE: 409 Conflict
        FE-->>U: "Project changed since load – please refresh"
    else Version OK
        BE->>PM: to_core_dict(api_project)
        note over PM: Preserve @directives<br/>and ${ENV_VARS} in output
        PM-->>BE: YAML-ready dict
        BE->>FS: Write timestamped backup
        FS-->>BE: Backup written
        BE->>FS: Write project YAML
        FS-->>BE: Saved
        BE->>SS: Increment version
        BE-->>FE: 200 OK
        FE-->>U: Project saved
    end
```

---

## 20. Project Refresh – Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant SM as SessionManager (Vue)
    participant PS as projectStore (Pinia)
    participant FE as Frontend API
    participant BE as Backend
    participant SVC as ProjectService
    participant CACHE as All Caches
    participant FS as File System
    participant PM as ProjectMapper

    U->>SM: Click REFRESH button
    alt Unsaved changes detected
        SM->>U: Confirm dialog<br/>"Unsaved changes will be lost"
        U->>SM: Confirm or Cancel
        SM-->>U: Cancel → abort
    end
    SM->>PS: refreshProject(name)
    PS->>PS: loading = true, error = null
    PS->>FE: POST /api/v1/projects/{name}/refresh
    FE->>BE: HTTP POST /api/v1/projects/{name}/refresh
    BE->>SVC: load_project(name, force_reload=True)

    note over SVC,CACHE: force_reload=True triggers full cache wipe
    SVC->>CACHE: _invalidate_all_caches(name)
    CACHE->>CACHE: ApplicationState.invalidate(name)
    note over CACHE: Clears active-project entry<br/>and version counter
    CACHE->>CACHE: ShapeShiftCache.invalidate_project(name)
    note over CACHE: Clears all preview DataFrames<br/>and metadata entries for project
    CACHE->>CACHE: ShapeShiftProjectCache.invalidate_project(name)
    note over CACHE: Clears resolved ShapeShiftProject<br/>instance and version tracking

    SVC->>FS: Read YAML file from disk
    FS-->>SVC: Raw YAML content
    SVC->>PM: to_api_config(raw_yaml, name)
    note over PM: Preserve ${ENV_VARS}<br/>and @directives unchanged
    PM-->>SVC: Project (API model, unresolved)
    SVC-->>BE: Project
    BE-->>FE: Project JSON
    FE-->>PS: Project
    PS->>PS: selectedProject = Project
    PS->>PS: hasUnsavedChanges = false
    PS->>PS: loading = false
    PS-->>SM: Done
    SM-->>U: UI re-renders with fresh data from disk
```

---

## 21. Entity Editing State

```mermaid
stateDiagram-v2
    direction LR

    [*] --> Unmodified : Project loaded
    Unmodified --> Editing : User edits field or YAML
    Editing --> Previewing : Debounce fires (300 ms)
    Previewing --> Editing : Cache miss – query running
    Previewing --> Unmodified : Save succeeds
    Editing --> Unmodified : Save succeeds
    Editing --> Error : Save fails (conflict / IO error)
    Error --> Editing : User corrects and retries
    Unmodified --> [*] : Project closed

    note right of Previewing
        POST /api/v1/preview
        3-tier cache checked
    end note

    note right of Error
        Version conflict or
        file system error
    end note

    classDef clean fill:#dff7e8,stroke:#2e9f5b,color:#1d3a29;
    classDef active fill:#e8f4fd,stroke:#4a90d9,color:#1a3a5c;
    classDef running fill:#fff7d6,stroke:#d6a300,color:#2b2b2b;
    classDef err fill:#ffe0e0,stroke:#d64545,color:#4a1f1f;

    class Unmodified clean;
    class Editing active;
    class Previewing running;
    class Error err;
```

---

## 22. Preview Cache State

```mermaid
stateDiagram-v2
    direction LR

    [*] --> Cold : Application start
    Cold --> Warming : Preview request received
    Warming --> Warm : Query succeeds + result cached
    Warming --> Cold : Query fails
    Warm --> Stale : Project YAML saved (version changed)
    Warm --> Stale : Entity config edited (hash changed)
    Warm --> Expired : TTL elapsed (300 s)
    Stale --> Warming : Next preview request
    Expired --> Warming : Next preview request

    note right of Warm
        TTL valid
        Version matches
        Hash matches
    end note

    note right of Stale
        Version or hash
        mismatch detected
    end note

    classDef cold fill:#eeeeee,stroke:#888,color:#333;
    classDef warming fill:#fff7d6,stroke:#d6a300,color:#2b2b2b;
    classDef warm fill:#dff7e8,stroke:#2e9f5b,color:#1d3a29;
    classDef stale fill:#fde8d0,stroke:#d48a2a,color:#4a2800;
    classDef expired fill:#ffe0e0,stroke:#d64545,color:#4a1f1f;

    class Cold cold;
    class Warming warming;
    class Warm warm;
    class Stale stale;
    class Expired expired;
```

---

## 23. Validation Result State

```mermaid
stateDiagram-v2
    direction LR

    [*] --> NotRun : Project opened
    NotRun --> Running : User triggers validation
    Running --> Valid : No issues found
    Running --> Invalid : Issues found
    Valid --> Stale : Project or entity modified
    Invalid --> Stale : Project or entity modified
    Stale --> Running : User re-runs validation
    Valid --> [*] : Project closed
    Invalid --> [*] : Project closed

    note right of Invalid
        Issues grouped by severity:
        error · warning · info
    end note

    note right of Stale
        Results shown but
        marked out-of-date
    end note

    classDef notrun fill:#eeeeee,stroke:#888,color:#333;
    classDef running fill:#fff7d6,stroke:#d6a300,color:#2b2b2b;
    classDef valid fill:#dff7e8,stroke:#2e9f5b,color:#1d3a29;
    classDef invalid fill:#ffe0e0,stroke:#d64545,color:#4a1f1f;
    classDef stale fill:#fde8d0,stroke:#d48a2a,color:#4a2800;

    class NotRun notrun;
    class Running running;
    class Valid valid;
    class Invalid invalid;
    class Stale stale;

```

---

## 24. Technology Stack

```mermaid
flowchart TB
    subgraph "Browser"
        B1[Modern Web Browser<br/>Chrome, Firefox, Safari]
    end
    
    subgraph "Frontend Technologies"
        F1[Vue 3<br/>Composition API]
        F2[Vuetify 3<br/>Material Design]
        F3[Pinia<br/>State Management]
        F4[TypeScript<br/>Type Safety]
        F5[Monaco Editor<br/>Code Editing]
        F6[Cytoscape.js<br/>Graph Visualization]
        F7[Vite<br/>Build Tool]
    end
    
    subgraph "Backend Technologies"
        BE1[FastAPI<br/>Python Framework]
        BE2[Pydantic v2<br/>Data Validation]
        BE3[SQLAlchemy<br/>ORM]
        BE4[Loguru<br/>Logging]
    end
    
    subgraph "Data Access"
        DA1[PostgreSQL Driver]
        DA2[SQLite Driver]
        DA3[UCanAccess<br/>MS Access]
        DA4[CSV/Excel Parsers]
    end
    
    subgraph "External Integrations"
        EX1[OpenRefine Protocol<br/>Reconciliation]
        EX2[SEAD Clearinghouse<br/>Dispatch Target]
    end
    
    B1 --> F1
    F1 --> F2 & F3 & F4 & F5 & F6
    F1 --> BE1
    F7 -.Build.-> F1
    
    BE1 --> BE2 & BE3 & BE4
    BE1 --> DA1 & DA2 & DA3 & DA4
    BE1 --> EX1 & EX2
```

---

## 25. Deployment Architecture

```mermaid
flowchart TB
    subgraph "Development"
        DEV1[Local Dev Server<br/>npm run dev]
        DEV2[Backend Dev<br/>uvicorn --reload]
    end
    
    subgraph "Production Deployment"
        NGINX[Nginx<br/>Reverse Proxy]
        
        subgraph "Frontend"
            FE[Static Assets<br/>Vite Build]
        end
        
        subgraph "Backend"
            API[FastAPI App<br/>Gunicorn/Uvicorn]
        end
        
        subgraph "Storage"
            FS[File System<br/>Project Configs]
            BACKUP[Backup Directory<br/>Auto-Rotation]
        end
    end
    
    subgraph "Data Sources"
        DB1[(PostgreSQL)]
        DB2[(SQLite)]
        FILES[CSV/Excel Files]
    end
    
    CLIENT[Web Browser] --> NGINX
    NGINX --> FE
    NGINX --> API
    
    API --> FS
    API --> BACKUP
    API --> DB1 & DB2 & FILES
    
    DEV1 -.->|Deploy| FE
    DEV2 -.->|Deploy| API
```

---

## 26. Registry Pattern (Extensibility)

```mermaid
flowchart TB
    subgraph "Core Registries"
        R1[Data Loaders<br/>Registry]
        R2[Validators<br/>Registry]
        R3[Dispatchers<br/>Registry]
        R4[Filters<br/>Registry]
    end
    
    subgraph "Registered Loaders"
        L1[PostgreSQL Loader]
        L2[SQLite Loader]
        L3[CSV Loader]
        L4[Excel Loader]
        L5[MS Access Loader]
        L6[Fixed Values]
    end
    
    subgraph "Registered Validators"
        V1[Cardinality Validator]
        V2[Unique Validator]
        V3[Foreign Key Validator]
        V4[Custom Validators]
    end
    
    subgraph "Registered Dispatchers"
        D1[SEAD Ingester]
        D2[Excel Dispatcher]
        D3[CSV Dispatcher]
        D4[Database Dispatcher]
        D5[Custom Dispatchers]
    end
    
    R1 --> L1 & L2 & L3 & L4 & L5 & L6
    R2 --> V1 & V2 & V3 & V4
    R3 --> D1 & D2 & D3 & D4 & D5
    
    PLUGIN[New Plugin] -.Register.-> R1
    PLUGIN -.Register.-> R2
    PLUGIN -.Register.-> R3

    classDef plugin fill:#fdf3e8,stroke:#d48a2a,color:#4a2800;

    class PLUGIN plugin;
```

---

**Document Version:** 1.0  
**Last Updated:** March 14, 2026  
**Purpose:** Visual documentation of Shape Shifter system architecture and workflows
