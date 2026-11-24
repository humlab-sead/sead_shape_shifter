# SEAD Schema

This folder describes the SEAD database schema that Shape Shifter projects write to.

## Current reference

| File | Content | How it is produced |
| --- | --- | --- |
| [`columns.csv`](columns.csv) | One row per column of every current SEAD table: type, length or precision, nullability, primary key, and foreign-key target table and column. | `make sead-schema` runs [`columns.sql`](columns.sql) read-only against the database in `SEAD_HOST`, `SEAD_PORT`, `SEAD_USER` and `SEAD_DBNAME` (normally `sead_staging`). |
| [`SCHEMA.md`](SCHEMA.md) | The same data as readable Markdown: one section per table with its columns, the tables it references and the tables that reference it. | Generated from `columns.csv` by `make sead-schema` or `make sead-schema-docs`. Do not edit by hand. |
| [`columns.sql`](columns.sql) | The export query. | Edited by hand. |

Use `columns.csv` or `SCHEMA.md` to decide which tables and columns exist, their types, whether they may be null, and how tables are linked. The target model in `resources/target_models/sead_standard_model.yml` is checked against `columns.csv`.

The export leaves out legacy tables and columns on purpose: the `tbl_aggregate*`, `tbl_mcr*`, `tbl_tephra*` and `tbl_isotope*` table families, `tbl_updates_log`, and every `date_updated` column.

### Refreshing

```bash
make sead-schema        # export columns.csv from the database, then regenerate SCHEMA.md
make sead-schema-docs   # regenerate SCHEMA.md from the current columns.csv only
make sead-schema-check  # exit with an error if SCHEMA.md does not match columns.csv
```

`make sead-schema` never prompts for a password. Put it in `~/.pgpass` or `PGPASSWORD`. A failed export leaves the current `columns.csv` unchanged.

## Historical DDL dump

The numbered `*.sql` files (`01_tables.sql` to `07_comments.sql`) are a DDL dump from March 2026 or earlier. They lack tables added since then, for example `tbl_dendro*`, `tbl_ceramics*` and `tbl_data_providers`. Use them only for details the column export does not contain, such as sequences, functions, indexes and column comments, and check anything they say about tables or columns against `columns.csv`.
