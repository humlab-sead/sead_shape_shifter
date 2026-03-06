create sequence public.tbl_abundance_elements_abundance_element_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_abundance_elements_abundance_element_id_seq owner to sead_master;
alter sequence public.tbl_abundance_elements_abundance_element_id_seq owned by public.tbl_abundance_elements.abundance_element_id;

create sequence public.tbl_abundance_ident_levels_abundance_ident_level_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_abundance_ident_levels_abundance_ident_level_id_seq owner to sead_master;
alter sequence public.tbl_abundance_ident_levels_abundance_ident_level_id_seq owned by public.tbl_abundance_ident_levels.abundance_ident_level_id;

create sequence public.tbl_abundance_modifications_abundance_modification_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_abundance_modifications_abundance_modification_id_seq owner to sead_master;
alter sequence public.tbl_abundance_modifications_abundance_modification_id_seq owned by public.tbl_abundance_modifications.abundance_modification_id;

create sequence public.tbl_abundance_properties_abundance_property_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_abundance_properties_abundance_property_id_seq owner to humlab_admin;
alter sequence public.tbl_abundance_properties_abundance_property_id_seq owned by public.tbl_abundance_properties.abundance_property_id;

create sequence public.tbl_abundances_abundance_id_seq
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_abundances_abundance_id_seq owner to sead_master;
alter sequence public.tbl_abundances_abundance_id_seq owned by public.tbl_abundances.abundance_id;

create sequence public.tbl_activity_types_activity_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_activity_types_activity_type_id_seq owner to sead_master;
alter sequence public.tbl_activity_types_activity_type_id_seq owned by public.tbl_activity_types.activity_type_id;

create sequence public.tbl_age_types_age_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_age_types_age_type_id_seq owner to sead_master;
alter sequence public.tbl_age_types_age_type_id_seq owned by public.tbl_age_types.age_type_id;

create sequence public.tbl_aggregate_datasets_aggregate_dataset_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_aggregate_datasets_aggregate_dataset_id_seq owner to sead_master;
alter sequence public.tbl_aggregate_datasets_aggregate_dataset_id_seq owned by public.tbl_aggregate_datasets.aggregate_dataset_id;

create sequence public.tbl_aggregate_order_types_aggregate_order_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_aggregate_order_types_aggregate_order_type_id_seq owner to sead_master;
alter sequence public.tbl_aggregate_order_types_aggregate_order_type_id_seq owned by public.tbl_aggregate_order_types.aggregate_order_type_id;

create sequence public.tbl_aggregate_sample_ages_aggregate_sample_age_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_aggregate_sample_ages_aggregate_sample_age_id_seq owner to sead_master;
alter sequence public.tbl_aggregate_sample_ages_aggregate_sample_age_id_seq owned by public.tbl_aggregate_sample_ages.aggregate_sample_age_id;

create sequence public.tbl_aggregate_samples_aggregate_sample_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_aggregate_samples_aggregate_sample_id_seq owner to sead_master;
alter sequence public.tbl_aggregate_samples_aggregate_sample_id_seq owned by public.tbl_aggregate_samples.aggregate_sample_id;

create sequence public.tbl_alt_ref_types_alt_ref_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_alt_ref_types_alt_ref_type_id_seq owner to sead_master;
alter sequence public.tbl_alt_ref_types_alt_ref_type_id_seq owned by public.tbl_alt_ref_types.alt_ref_type_id;

create sequence public.tbl_analysis_boolean_values_analysis_boolean_value_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_analysis_boolean_values_analysis_boolean_value_id_seq owner to sead_master;
alter sequence public.tbl_analysis_boolean_values_analysis_boolean_value_id_seq owned by public.tbl_analysis_boolean_values.analysis_boolean_value_id;

create sequence public.tbl_analysis_categorical_valu_analysis_categorical_value_id_seq
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_analysis_categorical_valu_analysis_categorical_value_id_seq owner to sead_master;
alter sequence public.tbl_analysis_categorical_valu_analysis_categorical_value_id_seq owned by public.tbl_analysis_categorical_values.analysis_categorical_value_id;

create sequence public.tbl_analysis_dating_ranges_analysis_dating_range_id_seq
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_analysis_dating_ranges_analysis_dating_range_id_seq owner to sead_master;
alter sequence public.tbl_analysis_dating_ranges_analysis_dating_range_id_seq owned by public.tbl_analysis_dating_ranges.analysis_dating_range_id;

create sequence public.tbl_analysis_entities_analysis_entity_id_seq
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_analysis_entities_analysis_entity_id_seq owner to sead_master;
alter sequence public.tbl_analysis_entities_analysis_entity_id_seq owned by public.tbl_analysis_entities.analysis_entity_id;

create sequence public.tbl_analysis_entity_ages_analysis_entity_age_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_analysis_entity_ages_analysis_entity_age_id_seq owner to sead_master;
alter sequence public.tbl_analysis_entity_ages_analysis_entity_age_id_seq owned by public.tbl_analysis_entity_ages.analysis_entity_age_id;

create sequence public.tbl_analysis_entity_dimensions_analysis_entity_dimension_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_analysis_entity_dimensions_analysis_entity_dimension_id_seq owner to sead_master;
alter sequence public.tbl_analysis_entity_dimensions_analysis_entity_dimension_id_seq owned by public.tbl_analysis_entity_dimensions.analysis_entity_dimension_id;

