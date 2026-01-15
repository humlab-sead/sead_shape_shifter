# Shape Shifter - System Diagrams

Diagrams showing Shape Shifter's architecture, workflow, and capabilities.

---

## 1. The Problem: Data Integration Chaos

```mermaid
flowchart LR
    subgraph "Data Providers"
        P1[<b>Provider</b> A<br/>Excel Spreadsheet]
        P2[<b>Provider</b> B<br/>Access Database]
        P3[<b>Provider</b> C<br/>CSV Files]
        P4[<b>Provider</b> D<br/>Database]
    end
    
    subgraph "Manual Integration Pain Points"
        M1[❌ Manual Column Mapping]
        M2[❌ Inconsistent Formats]
        M3[❌ Manual & Error-Prone Transformations]
        M4[❌ ID Lookup Nightmares]
        M5[❌ Weeks of Work Per Dataset]
        M6[❌ Hard to Reproduce]
    end
    
    subgraph "<b>SEAD</b>"
        S[Requires:<br/>✓ Standard Schema<br/>✓ Valid IDs<br/>✓ Clean Data<br/>✓ Documented Provenance]
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

    style P1 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    style P2 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    style P3 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    style P4 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    
    style M1 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    style M2 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    style M3 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    style M4 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    style M5 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    style M6 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px

    style S fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px

```

---

## 2. The Solution: Shape Shifter Integration Platform

```mermaid
flowchart LR
    subgraph "Data Sources "
        DS1[<b>Provider</b> A<br/>Excel Spreadsheet]
        DS2[<b>Provider</b> B<br/>Access Database]
        DS3[<b>Provider</b> C<br/>CSV Files]
        DS4[<b>Provider</b> D<br/>Database]
    end
    
    subgraph "Shape Shifter Platform"
        direction TB
        SS1[📝 Configure Once<br/>Declarative YAML]
        SS2[✅ Automatic Validation<br/>Multi-Level Checks]
        SS3[🔗 Identity Reconciliation<br/>Auto-Matching + Review]
        SS4[🔄 Transformation Engine<br/>Reproducible Pipeline]
        SS5[📊 Preview & Verify<br/>Before Commit]
    end
    
    subgraph "<b>SEAD</b>"
        SEAD[✓ Validated Data<br/>✓ Resolved IDs<br/>✓ Documented Lineage<br/>✓ Ready to Import]
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

    style DS1 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    style DS2 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    style DS3 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    style DS4 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    
    style SS1 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    style SS2 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    style SS3 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    style SS4 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
    style SS5 fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px

    style SEAD fill:#ffffff,color:#000000,stroke:#ffffff,stroke-width:2px
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
        C3[Apply<br/>Auto-Fixes]
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
    
    style UI3 fill:#e6f3ff
    style SVC3 fill:#fff0e6
    style CORE4 fill:#ffe6f0
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
            V3[Auto-Fix Suggestions]
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
    
    style E1 fill:#e6f3ff
    style L1 fill:#ffe6f0
    style U1 fill:#fff0e6
    style TR1 fill:#f0e6ff
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
    
    style TP2 fill:#ccffcc
    style TP3 fill:#ffffcc
    style TP4 fill:#ffcccc
    style R1 fill:#e6f3ff
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
        R2[Auto-Fix Suggestions]
        R3[Preview Changes]
        R4[One-Click Apply]
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
    
    style R2 fill:#fff0e6
    style R4 fill:#ccffcc
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
    
    style HIT fill:#ccffcc
    style MISS fill:#ffcccc
    style G5 fill:#e6f3ff
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
    Project Management
      YAML Configuration
      Automatic Backups
      Version Control
      Template Support
    Entity Management
      Visual Forms
      Relationship Mapping
      Preview Data
      Dependency Graph
    Validation System
      Multi-Level Checks
      Auto-Fix Suggestions
      Real-Time Feedback
      Error Prevention
    Identity Reconciliation
      Auto-Matching
      Confidence Scoring
      Review Interface
      Reusable Mappings
    Data Integration
      Multiple Sources
      Schema Introspection
      Query Testing
      Foreign Key Validation
    Dispatch System
      Target Configuration
      SEAD Integration
      File Export
      Status Tracking
```

---

## 12. User Personas & Use Cases

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
    
    UC1 & UC2 & UC3 & UC4 & UC5 & UC6 & UC7 & UC8 & UC9 --> RESULT[Clean Data<br/>Ready for SEAD]
    
    style U1 fill:#e6f3ff
    style U2 fill:#fff0e6
    style U3 fill:#ffe6f0
    style RESULT fill:#ccffcc
```

---

## 13. Technology Stack

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

## 14. Deployment Architecture

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

## 15. Registry Pattern (Extensibility)

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
    
    style PLUGIN fill:#fff0e6
```

---

**Document Version:** 1.0  
**Last Updated:** January 12, 2026  
**Purpose:** Visual documentation of Shape Shifter system architecture and workflows
