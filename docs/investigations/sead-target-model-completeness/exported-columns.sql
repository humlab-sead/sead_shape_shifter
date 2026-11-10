select *
from sead_utility.table_columns
where table_name like 'tbl_%'
  and column_name not in ('date_updated')
  and table_name not like 'tbl_aggregate%'
  and table_name not like 'tbl_mcr%'
  and table_name not like 'tbl_tephra%'
  and table_name not in ('tbl_updates_log')
  and table_name not like 'tbl_isotope%'