create sequence public.tbl_analysis_entity_prep_meth_analysis_entity_prep_method_i_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_analysis_entity_prep_meth_analysis_entity_prep_method_i_seq owner to sead_master;
alter sequence public.tbl_analysis_entity_prep_meth_analysis_entity_prep_method_i_seq owned by public.tbl_analysis_entity_prep_methods.analysis_entity_prep_method_id;

create sequence public.tbl_analysis_identifiers_analysis_identifier_id_seq
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_analysis_identifiers_analysis_identifier_id_seq owner to sead_master;
alter sequence public.tbl_analysis_identifiers_analysis_identifier_id_seq owned by public.tbl_analysis_identifiers.analysis_identifier_id;

create sequence public.tbl_analysis_integer_ranges_analysis_integer_range_id_seq
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_analysis_integer_ranges_analysis_integer_range_id_seq owner to sead_master;
alter sequence public.tbl_analysis_integer_ranges_analysis_integer_range_id_seq owned by public.tbl_analysis_integer_ranges.analysis_integer_range_id;

create sequence public.tbl_analysis_integer_values_analysis_integer_value_id_seq
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_analysis_integer_values_analysis_integer_value_id_seq owner to sead_master;
alter sequence public.tbl_analysis_integer_values_analysis_integer_value_id_seq owned by public.tbl_analysis_integer_values.analysis_integer_value_id;

create sequence public.tbl_analysis_notes_analysis_note_id_seq
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_analysis_notes_analysis_note_id_seq owner to sead_master;
alter sequence public.tbl_analysis_notes_analysis_note_id_seq owned by public.tbl_analysis_notes.analysis_note_id;

create sequence public.tbl_analysis_numerical_ranges_analysis_numerical_range_id_seq
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_analysis_numerical_ranges_analysis_numerical_range_id_seq owner to sead_master;
alter sequence public.tbl_analysis_numerical_ranges_analysis_numerical_range_id_seq owned by public.tbl_analysis_numerical_ranges.analysis_numerical_range_id;

create sequence public.tbl_analysis_numerical_values_analysis_numerical_value_id_seq
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_analysis_numerical_values_analysis_numerical_value_id_seq owner to sead_master;
alter sequence public.tbl_analysis_numerical_values_analysis_numerical_value_id_seq owned by public.tbl_analysis_numerical_values.analysis_numerical_value_id;

create sequence public.tbl_analysis_taxon_counts_analysis_taxon_count_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_analysis_taxon_counts_analysis_taxon_count_id_seq owner to sead_master;
alter sequence public.tbl_analysis_taxon_counts_analysis_taxon_count_id_seq owned by public.tbl_analysis_taxon_counts.analysis_taxon_count_id;

create sequence public.tbl_analysis_value_dimensions_analysis_value_dimension_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_analysis_value_dimensions_analysis_value_dimension_id_seq owner to sead_master;
alter sequence public.tbl_analysis_value_dimensions_analysis_value_dimension_id_seq owned by public.tbl_analysis_value_dimensions.analysis_value_dimension_id;

create sequence public.tbl_analysis_values_analysis_value_id_seq
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_analysis_values_analysis_value_id_seq owner to sead_master;
alter sequence public.tbl_analysis_values_analysis_value_id_seq owned by public.tbl_analysis_values.analysis_value_id;

create sequence public.tbl_biblio_biblio_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_biblio_biblio_id_seq owner to sead_master;
alter sequence public.tbl_biblio_biblio_id_seq owned by public.tbl_biblio.biblio_id;

create sequence public.tbl_ceramics_ceramics_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_ceramics_ceramics_id_seq owner to sead_master;
alter sequence public.tbl_ceramics_ceramics_id_seq owned by public.tbl_ceramics.ceramics_id;

create sequence public.tbl_ceramics_lookup_ceramics_lookup_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_ceramics_lookup_ceramics_lookup_id_seq owner to sead_master;
alter sequence public.tbl_ceramics_lookup_ceramics_lookup_id_seq owned by public.tbl_ceramics_lookup.ceramics_lookup_id;

create sequence public.tbl_ceramics_measurements_ceramics_measurement_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_ceramics_measurements_ceramics_measurement_id_seq owner to sead_master;
alter sequence public.tbl_ceramics_measurements_ceramics_measurement_id_seq owned by public.tbl_ceramics_measurements.ceramics_measurement_id;

create sequence public.tbl_chronologies_chronology_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_chronologies_chronology_id_seq owner to sead_master;
alter sequence public.tbl_chronologies_chronology_id_seq owned by public.tbl_chronologies.chronology_id;

create sequence public.tbl_colours_colour_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_colours_colour_id_seq owner to sead_master;
alter sequence public.tbl_colours_colour_id_seq owned by public.tbl_colours.colour_id;

create sequence public.tbl_contact_types_contact_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_contact_types_contact_type_id_seq owner to sead_master;
alter sequence public.tbl_contact_types_contact_type_id_seq owned by public.tbl_contact_types.contact_type_id;

create sequence public.tbl_contacts_contact_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_contacts_contact_id_seq owner to sead_master;
alter sequence public.tbl_contacts_contact_id_seq owned by public.tbl_contacts.contact_id;

