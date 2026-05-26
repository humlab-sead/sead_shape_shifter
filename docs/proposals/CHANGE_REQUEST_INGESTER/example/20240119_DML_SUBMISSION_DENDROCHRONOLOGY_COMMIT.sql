-- Deploy dendrochronology: 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT
/***************************************************************************
  Author         Roger Mähler
  Date           
  Description    New building data from Lund Dendrochronology lab
  Issue          https://github.com/humlab-sead/sead_change_control/issues/218
  Prerequisites  
  Reviewer
  Approver
  Idempotent     NO
  Notes          Use --single-transaction on execute!
***************************************************************************/
set client_encoding = 'UTF8';
set client_min_messages to warning;
\set autocommit off;

do $$
begin
    perform sead_utility.set_fk_is_deferrable('public', true, false);
end $$ language plpgsql;

begin;
set constraints all deferred;
\cd /repo/dendrochronology/deploy

\o /dev/null
call clearing_house_commit.reset_public_sequence_ids();
\o

/************************************************************************************************************************************
 ** project
 ************************************************************************************************************************************/

drop table if exists clearing_house_commit.temp_tbl_projects;
create table clearing_house_commit.temp_tbl_projects as select project_id, project_type_id, project_stage_id, project_name, project_abbrev_name, description, date_updated from public.tbl_projects where FALSE;

\copy clearing_house_commit.temp_tbl_projects (project_id, project_type_id, project_stage_id, project_name, project_abbrev_name, description, date_updated) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/project.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_projects (project_id, project_type_id, project_stage_id, project_name, project_abbrev_name, description, date_updated)
    select project_id, project_type_id, project_stage_id, project_name, project_abbrev_name, description, date_updated
    from clearing_house_commit.temp_tbl_projects ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_projects;



/************************************************************************************************************************************
 ** dataset
 ************************************************************************************************************************************/

drop table if exists clearing_house_commit.temp_tbl_datasets;
create table clearing_house_commit.temp_tbl_datasets as select dataset_id, master_set_id, data_type_id, method_id, biblio_id, updated_dataset_id, project_id, dataset_name, date_updated from public.tbl_datasets where FALSE;

\copy clearing_house_commit.temp_tbl_datasets (dataset_id, master_set_id, data_type_id, method_id, biblio_id, updated_dataset_id, project_id, dataset_name, date_updated) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/dataset.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_datasets (dataset_id, master_set_id, data_type_id, method_id, biblio_id, updated_dataset_id, project_id, dataset_name, date_updated)
    select dataset_id, master_set_id, data_type_id, method_id, biblio_id, updated_dataset_id, project_id, dataset_name, date_updated
    from clearing_house_commit.temp_tbl_datasets ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_datasets;



/************************************************************************************************************************************
 ** dataset_contact
 ************************************************************************************************************************************/

drop table if exists clearing_house_commit.temp_tbl_dataset_contacts;
create table clearing_house_commit.temp_tbl_dataset_contacts as select dataset_contact_id, contact_id, contact_type_id, dataset_id, date_updated from public.tbl_dataset_contacts where FALSE;

\copy clearing_house_commit.temp_tbl_dataset_contacts (dataset_contact_id, contact_id, contact_type_id, dataset_id, date_updated) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/dataset_contact.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_dataset_contacts (dataset_contact_id, contact_id, contact_type_id, dataset_id, date_updated)
    select dataset_contact_id, contact_id, contact_type_id, dataset_id, date_updated
    from clearing_house_commit.temp_tbl_dataset_contacts ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_dataset_contacts;



/************************************************************************************************************************************
 ** dataset_submission
 ************************************************************************************************************************************/

drop table if exists clearing_house_commit.temp_tbl_dataset_submissions;
create table clearing_house_commit.temp_tbl_dataset_submissions as select dataset_submission_id, dataset_id, submission_type_id, contact_id, date_submitted, notes, date_updated from public.tbl_dataset_submissions where FALSE;

