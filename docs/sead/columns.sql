-- Exports the SEAD table columns used as the schema reference (docs/sead/columns.csv).
-- Run with `make sead-schema`. Read-only.
--
-- One row per column: type, nullability, primary key and foreign-key target.
-- Excluded on purpose because they are legacy: the tbl_aggregate*, tbl_mcr*, tbl_tephra*
-- and tbl_isotope* table families, tbl_updates_log, and every date_updated column.
select *
from sead_utility.table_columns
where table_name like 'tbl_%'
  and column_name not in ('date_updated')
  and table_name not like 'tbl_aggregate%'
  and table_name not like 'tbl_mcr%'
  and table_name not like 'tbl_tephra%'
  and table_name not in ('tbl_updates_log')
  and table_name not like 'tbl_isotope%'
order by table_name, ordinal_position