create sequence public.tbl_coordinate_method_dimensi_coordinate_method_dimension_i_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_coordinate_method_dimensi_coordinate_method_dimension_i_seq owner to sead_master;
alter sequence public.tbl_coordinate_method_dimensi_coordinate_method_dimension_i_seq owned by public.tbl_coordinate_method_dimensions.coordinate_method_dimension_id;

create sequence public.tbl_data_type_groups_data_type_group_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_data_type_groups_data_type_group_id_seq owner to sead_master;
alter sequence public.tbl_data_type_groups_data_type_group_id_seq owned by public.tbl_data_type_groups.data_type_group_id;

create sequence public.tbl_data_types_data_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_data_types_data_type_id_seq owner to sead_master;
alter sequence public.tbl_data_types_data_type_id_seq owned by public.tbl_data_types.data_type_id;

create sequence public.tbl_dataset_contacts_dataset_contact_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_dataset_contacts_dataset_contact_id_seq owner to sead_master;
alter sequence public.tbl_dataset_contacts_dataset_contact_id_seq owned by public.tbl_dataset_contacts.dataset_contact_id;

create sequence public.tbl_dataset_masters_master_set_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_dataset_masters_master_set_id_seq owner to sead_master;
alter sequence public.tbl_dataset_masters_master_set_id_seq owned by public.tbl_dataset_masters.master_set_id;

create sequence public.tbl_dataset_methods_dataset_method_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_dataset_methods_dataset_method_id_seq owner to sead_master;
alter sequence public.tbl_dataset_methods_dataset_method_id_seq owned by public.tbl_dataset_methods.dataset_method_id;

create sequence public.tbl_dataset_submission_types_submission_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_dataset_submission_types_submission_type_id_seq owner to sead_master;
alter sequence public.tbl_dataset_submission_types_submission_type_id_seq owned by public.tbl_dataset_submission_types.submission_type_id;

create sequence public.tbl_dataset_submissions_dataset_submission_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_dataset_submissions_dataset_submission_id_seq owner to sead_master;
alter sequence public.tbl_dataset_submissions_dataset_submission_id_seq owned by public.tbl_dataset_submissions.dataset_submission_id;

create sequence public.tbl_datasets_dataset_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_datasets_dataset_id_seq owner to sead_master;
alter sequence public.tbl_datasets_dataset_id_seq owned by public.tbl_datasets.dataset_id;

create sequence public.tbl_dating_labs_dating_lab_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_dating_labs_dating_lab_id_seq owner to sead_master;
alter sequence public.tbl_dating_labs_dating_lab_id_seq owned by public.tbl_dating_labs.dating_lab_id;

create sequence public.tbl_dating_material_dating_material_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_dating_material_dating_material_id_seq owner to sead_master;
alter sequence public.tbl_dating_material_dating_material_id_seq owned by public.tbl_dating_material.dating_material_id;

create sequence public.tbl_dating_uncertainty_dating_uncertainty_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_dating_uncertainty_dating_uncertainty_id_seq owner to sead_master;
alter sequence public.tbl_dating_uncertainty_dating_uncertainty_id_seq owned by public.tbl_dating_uncertainty.dating_uncertainty_id;

create sequence public.tbl_dendro_date_notes_dendro_date_note_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_dendro_date_notes_dendro_date_note_id_seq owner to sead_master;
alter sequence public.tbl_dendro_date_notes_dendro_date_note_id_seq owned by public.tbl_dendro_date_notes.dendro_date_note_id;

create sequence public.tbl_dendro_dates_dendro_date_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_dendro_dates_dendro_date_id_seq owner to sead_master;
alter sequence public.tbl_dendro_dates_dendro_date_id_seq owned by public.tbl_dendro_dates.dendro_date_id;

create sequence public.tbl_dendro_dendro_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_dendro_dendro_id_seq owner to sead_master;
alter sequence public.tbl_dendro_dendro_id_seq owned by public.tbl_dendro.dendro_id;

create sequence public.tbl_dendro_lookup_dendro_lookup_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_dendro_lookup_dendro_lookup_id_seq owner to sead_master;
alter sequence public.tbl_dendro_lookup_dendro_lookup_id_seq owned by public.tbl_dendro_lookup.dendro_lookup_id;

create sequence public.tbl_dimensions_dimension_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_dimensions_dimension_id_seq owner to sead_master;
alter sequence public.tbl_dimensions_dimension_id_seq owned by public.tbl_dimensions.dimension_id;

create sequence public.tbl_ecocode_definitions_ecocode_definition_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_ecocode_definitions_ecocode_definition_id_seq owner to sead_master;
alter sequence public.tbl_ecocode_definitions_ecocode_definition_id_seq owned by public.tbl_ecocode_definitions.ecocode_definition_id;

create sequence public.tbl_ecocode_groups_ecocode_group_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_ecocode_groups_ecocode_group_id_seq owner to sead_master;
alter sequence public.tbl_ecocode_groups_ecocode_group_id_seq owned by public.tbl_ecocode_groups.ecocode_group_id;

create sequence public.tbl_ecocode_systems_ecocode_system_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_ecocode_systems_ecocode_system_id_seq owner to sead_master;
alter sequence public.tbl_ecocode_systems_ecocode_system_id_seq owned by public.tbl_ecocode_systems.ecocode_system_id;