\copy clearing_house_commit.temp_tbl_dataset_submissions (dataset_submission_id, dataset_id, submission_type_id, contact_id, date_submitted, notes, date_updated) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/dataset_submission.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_dataset_submissions (dataset_submission_id, dataset_id, submission_type_id, contact_id, date_submitted, notes, date_updated)
    select dataset_submission_id, dataset_id, submission_type_id, contact_id, date_submitted, notes, date_updated
    from clearing_house_commit.temp_tbl_dataset_submissions ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_dataset_submissions;



/************************************************************************************************************************************
 ** abundance
 ************************************************************************************************************************************/

drop table if exists clearing_house_commit.temp_tbl_abundances;
create table clearing_house_commit.temp_tbl_abundances as select abundance_id, taxon_id, analysis_entity_id, abundance_element_id, abundance, date_updated from public.tbl_abundances where FALSE;

\copy clearing_house_commit.temp_tbl_abundances (abundance_id, taxon_id, analysis_entity_id, abundance_element_id, abundance, date_updated) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/abundance.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_abundances (abundance_id, taxon_id, analysis_entity_id, abundance_element_id, abundance, date_updated)
    select abundance_id, taxon_id, analysis_entity_id, abundance_element_id, abundance, date_updated
    from clearing_house_commit.temp_tbl_abundances ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_abundances;



/************************************************************************************************************************************
 ** analysis_entity
 ************************************************************************************************************************************/

drop table if exists clearing_house_commit.temp_tbl_analysis_entities;
create table clearing_house_commit.temp_tbl_analysis_entities as select analysis_entity_id, physical_sample_id, dataset_id, date_updated from public.tbl_analysis_entities where FALSE;

\copy clearing_house_commit.temp_tbl_analysis_entities (analysis_entity_id, physical_sample_id, dataset_id, date_updated) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/analysis_entity.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_analysis_entities (analysis_entity_id, physical_sample_id, dataset_id, date_updated)
    select analysis_entity_id, physical_sample_id, dataset_id, date_updated
    from clearing_house_commit.temp_tbl_analysis_entities ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_analysis_entities;



/************************************************************************************************************************************
 ** dendro
 ************************************************************************************************************************************/


drop table if exists clearing_house_commit.temp_tbl_dendro;
create table clearing_house_commit.temp_tbl_dendro as select dendro_id, analysis_entity_id, measurement_value, date_updated, dendro_lookup_id from public.tbl_dendro where FALSE;

\copy clearing_house_commit.temp_tbl_dendro (dendro_id, analysis_entity_id, measurement_value, date_updated, dendro_lookup_id) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/dendro.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_dendro (dendro_id, analysis_entity_id, measurement_value, date_updated, dendro_lookup_id)
    select dendro_id, analysis_entity_id, measurement_value, date_updated, dendro_lookup_id
    from clearing_house_commit.temp_tbl_dendro ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_dendro;



/************************************************************************************************************************************
 ** dendro_date_note
 ************************************************************************************************************************************/


drop table if exists clearing_house_commit.temp_tbl_dendro_date_notes;
create table clearing_house_commit.temp_tbl_dendro_date_notes as select dendro_date_note_id, dendro_date_id, note, date_updated from public.tbl_dendro_date_notes where FALSE;

\copy clearing_house_commit.temp_tbl_dendro_date_notes (dendro_date_note_id, dendro_date_id, note, date_updated) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/dendro_date_note.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_dendro_date_notes (dendro_date_note_id, dendro_date_id, note, date_updated)
    select dendro_date_note_id, dendro_date_id, note, date_updated
    from clearing_house_commit.temp_tbl_dendro_date_notes ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_dendro_date_notes;



/************************************************************************************************************************************
 ** dendro_date
 ************************************************************************************************************************************/



