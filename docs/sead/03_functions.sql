--
-- PostgreSQL database dump
--

\restrict t8vzGfeSUOgeKdezgypNIEKYe6p3YVep0icm3QiGYx4XxxeJIJs0yw4Z3KNhBaG

-- Dumped from database version 16.4 (Debian 16.4-1.pgdg110+2)
-- Dumped by pg_dump version 18.1

set statement_timeout = 0;
set lock_timeout = 0;
set idle_in_transaction_session_timeout = 0;
set transaction_timeout = 0;
set client_encoding = 'UTF8';
set standard_conforming_strings = on;
select pg_catalog.set_config('search_path', '', false);
set check_function_bodies = false;
set xmloption = content;
set client_min_messages = warning;
set row_security = off;

--
-- Name: apa(); Type: FUNCTION; Schema: public; Owner: humlab_admin
--

create function public.apa() returns integer
language plpgsql stable
as $$
begin
  return 42;
end;
$$;


alter function public.apa() owner to humlab_admin;

--
-- Name: get_sample_graph(integer); Type: FUNCTION; Schema: public; Owner: humlab_admin
--

create function public.get_sample_graph(sample_id integer) returns jsonb
language plpgsql stable
as $_$
declare v_data jsonb;
declare v_ae_limit int := 10;
declare v_av_limit int := 5;
declare v_tc_limit int := 5;
declare v_mv_limit int := 5;
begin
  with
    du as (
      select dimension_id, coalesce(d.dimension_abbrev, 'dimension') as dimension, unit_id, unit_abbrev as unit
      from tbl_dimensions d
      left join tbl_units u using (unit_id)
    ),
    ps as (
      with sample_horizon as (
        select physical_sample_id, string_agg(horizon_name, ', ') as horizon_name
        from tbl_sample_horizons
        join tbl_horizons using (horizon_id)
        group by physical_sample_id
      ), sample_description as (
        select physical_sample_id, string_agg(format('%s: %s', type_name, description), ', ') as description
        from tbl_sample_descriptions
        join tbl_sample_description_types using (sample_description_type_id)
        group by physical_sample_id
      ), sample_alt_refs as (
        select physical_sample_id, string_agg(format('%s: %s', alt_ref_type, alt_ref), ', ') as alt_refs
        from tbl_sample_alt_refs
        join tbl_alt_ref_types using (alt_ref_type_id)
        group by physical_sample_id
      ), sample_notes as (
        select physical_sample_id, string_agg(note, chr(10)) as notes
        from tbl_sample_notes
        group by physical_sample_id
      )
      select physical_sample_id,
            type_name as sample_type,
            sample_name,
            alt_ref_type_id,
            sample_group_id,
            horizon_name,
            sample_description.description,
            alt_refs,
            notes
      from tbl_physical_samples
      join tbl_sample_types using (sample_type_id)
      left join sample_horizon using (physical_sample_id) 
      left join sample_description using (physical_sample_id)
      left join sample_alt_refs using (physical_sample_id)
      left join sample_notes using (physical_sample_id)
      where TRUE
        and physical_sample_id = sample_id
        --and sample_name = 'A017-005'
    ),
    sd as (
      select sd.sample_dimension_id,
          sd.physical_sample_id,
          sd.dimension_value,
          sd.method_id,
          format('%s %s', to_char(dimension_value, 'FM999999999990.0999999999999'), d.unit) as "value",
          d.dimension,
          q.symbol as qualifier,
          x.description
      from tbl_sample_dimensions sd 
      join ps using (physical_sample_id)
      left join du d using (dimension_id)
      left join tbl_methods m using (method_id)
      left join tbl_value_qualifiers q using (qualifier_id)
      left join (
        select physical_sample_id, string_agg(format('[%s]: %s', type_name, description), ' ') as "description"
        from tbl_sample_descriptions
        join tbl_sample_description_types using (sample_description_type_id)
        group by physical_sample_id
      ) as x using (physical_sample_id)
    ),
    sg as (
      with sample_group_dimensions as (
        select sample_group_id, string_agg(format('%s: %s %s', coalesce(d.dimension_abbrev, d.dimension_name), trim_scale(sgd.dimension_value), u.unit_abbrev), chr(10)) as dimensions
        from tbl_sample_group_dimensions sgd
        join tbl_dimensions d using (dimension_id)
		    join tbl_units u using (unit_id)
        group by sample_group_id
      ), sample_group_descriptions as (
        select sample_group_id, string_agg(format('%2$s (%1$s)', sgdt.type_name, sgd.group_description), chr(10)) as descriptions
        from tbl_sample_group_descriptions sgd
        join tbl_sample_group_description_types sgdt using (sample_group_description_type_id)
        group by sample_group_id
      ), sample_group_positions as (
        select sample_group_id, string_agg(format('%s %s: %s %s (%s)', m.method_name, coalesce(d.dimension_abbrev, d.dimension_name), trim_scale(tgc.sample_group_position), u.unit_abbrev, position_accuracy), chr(10)) as positions
        from tbl_sample_group_coordinates tgc
        join tbl_coordinate_method_dimensions cmd using (coordinate_method_dimension_id)
        join tbl_dimensions d using (dimension_id)
        join tbl_units u using (unit_id)
        join tbl_methods m using (method_id)
        group by sample_group_id
      )
        select g.site_id,
              g.sample_group_id,
              g.sample_group_name,
              g.sampling_context_id,
              g.method_id,
              sampling_context,
              dimensions,
              descriptions,
              positions
        from tbl_sample_groups g
        join ps using (sample_group_id)
        left join tbl_sample_group_sampling_contexts using (sampling_context_id)
        left join sample_group_dimensions using (sample_group_id)
        left join sample_group_descriptions using (sample_group_id)
        left join sample_group_positions using (sample_group_id)
      ),
      si as (
      with sor as (
        select site_id, string_agg(record_type_name, chr(10)) as record_types
        from tbl_site_other_records
        join tbl_record_types using (record_type_id)
        group by site_id
      )
      select i.site_id, i.site_name, i.site_location_accuracy, i.national_site_identifier,
              json_build_array(i.latitude_dd, i.longitude_dd) as coordinate,
              record_types
      from tbl_sites i
      join sg using (site_id)
      left join sor using (site_id)
    ),
    ae as (
      select a.analysis_entity_id, a.physical_sample_id, a.dataset_id
      from tbl_analysis_entities a
      -- note: tbl_analysis_entity_dimensions skipped (has no data)
      join ps using (physical_sample_id)
      limit v_ae_limit
    ),
    av as (
      select analysis_entity_id, analysis_value_id, analysis_value, value_class_id
      from tbl_analysis_values
      join ae using (analysis_entity_id)
      limit v_av_limit
    ),
    tc as (
      with identification_level as (
        select abundance_id, string_agg(identification_level_name, ', ') as identification_level
        from tbl_abundance_ident_levels 
        join tbl_identification_levels using (identification_level_id)
        group by abundance_id
      ), modification as (
        select abundance_id, string_agg(modification_type_name, ', ') as modification
        from tbl_abundance_modifications
        join tbl_modification_types using (modification_type_id)
        group by abundance_id
      )
        select analysis_entity_id, abundance_id, taxon_id, abundance as "count", identification_level, modification
        from tbl_abundances
        join ae using (analysis_entity_id)
        left join identification_level using (abundance_id)
        left join modification using (abundance_id)
        limit v_tc_limit
        -- note: tbl_dating_materials skipped (has no data)
    ),
    mv as (
      select measured_value_id, analysis_entity_id, measured_value
      from tbl_measured_values
      join ae using (analysis_entity_id)
      -- note: tbl_measured_value_dimensions skipped (has no data)
      limit v_mv_limit
    ),
    rd as (
      select relative_date_id,
      		 analysis_entity_id,
      		 relative_age_name,
    		 case when coalesce(c14_age_older::bigint, c14_age_younger::bigint) is not null then
        		    format('%s-%s', coalesce(to_char(c14_age_older, 'FM999999999990'), ''), coalesce(to_char(c14_age_younger, 'FM999999999990'), ''))
              else
    		        format('%s-%s', coalesce(to_char(cal_age_older, 'FM999999999990'), ''), coalesce(to_char(cal_age_younger, 'FM999999999990'), ''))
    		 end as dating,
    		 age_type
      from tbl_relative_dates rd
      join tbl_relative_ages ra using (relative_age_id)
      join tbl_relative_age_types rt using (relative_age_type_id)
      join ae using (analysis_entity_id)
    ),
    gc as (
    	select geochron_id, analysis_entity_id, lab_number, age::int,
    		case when coalesce(error_older, error_younger) is null
    			 then null
    			 else
    				json_build_array(error_older::bigint, error_younger::bigint)
    		end as error, delta_13c, international_lab_id as lab_id, uncertainty, notes
    	from tbl_geochronology
    	join tbl_dating_labs using (dating_lab_id)
      left join tbl_dating_uncertainty using (dating_uncertainty_id)
      join ae using (analysis_entity_id)		
    ),
    vc as (
      select value_class_id, c.name, c.method_id, t.name as value_type
      from tbl_value_classes c
      join tbl_value_types t using (value_type_id)
      where value_class_id in (select value_class_id from av)
    ),
    ds as (
      select  d.dataset_id,
              d.dataset_name,
              dt.data_type_name as data_type,
              dm.master_name,
              d.master_set_id,
              d.method_id,
              d.biblio_id,
              d.project_id,
              dm.biblio_id as master_biblio_id
      from tbl_datasets d
      join tbl_data_types dt using (data_type_id)
      join tbl_dataset_masters dm using (master_set_id)
      join ae using (dataset_id)
    ),
    sl as (
      select l.location_id,
            t.location_type,
            l.location_name,
            si.site_id
      from tbl_locations l
      join tbl_location_types t using (location_type_id)
      join tbl_site_locations sl using (location_id)
      join si using (site_id)
    ),
    f as (
      select f.feature_id, ps.physical_sample_id, f.feature_name, f.feature_description, ft.feature_type_name
      from tbl_features f
      join tbl_physical_sample_features psf using (feature_id)
      join ps using (physical_sample_id)
      join tbl_feature_types ft using (feature_type_id)
    ),
    p as (
      select p.project_id, p.project_name, ds.dataset_id
      from tbl_projects p
      join ds using (project_id)
    ),
    aem as (
      select analysis_entity_id, method_id
      from tbl_analysis_entity_prep_methods
      join ae using (analysis_entity_id)
    ),
    si_b as (
      select site_id, biblio_id
      from tbl_site_references
      join si using (site_id)
    ),
    sg_b as (
      select sample_group_id, biblio_id
      from tbl_sample_group_references
      join sg using (sample_group_id)
    ),
    m as (
      select method_id, method_name, record_type_name as record_type, biblio_id
      from tbl_methods
      join tbl_record_types using (record_type_id)
      where method_id in (
        select method_id from ds union all select method_id from sg union all select method_id from aem union all select method_id from vc union all select method_id from sd
      )
    ),
    b as (
      select biblio_id, case when authors is not null then format('%s (%s).', authors, year) else title end as citation
      from tbl_biblio
      where biblio_id in (
        select biblio_id from si_b union
        select biblio_id from ds union
        select biblio_id from m union
        select biblio_id from sg_b)
    ),
    t as (
      select taxon_id, species, genus_name, author_name, family_name
      from tbl_taxa_tree_master
      left join tbl_taxa_tree_genera using (genus_id)
      left join tbl_taxa_tree_authors using (author_id)
      left join tbl_taxa_tree_families using (family_id)
      where taxon_id in (select taxon_id from tc)
    )
      select jsonb_build_object(
          'nodes', jsonb_agg(node) FILTER (where node is not null),
          'edges', jsonb_agg(edge) FILTER (where edge is not null)
      ) into v_data
      from (
        -- SITE
        select jsonb_build_object(
            'id', 'site_' || si.site_id,
            'entity','Site',
            'label', site_name,
            'attrs', jsonb_strip_nulls(jsonb_build_object(
              -- 'name', site_name,
              'national_id', national_site_identifier,
              'accuracy', site_location_accuracy,
              'coordinate', coordinate,
              'record_types', record_types
            ))
          ) as node, null::jsonb as edge from si
        union all
        select jsonb_build_object(
          'id', 'sg_' || sg.sample_group_id,
          'entity', 'SampleGroup',
          'label', sample_group_name,
          'attrs', jsonb_strip_nulls(jsonb_build_object(
            -- 'name', sample_group_name
               'sampling_context', sampling_context,
               'dimensions', dimensions,
               'descriptions', descriptions,
               'positions', positions
          ))
        ), null::jsonb as edge from sg
        union all
        select jsonb_build_object(
          'id', 'ps_' || ps.physical_sample_id,
          'entity', 'Sample',
          'label', sample_name,
          'attrs', jsonb_strip_nulls(jsonb_build_object(
            -- 'name', sample_name,
            'type', sample_type,
            'horizon_name', horizon_name,
            'description', description,
            'alt_refs', alt_refs,
            'notes', notes
          ))
        ), null from ps
        union all
		    select jsonb_build_object(
            'id', 'sd_' || sample_dimension_id,
            'entity', 'Dimension',
            'label', "value",
            'attrs', jsonb_strip_nulls(jsonb_build_object(
              'dimension', dimension,
              'qualifier', qualifier,
              'description', description
            ))
          ), null from sd
		    union all
        select jsonb_build_object(
            'id', 'ae_' || ae.analysis_entity_id,
            'entity', 'Analysis',
            'label', ae.analysis_entity_id::text,
            'attrs', jsonb_build_object()
          ), null from ae
        union all
        select jsonb_build_object(
            'id', 'ds_' || ds.dataset_id,
            'entity', 'Dataset',
            'label', '',
            'attrs', jsonb_strip_nulls(jsonb_build_object(
              'name', dataset_name,
              'master_name', master_name,
              'data_type', data_type
            ))
			    ), null from ds
        union all
        select jsonb_build_object(
            'id', 'sl_' || sl.location_id,
            'entity', 'Location',
            'label', location_name,
            'attrs', jsonb_strip_nulls(jsonb_build_object(
              -- 'name', location_name,
              'type', location_type
            ))
          ), null from sl
        union all
        select jsonb_build_object(
            'id', 'f_' || f.feature_id,
            'entity', 'Feature',
            'label', feature_type_name,
            'attrs', jsonb_build_object(
              'name', feature_name
            )
          ), null from f
        union all
        select jsonb_build_object(
            'id', 'p_' || p.project_id,
            'entity', 'Project',
            'label', '',
            'attrs', jsonb_build_object(
              'project_name', project_name,
              'type', project_type_name
            )
          ), null from tbl_projects p
                  left join tbl_project_types pt using (project_type_id)
                  where project_id in (select project_id from p)
        union all
        select jsonb_build_object(
            'id', 'm_' || m.method_id,
            'entity', 'Method',
            'label', '',
            'attrs', jsonb_strip_nulls(jsonb_build_object(
              'name', method_name,
              'type', record_type
            ))
          ), null from m
        union all
        select jsonb_build_object(
              'id', 'b_' || b.biblio_id,
              'entity', 'Bibliography',
              'label', '',
              'attrs', jsonb_strip_nulls(jsonb_build_object(
                'citation', coalesce(citation, 'null')
              ))
          ), null from b
        union all
        select jsonb_build_object(
            'id', 'av_' || av.analysis_value_id,
            'entity', 'AnalysisValue',
            'label', coalesce(analysis_value, 'null'),
            'attrs', jsonb_strip_nulls(jsonb_build_object(
              -- 'analysis_value', coalesce(analysis_value, 'null')
              ))
			  ), null from av
        union all
        select jsonb_build_object(
            'id', 'vc_' || vc.value_class_id,
            'entity', 'ValueClass',
            'label', name,
            'attrs', jsonb_build_object(
              -- 'name', name,
              'value_type', value_type
            )
          ), null from vc
        union all -- Abundance / Taxon
        select jsonb_build_object(
            'id', 'tc_' || tc.abundance_id,
            'entity', 'TaxonCount',
            'label', tc.abundance_id::text,
            'attrs', jsonb_strip_nulls(jsonb_build_object(
              'count', tc."count",
              'identification_level', tc.identification_level,
              'modification', tc.modification
            ))
          ), null from tc
        union all -- Measured Value
        select jsonb_build_object(
            'id', 'mv_' || mv.measured_value_id,
            'entity', 'MeasuredValue',
            'label', measured_value,
            'attrs', jsonb_build_object(
            )
          ), null from mv
		    union all -- Dating
        select jsonb_build_object(
            'id', 'rd_' || rd.relative_date_id,
            'entity', 'Dating',
            'label', rd.dating::text,
            'attrs', jsonb_strip_nulls(jsonb_build_object(
              'age_name', relative_age_name,
			        'age_type', age_type
            ))
          ), null from rd
		    union all -- Geochronology
        select jsonb_build_object(
            'id', 'gc_' || geochron_id,
            'entity', 'Geochronology',
            'label', age::text,
            'attrs', jsonb_strip_nulls(jsonb_build_object(
              'error', error,
			        'lab_id', lab_id,
			        'lab_number', lab_number,
			        'notes', notes,
              'uncertainty', uncertainty
            ))
          ), null from gc
        union all -- Taxon
        select jsonb_build_object(
            'id', 'taxon_' || t.taxon_id,
            'entity', 'Taxon',
            'label', coalesce(species, 'taxon_' || t.taxon_id),
            'attrs', jsonb_strip_nulls(jsonb_build_object(
              'species', species,
              'genus', genus_name,
              'author', author_name,
              'family', family_name
            ))
          ), null from t
        /* edges */
        union all -- Sample Group to Site
        select null, jsonb_build_object('source', 'sg_' || sg.sample_group_id,'target', 'site_' || sg.site_id,'rel', 'belongs_to') from sg
        union all -- Sample to Sample Group
        select null, jsonb_build_object('source', 'ps_' || ps.physical_sample_id,'target', 'sg_' || ps.sample_group_id,'rel', 'in_group') from ps
        union all -- Analysis to Sample
        select null, jsonb_build_object('source', 'ae_' || ae.analysis_entity_id,'target', 'ps_' || ae.physical_sample_id,'rel', '') from ae
        union all -- Analysis to Dataset
        select null, jsonb_build_object('source', 'ae_' || ae.analysis_entity_id,'target', 'ds_' || ae.dataset_id,'rel', 'in') from ae
        union all -- Sample Dimension to Sample
        select null, jsonb_build_object('source', 'sd_' || sd.sample_dimension_id,'target', 'ps_' || sd.physical_sample_id,'rel', 'of_sample') from sd
        union all -- Sample Dimension to Method
        select null, jsonb_build_object('source', 'sd_' || sd.sample_dimension_id,'target', 'm_' || sd.method_id,'rel', 'measured_by') from sd
        union all -- Sample to Feature
        select null, jsonb_build_object('source', 'ps_' || f.physical_sample_id,'target', 'f_' || f.feature_id,'rel', 'has_feature') from f
        union all -- Dataset to Project
        select null, jsonb_build_object('source', 'ds_' || p.dataset_id,'target', 'p_' || p.project_id,'rel', 'belongs_to') from p
        union all -- Dataset to Method
        select null, jsonb_build_object('source', 'ds_' || ds.dataset_id,'target', 'm_' || ds.method_id,'rel', 'produced_by') from ds
        union all -- Sample Group Method to Method
        select null, jsonb_build_object('source', 'sg_' || sg.sample_group_id,'target', 'm_' || sg.method_id,'rel', 'uses_method') from sg
        union all -- Site to Publication
        select null, jsonb_build_object('source', 'site_' || site_id,'target', 'b_' || biblio_id,'rel', 'has_publication') from si_b
        union all -- Site to Location
        select null, jsonb_build_object('source', 'site_' || sl.site_id,'target', 'sl_' || sl.location_id,'rel', 'has_location') from sl
        union all -- Dataset to Publication
        select null, jsonb_build_object('source', 'ds_' || ds.dataset_id,'target', 'b_' || ds.biblio_id,'rel', 'has_publication') from ds
        union all -- Method to Publication
        select null, jsonb_build_object('source', 'm_' || m.method_id,'target', 'b_' || m.biblio_id,'rel', 'described_in') from m
        union all -- Sample Group to Publication
        select null, jsonb_build_object('source', 'sg_' || sample_group_id,'target', 'b_' || biblio_id,'rel', 'has_publication') from sg_b
        union all -- Sample Prep Method to Method
        select null, jsonb_build_object('source', 'ae_' || analysis_entity_id,'target', 'm_' || method_id,'rel', 'uses_prep_method') from aem
        union all -- Analysis Value to Analysis Entity
        select null, jsonb_build_object('source', 'av_' || analysis_value_id,'target', 'ae_' || analysis_entity_id,'rel', 'measured_in' ) from av
        union all -- Analysis Value to Value Class
        select null, jsonb_build_object('source', 'av_' || analysis_value_id,'target', 'vc_' || value_class_id,'rel', 'of_type' ) from av
        union all -- Analysis Entity to Taxon Count
        select null, jsonb_build_object('source', 'tc_' || abundance_id,'target', 'ae_' || analysis_entity_id,'rel', 'measured_in' ) from tc
        union all -- Analysis Entity to Measured Value
        select null, jsonb_build_object('source', 'mv_' || measured_value_id,'target', 'ae_' || analysis_entity_id,'rel', 'measured_in' ) from mv
        union all -- Analysis Entity to Dating
        select null, jsonb_build_object('source', 'rd_' || relative_date_id,'target', 'ae_' || analysis_entity_id,'rel', 'dated_in' ) from rd
        union all -- Analysis Entity to Geochronology
        select null, jsonb_build_object('source', 'gc_' || geochron_id, 'target', 'ae_' || analysis_entity_id,'rel', 'dated_in' ) from gc
        union all -- Taxon Count to Taxon
        select null, jsonb_build_object('source', 'tc_' || abundance_id,'target', 'taxon_' || taxon_id,'rel', 'of_taxon' ) from tc
      ) t(node, edge);
	return v_data;