create sequence public.tbl_ecocodes_ecocode_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_ecocodes_ecocode_id_seq owner to sead_master;
alter sequence public.tbl_ecocodes_ecocode_id_seq owned by public.tbl_ecocodes.ecocode_id;

create sequence public.tbl_feature_types_feature_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_feature_types_feature_type_id_seq owner to sead_master;
alter sequence public.tbl_feature_types_feature_type_id_seq owned by public.tbl_feature_types.feature_type_id;

create sequence public.tbl_features_feature_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_features_feature_id_seq owner to sead_master;
alter sequence public.tbl_features_feature_id_seq owned by public.tbl_features.feature_id;

create sequence public.tbl_geochron_refs_geochron_ref_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_geochron_refs_geochron_ref_id_seq owner to sead_master;
alter sequence public.tbl_geochron_refs_geochron_ref_id_seq owned by public.tbl_geochron_refs.geochron_ref_id;

create sequence public.tbl_geochronology_geochron_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_geochronology_geochron_id_seq owner to sead_master;
alter sequence public.tbl_geochronology_geochron_id_seq owned by public.tbl_geochronology.geochron_id;

create sequence public.tbl_horizons_horizon_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_horizons_horizon_id_seq owner to sead_master;
alter sequence public.tbl_horizons_horizon_id_seq owned by public.tbl_horizons.horizon_id;

create sequence public.tbl_identification_levels_identification_level_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_identification_levels_identification_level_id_seq owner to sead_master;
alter sequence public.tbl_identification_levels_identification_level_id_seq owned by public.tbl_identification_levels.identification_level_id;

create sequence public.tbl_image_types_image_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_image_types_image_type_id_seq owner to sead_master;
alter sequence public.tbl_image_types_image_type_id_seq owned by public.tbl_image_types.image_type_id;

create sequence public.tbl_imported_taxa_replacements_imported_taxa_replacement_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_imported_taxa_replacements_imported_taxa_replacement_id_seq owner to sead_master;
alter sequence public.tbl_imported_taxa_replacements_imported_taxa_replacement_id_seq owned by public.tbl_imported_taxa_replacements.imported_taxa_replacement_id;

create sequence public.tbl_isotope_measurements_isotope_measurement_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_isotope_measurements_isotope_measurement_id_seq owner to sead_master;
alter sequence public.tbl_isotope_measurements_isotope_measurement_id_seq owned by public.tbl_isotope_measurements.isotope_measurement_id;

create sequence public.tbl_isotope_standards_isotope_standard_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_isotope_standards_isotope_standard_id_seq owner to sead_master;
alter sequence public.tbl_isotope_standards_isotope_standard_id_seq owned by public.tbl_isotope_standards.isotope_standard_id;

create sequence public.tbl_isotope_types_isotope_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_isotope_types_isotope_type_id_seq owner to sead_master;
alter sequence public.tbl_isotope_types_isotope_type_id_seq owned by public.tbl_isotope_types.isotope_type_id;

create sequence public.tbl_isotopes_isotope_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_isotopes_isotope_id_seq owner to sead_master;
alter sequence public.tbl_isotopes_isotope_id_seq owned by public.tbl_isotopes.isotope_id;

create sequence public.tbl_languages_language_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_languages_language_id_seq owner to sead_master;
alter sequence public.tbl_languages_language_id_seq owned by public.tbl_languages.language_id;

create sequence public.tbl_lithology_lithology_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_lithology_lithology_id_seq owner to sead_master;
alter sequence public.tbl_lithology_lithology_id_seq owned by public.tbl_lithology.lithology_id;

create sequence public.tbl_location_types_location_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_location_types_location_type_id_seq owner to sead_master;
alter sequence public.tbl_location_types_location_type_id_seq owned by public.tbl_location_types.location_type_id;

create sequence public.tbl_locations_location_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_locations_location_id_seq owner to sead_master;
alter sequence public.tbl_locations_location_id_seq owned by public.tbl_locations.location_id;

create sequence public.tbl_mcr_names_taxon_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_mcr_names_taxon_id_seq owner to sead_master;
alter sequence public.tbl_mcr_names_taxon_id_seq owned by public.tbl_mcr_names.taxon_id;

create sequence public.tbl_mcr_summary_data_mcr_summary_data_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_mcr_summary_data_mcr_summary_data_id_seq owner to sead_master;
alter sequence public.tbl_mcr_summary_data_mcr_summary_data_id_seq owned by public.tbl_mcr_summary_data.mcr_summary_data_id;

create sequence public.tbl_mcrdata_birmbeetledat_mcrdata_birmbeetledat_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_mcrdata_birmbeetledat_mcrdata_birmbeetledat_id_seq owner to sead_master;
alter sequence public.tbl_mcrdata_birmbeetledat_mcrdata_birmbeetledat_id_seq owned by public.tbl_mcrdata_birmbeetledat.mcrdata_birmbeetledat_id;

create sequence public.tbl_measured_value_dimensions_measured_value_dimension_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_measured_value_dimensions_measured_value_dimension_id_seq owner to sead_master;
alter sequence public.tbl_measured_value_dimensions_measured_value_dimension_id_seq owned by public.tbl_measured_value_dimensions.measured_value_dimension_id;