drop table if exists clearing_house_commit.temp_tbl_dendro_dates;
create table clearing_house_commit.temp_tbl_dendro_dates as
    select dendro_date_id, season_id, dating_uncertainty_id, dendro_lookup_id, age_type_id, analysis_entity_id, age_older, age_younger, date_updated
    from public.tbl_dendro_dates where FALSE;

\copy clearing_house_commit.temp_tbl_dendro_dates (dendro_date_id, season_id, dating_uncertainty_id, dendro_lookup_id, age_type_id, analysis_entity_id, age_older, age_younger, date_updated) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/dendro_date.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_dendro_dates (dendro_date_id, season_id, dating_uncertainty_id, dendro_lookup_id, age_type_id, analysis_entity_id, age_older, age_younger, date_updated)
    select dendro_date_id, season_id, dating_uncertainty_id, dendro_lookup_id, age_type_id, analysis_entity_id, age_older, age_younger, date_updated
    from clearing_house_commit.temp_tbl_dendro_dates
    /* on conflict (v_pk_name) update set list-of-all-fields */;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_dendro_dates;



/************************************************************************************************************************************
 ** physical_sample
 ************************************************************************************************************************************/

drop table if exists clearing_house_commit.temp_tbl_physical_samples;
create table clearing_house_commit.temp_tbl_physical_samples as select physical_sample_id, sample_group_id, alt_ref_type_id, sample_type_id, sample_name, date_updated, date_sampled from public.tbl_physical_samples where FALSE;

\copy clearing_house_commit.temp_tbl_physical_samples (physical_sample_id, sample_group_id, alt_ref_type_id, sample_type_id, sample_name, date_updated, date_sampled) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/physical_sample.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_physical_samples (physical_sample_id, sample_group_id, alt_ref_type_id, sample_type_id, sample_name, date_updated, date_sampled)
    select physical_sample_id, sample_group_id, alt_ref_type_id, sample_type_id, sample_name, date_updated, date_sampled
    from clearing_house_commit.temp_tbl_physical_samples ;


\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_physical_samples;



/************************************************************************************************************************************
 ** sample_alt_ref
 ************************************************************************************************************************************/


drop table if exists clearing_house_commit.temp_tbl_sample_alt_refs;
create table clearing_house_commit.temp_tbl_sample_alt_refs as select sample_alt_ref_id, alt_ref, alt_ref_type_id, date_updated, physical_sample_id from public.tbl_sample_alt_refs where FALSE;

\copy clearing_house_commit.temp_tbl_sample_alt_refs (sample_alt_ref_id, alt_ref, alt_ref_type_id, date_updated, physical_sample_id) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/sample_alt_ref.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_sample_alt_refs (sample_alt_ref_id, alt_ref, alt_ref_type_id, date_updated, physical_sample_id)
    select sample_alt_ref_id, alt_ref, alt_ref_type_id, date_updated, physical_sample_id
    from clearing_house_commit.temp_tbl_sample_alt_refs ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_sample_alt_refs;



/************************************************************************************************************************************
 ** sample_description
 ************************************************************************************************************************************/


drop table if exists clearing_house_commit.temp_tbl_sample_descriptions;
create table clearing_house_commit.temp_tbl_sample_descriptions as select sample_description_id, sample_description_type_id, physical_sample_id, description, date_updated from public.tbl_sample_descriptions where FALSE;

\copy clearing_house_commit.temp_tbl_sample_descriptions (sample_description_id, sample_description_type_id, physical_sample_id, description, date_updated)from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/sample_description.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_sample_descriptions (sample_description_id, sample_description_type_id, physical_sample_id, description, date_updated)
    select sample_description_id, sample_description_type_id, physical_sample_id, description, date_updated
    from clearing_house_commit.temp_tbl_sample_descriptions ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_sample_descriptions;



/************************************************************************************************************************************
 ** sample_group_coordinate
 ************************************************************************************************************************************/