end;
$_$;


alter function public.get_sample_graph(sample_id integer) owner to humlab_admin;

--
-- Name: table_dependency_levels(); Type: FUNCTION; Schema: public; Owner: sead_master
--

create function public.table_dependency_levels() returns table (schema_name text, table_name text, level integer)
language plpgsql
as $$
declare
	v_level int;
	v_count int;
begin

	drop table if exists table_level;
	drop view  if exists all_fks_aggs;
	drop view  if exists all_tables;
	drop view  if exists all_fks;

	create temporary view all_tables as (
		select s.nspname as schema_name, p.relname as table_name
		from pg_class p
		join pg_namespace s on s.oid = p.relnamespace
		where true
		  and p.relkind = 'r'
		  and s.nspname = 'public'
	);

	create temporary view all_fks as (
		select rs.nspname as schema_name, ref.relname as table_name, p.relname as referenced_table_name
		from pg_class ref
		join pg_namespace rs on rs.oid = ref.relnamespace
		join pg_constraint c on c.contype = 'f' and c.conrelid = ref.oid
		join pg_class p on p.oid = c.confrelid
		join pg_namespace s on s.oid = p.relnamespace
		where true
		  and rs.nspname = 'public'
		  and ref.relname <> p.relname
	);

	create temporary view all_fks_aggs as
		select table_name, array_agg(referenced_table_name) as referenced_table_names
		from all_fks
		group by table_name;

	create temporary table table_level as

		/* All tables with no dependendencies */
		select t.schema_name::text as schema_name, t.table_name::text as table_name, 0::int as level
		from all_tables t
		left join all_fks r
		  on t.schema_name = r.schema_name
		 and t.table_name = r.table_name
		where r.table_name is null;

	v_level = 0;

	loop

		v_level = v_level + 1;

		insert into table_level
			with processed_count as (
				select f.schema_name, f.table_name
				from all_fks f
				left join table_level x
				  on x.schema_name = f.schema_name
				 and x.table_name = f.referenced_table_name
				group by f.schema_name, f.table_name
				having count(f.referenced_table_name) = count(x.table_name)
			) select processed_count.schema_name, processed_count.table_name, v_level
			  from processed_count
			  left join table_level using (schema_name, table_name)
			  where table_level.table_name is null;


		get diagnostics v_count = row_count;

		exit when v_count = 0 or v_level = 10;

		-- raise notice '%', v_level;

	end loop;

	return query
		select t.schema_name, t.table_name, t.level
		from table_level t;

end $$;


alter function public.table_dependency_levels() owner to sead_master;

--
-- Name: whoami(); Type: FUNCTION; Schema: public; Owner: humlab_admin
--

create function public.whoami() returns table (user_name text, search_path text)
language plpgsql stable
as $$
begin
  return query
  select current_user::text, current_setting('search_path')::text;
end;
$$;


alter function public.whoami() owner to humlab_admin;

--
-- PostgreSQL database dump complete
--

\unrestrict t8vzGfeSUOgeKdezgypNIEKYe6p3YVep0icm3QiGYx4XxxeJIJs0yw4Z3KNhBaG