create sequence public.tbl_measured_values_measured_value_id_seq
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_measured_values_measured_value_id_seq owner to sead_master;
alter sequence public.tbl_measured_values_measured_value_id_seq owned by public.tbl_measured_values.measured_value_id;

create sequence public.tbl_method_groups_method_group_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_method_groups_method_group_id_seq owner to sead_master;
alter sequence public.tbl_method_groups_method_group_id_seq owned by public.tbl_method_groups.method_group_id;

create sequence public.tbl_methods_method_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_methods_method_id_seq owner to sead_master;
alter sequence public.tbl_methods_method_id_seq owned by public.tbl_methods.method_id;

create sequence public.tbl_modification_types_modification_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_modification_types_modification_type_id_seq owner to sead_master;
alter sequence public.tbl_modification_types_modification_type_id_seq owned by public.tbl_modification_types.modification_type_id;

create sequence public.tbl_physical_sample_features_physical_sample_feature_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_physical_sample_features_physical_sample_feature_id_seq owner to sead_master;
alter sequence public.tbl_physical_sample_features_physical_sample_feature_id_seq owned by public.tbl_physical_sample_features.physical_sample_feature_id;

create sequence public.tbl_physical_samples_physical_sample_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_physical_samples_physical_sample_id_seq owner to sead_master;
alter sequence public.tbl_physical_samples_physical_sample_id_seq owned by public.tbl_physical_samples.physical_sample_id;

create sequence public.tbl_project_stages_project_stage_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_project_stages_project_stage_id_seq owner to sead_master;
alter sequence public.tbl_project_stages_project_stage_id_seq owned by public.tbl_project_stages.project_stage_id;

create sequence public.tbl_project_types_project_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_project_types_project_type_id_seq owner to sead_master;
alter sequence public.tbl_project_types_project_type_id_seq owned by public.tbl_project_types.project_type_id;

create sequence public.tbl_projects_project_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_projects_project_id_seq owner to sead_master;
alter sequence public.tbl_projects_project_id_seq owned by public.tbl_projects.project_id;

create sequence public.tbl_property_types_property_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_property_types_property_type_id_seq owner to humlab_admin;
alter sequence public.tbl_property_types_property_type_id_seq owned by public.tbl_property_types.property_type_id;

create sequence public.tbl_rdb_codes_rdb_code_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_rdb_codes_rdb_code_id_seq owner to sead_master;
alter sequence public.tbl_rdb_codes_rdb_code_id_seq owned by public.tbl_rdb_codes.rdb_code_id;

create sequence public.tbl_rdb_rdb_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_rdb_rdb_id_seq owner to sead_master;
alter sequence public.tbl_rdb_rdb_id_seq owned by public.tbl_rdb.rdb_id;

create sequence public.tbl_rdb_systems_rdb_system_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_rdb_systems_rdb_system_id_seq owner to sead_master;
alter sequence public.tbl_rdb_systems_rdb_system_id_seq owned by public.tbl_rdb_systems.rdb_system_id;

create sequence public.tbl_record_types_record_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_record_types_record_type_id_seq owner to sead_master;
alter sequence public.tbl_record_types_record_type_id_seq owned by public.tbl_record_types.record_type_id;

create sequence public.tbl_relative_age_refs_relative_age_ref_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_relative_age_refs_relative_age_ref_id_seq owner to sead_master;
alter sequence public.tbl_relative_age_refs_relative_age_ref_id_seq owned by public.tbl_relative_age_refs.relative_age_ref_id;

create sequence public.tbl_relative_age_types_relative_age_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_relative_age_types_relative_age_type_id_seq owner to sead_master;
alter sequence public.tbl_relative_age_types_relative_age_type_id_seq owned by public.tbl_relative_age_types.relative_age_type_id;

create sequence public.tbl_relative_ages_relative_age_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_relative_ages_relative_age_id_seq owner to sead_master;
alter sequence public.tbl_relative_ages_relative_age_id_seq owned by public.tbl_relative_ages.relative_age_id;

create sequence public.tbl_relative_dates_relative_date_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_relative_dates_relative_date_id_seq owner to sead_master;
alter sequence public.tbl_relative_dates_relative_date_id_seq owned by public.tbl_relative_dates.relative_date_id;

create sequence public.tbl_sample_alt_refs_sample_alt_ref_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_alt_refs_sample_alt_ref_id_seq owner to sead_master;
alter sequence public.tbl_sample_alt_refs_sample_alt_ref_id_seq owned by public.tbl_sample_alt_refs.sample_alt_ref_id;

create sequence public.tbl_sample_colours_sample_colour_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_colours_sample_colour_id_seq owner to sead_master;
alter sequence public.tbl_sample_colours_sample_colour_id_seq owned by public.tbl_sample_colours.sample_colour_id;

create sequence public.tbl_sample_coordinates_sample_coordinate_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_coordinates_sample_coordinate_id_seq owner to sead_master;
alter sequence public.tbl_sample_coordinates_sample_coordinate_id_seq owned by public.tbl_sample_coordinates.sample_coordinate_id;