drop table if exists clearing_house_commit.temp_tbl_sample_group_coordinates;
create table clearing_house_commit.temp_tbl_sample_group_coordinates as select sample_group_position_id, coordinate_method_dimension_id, sample_group_position, position_accuracy, sample_group_id, date_updated from public.tbl_sample_group_coordinates where FALSE;

\copy clearing_house_commit.temp_tbl_sample_group_coordinates (sample_group_position_id, coordinate_method_dimension_id, sample_group_position, position_accuracy, sample_group_id, date_updated) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/sample_group_coordinate.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_sample_group_coordinates (sample_group_position_id, coordinate_method_dimension_id, sample_group_position, position_accuracy, sample_group_id, date_updated)
    select sample_group_position_id, coordinate_method_dimension_id, sample_group_position, position_accuracy, sample_group_id, date_updated
    from clearing_house_commit.temp_tbl_sample_group_coordinates ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_sample_group_coordinates;



/************************************************************************************************************************************
 ** sample_group_description
 ************************************************************************************************************************************/


drop table if exists clearing_house_commit.temp_tbl_sample_group_descriptions;
create table clearing_house_commit.temp_tbl_sample_group_descriptions as select sample_group_description_id, group_description, sample_group_description_type_id, date_updated, sample_group_id from public.tbl_sample_group_descriptions where FALSE;

\copy clearing_house_commit.temp_tbl_sample_group_descriptions (sample_group_description_id, group_description, sample_group_description_type_id, date_updated, sample_group_id) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/sample_group_description.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_sample_group_descriptions (sample_group_description_id, group_description, sample_group_description_type_id, date_updated, sample_group_id)
    select sample_group_description_id, group_description, sample_group_description_type_id, date_updated, sample_group_id
    from clearing_house_commit.temp_tbl_sample_group_descriptions ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_sample_group_descriptions;



/************************************************************************************************************************************
 ** sample_group_note
 ************************************************************************************************************************************/


drop table if exists clearing_house_commit.temp_tbl_sample_group_notes;
create table clearing_house_commit.temp_tbl_sample_group_notes as select sample_group_note_id, sample_group_id, note, date_updated from public.tbl_sample_group_notes where FALSE;

\copy clearing_house_commit.temp_tbl_sample_group_notes (sample_group_note_id, sample_group_id, note, date_updated) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/sample_group_note.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_sample_group_notes (sample_group_note_id, sample_group_id, note, date_updated)
    select sample_group_note_id, sample_group_id, note, date_updated
    from clearing_house_commit.temp_tbl_sample_group_notes ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_sample_group_notes;



/************************************************************************************************************************************
 ** sample_group
 ************************************************************************************************************************************/


drop table if exists clearing_house_commit.temp_tbl_sample_groups;
create table clearing_house_commit.temp_tbl_sample_groups as select sample_group_id, site_id, sampling_context_id, method_id, sample_group_name, sample_group_description, date_updated from public.tbl_sample_groups where FALSE;

\copy clearing_house_commit.temp_tbl_sample_groups (sample_group_id, site_id, sampling_context_id, method_id, sample_group_name, sample_group_description, date_updated) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/sample_group.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_sample_groups (sample_group_id, site_id, sampling_context_id, method_id, sample_group_name, sample_group_description, date_updated)
    select sample_group_id, site_id, sampling_context_id, method_id, sample_group_name, sample_group_description, date_updated
    from clearing_house_commit.temp_tbl_sample_groups ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_sample_groups;



/************************************************************************************************************************************
 ** sample_location
 ************************************************************************************************************************************/


drop table if exists clearing_house_commit.temp_tbl_sample_locations;
create table clearing_house_commit.temp_tbl_sample_locations as select sample_location_id, sample_location_type_id, physical_sample_id, location, date_updated from public.tbl_sample_locations where FALSE;

