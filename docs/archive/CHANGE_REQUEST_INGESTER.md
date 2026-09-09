---
**⚠️ NOTE:** This document contains original design notes and has been superseded by structured design documentation:

- **Start here:** [README.md](./README.md) - Overview and navigation guide
- **SIMS:** [sims/SEAD_IDENTITY_SYSTEM.md](./sims/SEAD_IDENTITY_SYSTEM.md) - External identity management system used by the ingester via API
- **Ingester Design:** [SEAD_INGESTER_DESIGN.md](./SEAD_INGESTER_DESIGN.md) - Complete ingester component specification

This file is kept for historical reference and context. SIMS-specific design and implementation material now lives under [sims/](./sims/).

---

# Original Design Notes: New SEAD Ingester

TODO: New SEAD ingester

You and I will design a new ingester that creates SQL DML code instead of writing data to files on disk.

I need your opinion on how to design a ingester that creates SQL DML code instead of writing data to files on disk. My vision is that this system not only is used for reconciliation of data to existing entities in the remote system (e.g. SEAD), but also using using n API published by the SEAD system can allocate primary keys for new entities, and resolve FKs now referring to systems ids to  allocated SEAD of. SEAD uses "Sqitch" as the database change control system, so ultimatly the dispatch should create a SQL DML ready to be commited into SEAD.

The current workflow is this:

  Data provider's data                --> Shape Shifter [ USER ]              --> Project YAML
  Data provider's data + Project YAML --> Shape Shifter [ NORMALIZER ]        --> Normalized DataFrames 
  Normalized DataFrames               --> Shape Shifter [ DISPATCHER ]        --> SEAD-conforming Data (csv or Excel)
  SEAD-conforming Data                --> Shape Shifter [ INGESTER ]          --> SEAD Clearinghouse Submission
  SEAD Clearinghouse Submission       --> SEAD Transport System               --> SEAD Change Request (SQL DML scripts)
  SEAD SEAD Change Request            --> SEAD Change Control System (Sqitch) --> SEAD database
  
Ideally, the same Project YAML can be used for future ingestions, but each new dataset will require some manual, computer-assisted work for e.g. a reconciliation step to match the new data to existing SEAD entities, or for specifying mandatory data that is missing in the incoming data.