create sequence public.tbl_sample_description_sample_sample_description_sample_gro_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_description_sample_sample_description_sample_gro_seq owner to sead_master;
alter sequence public.tbl_sample_description_sample_sample_description_sample_gro_seq owned by public.tbl_sample_description_sample_group_contexts.sample_description_sample_group_context_id;

create sequence public.tbl_sample_description_types_sample_description_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_description_types_sample_description_type_id_seq owner to sead_master;
alter sequence public.tbl_sample_description_types_sample_description_type_id_seq owned by public.tbl_sample_description_types.sample_description_type_id;

create sequence public.tbl_sample_descriptions_sample_description_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_descriptions_sample_description_id_seq owner to sead_master;
alter sequence public.tbl_sample_descriptions_sample_description_id_seq owned by public.tbl_sample_descriptions.sample_description_id;

create sequence public.tbl_sample_dimensions_sample_dimension_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_dimensions_sample_dimension_id_seq owner to sead_master;
alter sequence public.tbl_sample_dimensions_sample_dimension_id_seq owned by public.tbl_sample_dimensions.sample_dimension_id;

create sequence public.tbl_sample_group_coordinates_sample_group_position_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_group_coordinates_sample_group_position_id_seq owner to sead_master;
alter sequence public.tbl_sample_group_coordinates_sample_group_position_id_seq owned by public.tbl_sample_group_coordinates.sample_group_position_id;

create sequence public.tbl_sample_group_description__sample_group_description_typ_seq1
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_group_description__sample_group_description_typ_seq1 owner to sead_master;
alter sequence public.tbl_sample_group_description__sample_group_description_typ_seq1 owned by public.tbl_sample_group_description_types.sample_group_description_type_id;

create sequence public.tbl_sample_group_description__sample_group_description_type_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_group_description__sample_group_description_type_seq owner to sead_master;
alter sequence public.tbl_sample_group_description__sample_group_description_type_seq owned by public.tbl_sample_group_description_type_sampling_contexts.sample_group_description_type_sampling_context_id;

create sequence public.tbl_sample_group_descriptions_sample_group_description_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_group_descriptions_sample_group_description_id_seq owner to sead_master;
alter sequence public.tbl_sample_group_descriptions_sample_group_description_id_seq owned by public.tbl_sample_group_descriptions.sample_group_description_id;

create sequence public.tbl_sample_group_dimensions_sample_group_dimension_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_group_dimensions_sample_group_dimension_id_seq owner to sead_master;
alter sequence public.tbl_sample_group_dimensions_sample_group_dimension_id_seq owned by public.tbl_sample_group_dimensions.sample_group_dimension_id;

create sequence public.tbl_sample_group_images_sample_group_image_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_group_images_sample_group_image_id_seq owner to sead_master;
alter sequence public.tbl_sample_group_images_sample_group_image_id_seq owned by public.tbl_sample_group_images.sample_group_image_id;

create sequence public.tbl_sample_group_notes_sample_group_note_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_group_notes_sample_group_note_id_seq owner to sead_master;
alter sequence public.tbl_sample_group_notes_sample_group_note_id_seq owned by public.tbl_sample_group_notes.sample_group_note_id;

create sequence public.tbl_sample_group_references_sample_group_reference_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_group_references_sample_group_reference_id_seq owner to sead_master;
alter sequence public.tbl_sample_group_references_sample_group_reference_id_seq owned by public.tbl_sample_group_references.sample_group_reference_id;

create sequence public.tbl_sample_group_sampling_contexts_sampling_context_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_group_sampling_contexts_sampling_context_id_seq owner to sead_master;
alter sequence public.tbl_sample_group_sampling_contexts_sampling_context_id_seq owned by public.tbl_sample_group_sampling_contexts.sampling_context_id;

create sequence public.tbl_sample_groups_sample_group_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_groups_sample_group_id_seq owner to sead_master;
alter sequence public.tbl_sample_groups_sample_group_id_seq owned by public.tbl_sample_groups.sample_group_id;

create sequence public.tbl_sample_horizons_sample_horizon_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_horizons_sample_horizon_id_seq owner to sead_master;
alter sequence public.tbl_sample_horizons_sample_horizon_id_seq owned by public.tbl_sample_horizons.sample_horizon_id;

create sequence public.tbl_sample_images_sample_image_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_images_sample_image_id_seq owner to sead_master;
alter sequence public.tbl_sample_images_sample_image_id_seq owned by public.tbl_sample_images.sample_image_id;

create sequence public.tbl_sample_location_type_samp_sample_location_type_sampling_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_location_type_samp_sample_location_type_sampling_seq owner to sead_master;
alter sequence public.tbl_sample_location_type_samp_sample_location_type_sampling_seq owned by public.tbl_sample_location_type_sampling_contexts.sample_location_type_sampling_context_id;

create sequence public.tbl_sample_location_types_sample_location_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_location_types_sample_location_type_id_seq owner to sead_master;
alter sequence public.tbl_sample_location_types_sample_location_type_id_seq owned by public.tbl_sample_location_types.sample_location_type_id;

create sequence public.tbl_sample_locations_sample_location_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_locations_sample_location_id_seq owner to sead_master;
alter sequence public.tbl_sample_locations_sample_location_id_seq owned by public.tbl_sample_locations.sample_location_id;