\copy clearing_house_commit.temp_tbl_sample_locations (sample_location_id, sample_location_type_id, physical_sample_id, location, date_updated) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/sample_location.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_sample_locations (sample_location_id, sample_location_type_id, physical_sample_id, location, date_updated)
    select sample_location_id, sample_location_type_id, physical_sample_id, location, date_updated
    from clearing_house_commit.temp_tbl_sample_locations ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_sample_locations;



/************************************************************************************************************************************
 ** sample_note
 ************************************************************************************************************************************/


drop table if exists clearing_house_commit.temp_tbl_sample_notes;
create table clearing_house_commit.temp_tbl_sample_notes as select sample_note_id, physical_sample_id, note_type, note, date_updated from public.tbl_sample_notes where FALSE;

\copy clearing_house_commit.temp_tbl_sample_notes (sample_note_id, physical_sample_id, note_type, note, date_updated) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/sample_note.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_sample_notes (sample_note_id, physical_sample_id, note_type, note, date_updated)
    select sample_note_id, physical_sample_id, note_type, note, date_updated
    from clearing_house_commit.temp_tbl_sample_notes ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_sample_notes;



/************************************************************************************************************************************
 ** site_location
 ************************************************************************************************************************************/

drop table if exists clearing_house_commit.temp_tbl_site_locations;
create table clearing_house_commit.temp_tbl_site_locations as select site_location_id, date_updated, location_id, site_id from public.tbl_site_locations where FALSE;

\copy clearing_house_commit.temp_tbl_site_locations (site_location_id, date_updated, location_id, site_id) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/site_location.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_site_locations (site_location_id, date_updated, location_id, site_id)
    select site_location_id, date_updated, location_id, site_id
    from clearing_house_commit.temp_tbl_site_locations ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_site_locations;



/************************************************************************************************************************************
 ** site_reference
 ************************************************************************************************************************************/

drop table if exists clearing_house_commit.temp_tbl_site_references;
create table clearing_house_commit.temp_tbl_site_references as select site_reference_id, site_id, biblio_id, date_updated from public.tbl_site_references where FALSE;

\copy clearing_house_commit.temp_tbl_site_references (site_reference_id, site_id, biblio_id, date_updated) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/site_reference.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_site_references (site_reference_id, site_id, biblio_id, date_updated)
    select site_reference_id, site_id, biblio_id, date_updated
    from clearing_house_commit.temp_tbl_site_references ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_site_references;



/************************************************************************************************************************************
 ** site
 ************************************************************************************************************************************/

drop table if exists clearing_house_commit.temp_tbl_sites;
create table clearing_house_commit.temp_tbl_sites as select site_id, altitude, latitude_dd, longitude_dd, national_site_identifier, site_description, site_name, site_preservation_status_id, date_updated, site_location_accuracy from public.tbl_sites where FALSE;

\copy clearing_house_commit.temp_tbl_sites (site_id, altitude, latitude_dd, longitude_dd, national_site_identifier, site_description, site_name, site_preservation_status_id, date_updated, site_location_accuracy) from program 'zcat -qac 20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT/site.gz' with (FORMAT text, DELIMITER E'\t', ENCODING 'utf-8');


insert into public.tbl_sites (site_id, altitude, latitude_dd, longitude_dd, national_site_identifier, site_description, site_name, site_preservation_status_id, site_location_accuracy, date_updated)
    select site_id, altitude, latitude_dd, longitude_dd, national_site_identifier, site_description, site_name, site_preservation_status_id, site_location_accuracy, date_updated
    from clearing_house_commit.temp_tbl_sites ;

\o /dev/null

drop table if exists clearing_house_commit.temp_tbl_sites;


\o /dev/null
call clearing_house_commit.reset_public_sequence_ids();
select clearing_house_commit.commit_submission('20240119_DML_SUBMISSION_DENDROCHRONOLOGY_COMMIT');
\o
commit;

do $$
begin
    perform sead_utility.set_fk_is_deferrable('public', false, false);
    perform sead_utility.sync_sequences('public');
    perform sead_utility.sync_sequences('bugs_import');
    
end $$ language plpgsql;