create sequence public.tbl_sample_notes_sample_note_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_notes_sample_note_id_seq owner to sead_master;
alter sequence public.tbl_sample_notes_sample_note_id_seq owned by public.tbl_sample_notes.sample_note_id;

create sequence public.tbl_sample_types_sample_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sample_types_sample_type_id_seq owner to sead_master;
alter sequence public.tbl_sample_types_sample_type_id_seq owned by public.tbl_sample_types.sample_type_id;

create sequence public.tbl_season_types_season_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_season_types_season_type_id_seq owner to sead_master;
alter sequence public.tbl_season_types_season_type_id_seq owned by public.tbl_season_types.season_type_id;

create sequence public.tbl_seasons_season_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_seasons_season_id_seq owner to sead_master;
alter sequence public.tbl_seasons_season_id_seq owned by public.tbl_seasons.season_id;

create sequence public.tbl_site_images_site_image_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_site_images_site_image_id_seq owner to sead_master;
alter sequence public.tbl_site_images_site_image_id_seq owned by public.tbl_site_images.site_image_id;

create sequence public.tbl_site_locations_site_location_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_site_locations_site_location_id_seq owner to sead_master;
alter sequence public.tbl_site_locations_site_location_id_seq owned by public.tbl_site_locations.site_location_id;

create sequence public.tbl_site_natgridrefs_site_natgridref_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_site_natgridrefs_site_natgridref_id_seq owner to sead_master;
alter sequence public.tbl_site_natgridrefs_site_natgridref_id_seq owned by public.tbl_site_natgridrefs.site_natgridref_id;

create sequence public.tbl_site_other_records_site_other_records_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_site_other_records_site_other_records_id_seq owner to sead_master;
alter sequence public.tbl_site_other_records_site_other_records_id_seq owned by public.tbl_site_other_records.site_other_records_id;

create sequence public.tbl_site_preservation_status_site_preservation_status_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_site_preservation_status_site_preservation_status_id_seq owner to sead_master;
alter sequence public.tbl_site_preservation_status_site_preservation_status_id_seq owned by public.tbl_site_preservation_status.site_preservation_status_id;

create sequence public.tbl_site_properties_site_property_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_site_properties_site_property_id_seq owner to humlab_admin;
alter sequence public.tbl_site_properties_site_property_id_seq owned by public.tbl_site_properties.site_property_id;

create sequence public.tbl_site_references_site_reference_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_site_references_site_reference_id_seq owner to sead_master;
alter sequence public.tbl_site_references_site_reference_id_seq owned by public.tbl_site_references.site_reference_id;

create sequence public.tbl_site_site_types_site_site_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_site_site_types_site_site_type_id_seq owner to humlab_admin;
alter sequence public.tbl_site_site_types_site_site_type_id_seq owned by public.tbl_site_site_types.site_site_type_id;

create sequence public.tbl_site_type_groups_site_type_group_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_site_type_groups_site_type_group_id_seq owner to humlab_admin;
alter sequence public.tbl_site_type_groups_site_type_group_id_seq owned by public.tbl_site_type_groups.site_type_group_id;

create sequence public.tbl_site_types_site_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_site_types_site_type_id_seq owner to humlab_admin;
alter sequence public.tbl_site_types_site_type_id_seq owned by public.tbl_site_types.site_type_id;

create sequence public.tbl_sites_site_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_sites_site_id_seq owner to sead_master;
alter sequence public.tbl_sites_site_id_seq owned by public.tbl_sites.site_id;

create sequence public.tbl_species_association_types_association_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_species_association_types_association_type_id_seq owner to sead_master;
alter sequence public.tbl_species_association_types_association_type_id_seq owned by public.tbl_species_association_types.association_type_id;

create sequence public.tbl_species_associations_species_association_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_species_associations_species_association_id_seq owner to sead_master;
alter sequence public.tbl_species_associations_species_association_id_seq owned by public.tbl_species_associations.species_association_id;

create sequence public.tbl_taxa_common_names_taxon_common_name_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_taxa_common_names_taxon_common_name_id_seq owner to sead_master;
alter sequence public.tbl_taxa_common_names_taxon_common_name_id_seq owned by public.tbl_taxa_common_names.taxon_common_name_id;

create sequence public.tbl_taxa_images_taxa_images_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_taxa_images_taxa_images_id_seq owner to sead_master;
alter sequence public.tbl_taxa_images_taxa_images_id_seq owned by public.tbl_taxa_images.taxa_images_id;

create sequence public.tbl_taxa_measured_attributes_measured_attribute_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_taxa_measured_attributes_measured_attribute_id_seq owner to sead_master;
alter sequence public.tbl_taxa_measured_attributes_measured_attribute_id_seq owned by public.tbl_taxa_measured_attributes.measured_attribute_id;

create sequence public.tbl_taxa_reference_specimens_taxa_reference_specimen_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_taxa_reference_specimens_taxa_reference_specimen_id_seq owner to sead_master;
alter sequence public.tbl_taxa_reference_specimens_taxa_reference_specimen_id_seq owned by public.tbl_taxa_reference_specimens.taxa_reference_specimen_id;

create sequence public.tbl_taxa_seasonality_seasonality_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_taxa_seasonality_seasonality_id_seq owner to sead_master;
alter sequence public.tbl_taxa_seasonality_seasonality_id_seq owned by public.tbl_taxa_seasonality.seasonality_id;

create sequence public.tbl_taxa_synonyms_synonym_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_taxa_synonyms_synonym_id_seq owner to sead_master;
alter sequence public.tbl_taxa_synonyms_synonym_id_seq owned by public.tbl_taxa_synonyms.synonym_id;

create sequence public.tbl_taxa_tree_authors_author_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_taxa_tree_authors_author_id_seq owner to sead_master;
alter sequence public.tbl_taxa_tree_authors_author_id_seq owned by public.tbl_taxa_tree_authors.author_id;

create sequence public.tbl_taxa_tree_families_family_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_taxa_tree_families_family_id_seq owner to sead_master;
alter sequence public.tbl_taxa_tree_families_family_id_seq owned by public.tbl_taxa_tree_families.family_id;

create sequence public.tbl_taxa_tree_genera_genus_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_taxa_tree_genera_genus_id_seq owner to sead_master;
alter sequence public.tbl_taxa_tree_genera_genus_id_seq owned by public.tbl_taxa_tree_genera.genus_id;

create sequence public.tbl_taxa_tree_master_taxon_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_taxa_tree_master_taxon_id_seq owner to sead_master;
alter sequence public.tbl_taxa_tree_master_taxon_id_seq owned by public.tbl_taxa_tree_master.taxon_id;

create sequence public.tbl_taxa_tree_orders_order_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_taxa_tree_orders_order_id_seq owner to sead_master;
alter sequence public.tbl_taxa_tree_orders_order_id_seq owned by public.tbl_taxa_tree_orders.order_id;

create sequence public.tbl_taxonomic_order_biblio_taxonomic_order_biblio_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_taxonomic_order_biblio_taxonomic_order_biblio_id_seq owner to sead_master;
alter sequence public.tbl_taxonomic_order_biblio_taxonomic_order_biblio_id_seq owned by public.tbl_taxonomic_order_biblio.taxonomic_order_biblio_id;

create sequence public.tbl_taxonomic_order_systems_taxonomic_order_system_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_taxonomic_order_systems_taxonomic_order_system_id_seq owner to sead_master;
alter sequence public.tbl_taxonomic_order_systems_taxonomic_order_system_id_seq owned by public.tbl_taxonomic_order_systems.taxonomic_order_system_id;

create sequence public.tbl_taxonomic_order_taxonomic_order_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_taxonomic_order_taxonomic_order_id_seq owner to sead_master;
alter sequence public.tbl_taxonomic_order_taxonomic_order_id_seq owned by public.tbl_taxonomic_order.taxonomic_order_id;

create sequence public.tbl_taxonomy_notes_taxonomy_notes_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_taxonomy_notes_taxonomy_notes_id_seq owner to sead_master;
alter sequence public.tbl_taxonomy_notes_taxonomy_notes_id_seq owned by public.tbl_taxonomy_notes.taxonomy_notes_id;

create sequence public.tbl_temperatures_record_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_temperatures_record_id_seq owner to sead_master;
alter sequence public.tbl_temperatures_record_id_seq owned by public.tbl_temperatures.record_id;

create sequence public.tbl_tephra_dates_tephra_date_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_tephra_dates_tephra_date_id_seq owner to sead_master;
alter sequence public.tbl_tephra_dates_tephra_date_id_seq owned by public.tbl_tephra_dates.tephra_date_id;

create sequence public.tbl_tephra_refs_tephra_ref_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_tephra_refs_tephra_ref_id_seq owner to sead_master;
alter sequence public.tbl_tephra_refs_tephra_ref_id_seq owned by public.tbl_tephra_refs.tephra_ref_id;

create sequence public.tbl_tephras_tephra_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_tephras_tephra_id_seq owner to sead_master;
alter sequence public.tbl_tephras_tephra_id_seq owned by public.tbl_tephras.tephra_id;

create sequence public.tbl_text_biology_biology_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_text_biology_biology_id_seq owner to sead_master;
alter sequence public.tbl_text_biology_biology_id_seq owned by public.tbl_text_biology.biology_id;

create sequence public.tbl_text_distribution_distribution_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_text_distribution_distribution_id_seq owner to sead_master;
alter sequence public.tbl_text_distribution_distribution_id_seq owned by public.tbl_text_distribution.distribution_id;

create sequence public.tbl_text_identification_keys_key_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_text_identification_keys_key_id_seq owner to sead_master;
alter sequence public.tbl_text_identification_keys_key_id_seq owned by public.tbl_text_identification_keys.key_id;

create sequence public.tbl_units_unit_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_units_unit_id_seq owner to sead_master;
alter sequence public.tbl_units_unit_id_seq owned by public.tbl_units.unit_id;

create sequence public.tbl_years_types_years_type_id_seq
as integer
start with 1
increment by 1
no minvalue
no maxvalue
cache 1;


alter sequence public.tbl_years_types_years_type_id_seq owner to sead_master;
alter sequence public.tbl_years_types_years_type_id_seq owned by public.tbl_years_types.years_type_id;


--
-- PostgreSQL database dump complete
--

\unrestrict HG9VTnOp7imKVr7BraooPAj1g0T6DmKceBfeyvjfyduAf0dg9bqS5crRNwxAtW6
