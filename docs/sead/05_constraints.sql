alter table only public.tbl_abundance_elements
add constraint tbl_abundance_elements_pkey primary key (abundance_element_id);


alter table only public.tbl_abundance_ident_levels
add constraint tbl_abundance_ident_levels_pkey primary key (abundance_ident_level_id);


alter table only public.tbl_abundance_modifications
add constraint tbl_abundance_modifications_pkey primary key (abundance_modification_id);


alter table only public.tbl_abundance_properties
add constraint tbl_abundance_properties_pkey primary key (abundance_property_id);


alter table only public.tbl_abundances
add constraint tbl_abundances_pkey primary key (abundance_id);


alter table only public.tbl_activity_types
add constraint tbl_activity_types_activity_type_key unique (activity_type);


alter table only public.tbl_activity_types
add constraint tbl_activity_types_activity_type_unique unique (activity_type);


alter table only public.tbl_activity_types
add constraint tbl_activity_types_pkey primary key (activity_type_id);


alter table only public.tbl_age_types
add constraint tbl_age_types_pkey primary key (age_type_id);


alter table only public.tbl_aggregate_datasets
add constraint tbl_aggregate_datasets_pkey primary key (aggregate_dataset_id);


alter table only public.tbl_aggregate_order_types
add constraint tbl_aggregate_order_types_aggregate_order_type_key unique (aggregate_order_type);


alter table only public.tbl_aggregate_order_types
add constraint tbl_aggregate_order_types_aggregate_order_type_unique unique (aggregate_order_type);


alter table only public.tbl_aggregate_order_types
add constraint tbl_aggregate_order_types_pkey primary key (aggregate_order_type_id);


alter table only public.tbl_aggregate_sample_ages
add constraint tbl_aggregate_sample_ages_pkey primary key (aggregate_sample_age_id);


alter table only public.tbl_aggregate_samples
add constraint tbl_aggregate_samples_pkey primary key (aggregate_sample_id);


alter table only public.tbl_alt_ref_types
add constraint tbl_alt_ref_types_alt_ref_type_key unique (alt_ref_type);


alter table only public.tbl_alt_ref_types
add constraint tbl_alt_ref_types_alt_ref_type_unique unique (alt_ref_type);


alter table only public.tbl_alt_ref_types
add constraint tbl_alt_ref_types_pkey primary key (alt_ref_type_id);


alter table only public.tbl_analysis_boolean_values
add constraint tbl_analysis_boolean_values_analysis_value_id_key unique (analysis_value_id);


alter table only public.tbl_analysis_boolean_values
add constraint tbl_analysis_boolean_values_pkey primary key (analysis_boolean_value_id);


alter table only public.tbl_analysis_categorical_values
add constraint tbl_analysis_categorical_values_pkey primary key (analysis_categorical_value_id);


alter table only public.tbl_analysis_dating_ranges
add constraint tbl_analysis_dating_ranges_pkey primary key (analysis_dating_range_id);


alter table only public.tbl_analysis_entities
add constraint tbl_analysis_entities_pkey primary key (analysis_entity_id);


alter table only public.tbl_analysis_entity_ages
add constraint tbl_analysis_entity_ages_pkey primary key (analysis_entity_age_id);


alter table only public.tbl_analysis_entity_dimensions
add constraint tbl_analysis_entity_dimensions_pkey primary key (analysis_entity_dimension_id);


alter table only public.tbl_analysis_entity_prep_methods
add constraint tbl_analysis_entity_prep_methods_pkey primary key (analysis_entity_prep_method_id);


alter table only public.tbl_analysis_identifiers
add constraint tbl_analysis_identifiers_pkey primary key (analysis_identifier_id);


alter table only public.tbl_analysis_integer_ranges
add constraint tbl_analysis_integer_ranges_pkey primary key (analysis_integer_range_id);


alter table only public.tbl_analysis_integer_values
add constraint tbl_analysis_integer_values_pkey primary key (analysis_integer_value_id);


alter table only public.tbl_analysis_notes
add constraint tbl_analysis_notes_pkey primary key (analysis_note_id);


alter table only public.tbl_analysis_numerical_ranges
add constraint tbl_analysis_numerical_ranges_pkey primary key (analysis_numerical_range_id);


alter table only public.tbl_analysis_numerical_values
add constraint tbl_analysis_numerical_values_pkey primary key (analysis_numerical_value_id);


alter table only public.tbl_analysis_taxon_counts
add constraint tbl_analysis_taxon_counts_pkey primary key (analysis_taxon_count_id);


alter table only public.tbl_analysis_value_dimensions
add constraint tbl_analysis_value_dimensions_pkey primary key (analysis_value_dimension_id);


alter table only public.tbl_analysis_values
add constraint tbl_analysis_values_pkey primary key (analysis_value_id);


alter table only public.tbl_biblio
add constraint tbl_biblio_pkey primary key (biblio_id);


alter table only public.tbl_ceramics_lookup
add constraint tbl_ceramics_lookup_pkey primary key (ceramics_lookup_id);


alter table only public.tbl_ceramics_measurements
add constraint tbl_ceramics_measurements_pkey primary key (ceramics_measurement_id);


alter table only public.tbl_ceramics
add constraint tbl_ceramics_pkey primary key (ceramics_id);


alter table only public.tbl_chronologies
add constraint tbl_chronologies_chronology_name_key unique (chronology_name);


alter table only public.tbl_chronologies
add constraint tbl_chronologies_chronology_name_unique unique (chronology_name);


alter table only public.tbl_chronologies
add constraint tbl_chronologies_pkey primary key (chronology_id);


alter table only public.tbl_colours
add constraint tbl_colours_colour_name_key unique (colour_name);


alter table only public.tbl_colours
add constraint tbl_colours_colour_name_unique unique (colour_name);


alter table only public.tbl_colours
add constraint tbl_colours_pkey primary key (colour_id);


alter table only public.tbl_contact_types
add constraint tbl_contact_types_pkey primary key (contact_type_id);


alter table only public.tbl_contacts
add constraint tbl_contacts_pkey primary key (contact_id);


alter table only public.tbl_coordinate_method_dimensions
add constraint tbl_coordinate_method_dimensions_pkey primary key (coordinate_method_dimension_id);


alter table only public.tbl_data_type_groups
add constraint tbl_data_type_groups_data_type_group_name_key unique (data_type_group_name);


alter table only public.tbl_data_type_groups
add constraint tbl_data_type_groups_data_type_group_name_unique unique (data_type_group_name);


alter table only public.tbl_data_type_groups
add constraint tbl_data_type_groups_pkey primary key (data_type_group_id);


alter table only public.tbl_data_types
add constraint tbl_data_types_data_type_name_key unique (data_type_name);


alter table only public.tbl_data_types
add constraint tbl_data_types_data_type_name_unique unique (data_type_name);


alter table only public.tbl_data_types
add constraint tbl_data_types_pkey primary key (data_type_id);


alter table only public.tbl_dataset_contacts
add constraint tbl_dataset_contacts_pkey primary key (dataset_contact_id);


alter table only public.tbl_dataset_masters
add constraint tbl_dataset_masters_master_name_key unique (master_name);


alter table only public.tbl_dataset_masters
add constraint tbl_dataset_masters_master_name_unique unique (master_name);


alter table only public.tbl_dataset_masters
add constraint tbl_dataset_masters_pkey primary key (master_set_id);


alter table only public.tbl_dataset_methods
add constraint tbl_dataset_methods_pkey primary key (dataset_method_id);


alter table only public.tbl_dataset_submission_types
add constraint tbl_dataset_submission_types_pkey primary key (submission_type_id);


alter table only public.tbl_dataset_submissions
add constraint tbl_dataset_submissions_pkey primary key (dataset_submission_id);


alter table only public.tbl_datasets
add constraint tbl_datasets_pkey primary key (dataset_id);


alter table only public.tbl_dating_labs
add constraint tbl_dating_labs_pkey primary key (dating_lab_id);


alter table only public.tbl_dating_material
add constraint tbl_dating_material_pkey primary key (dating_material_id);


alter table only public.tbl_dating_uncertainty
add constraint tbl_dating_uncertainty_pkey primary key (dating_uncertainty_id);


alter table only public.tbl_dating_uncertainty
add constraint tbl_dating_uncertainty_uncertainty_key unique (uncertainty);


alter table only public.tbl_dating_uncertainty
add constraint tbl_dating_uncertainty_uncertainty_unique unique (uncertainty);


alter table only public.tbl_dendro_date_notes
add constraint tbl_dendro_date_notes_pkey primary key (dendro_date_note_id);


alter table only public.tbl_dendro_dates
add constraint tbl_dendro_dates_pkey primary key (dendro_date_id);


alter table only public.tbl_dendro_lookup
add constraint tbl_dendro_lookup_pkey primary key (dendro_lookup_id);


alter table only public.tbl_dendro
add constraint tbl_dendro_pkey primary key (dendro_id);


alter table only public.tbl_dimensions
add constraint tbl_dimensions_pkey primary key (dimension_id);


alter table only public.tbl_ecocode_definitions
add constraint tbl_ecocode_definitions_pkey primary key (ecocode_definition_id);


alter table only public.tbl_ecocode_groups
add constraint tbl_ecocode_groups_name_key unique (name);


alter table only public.tbl_ecocode_groups
add constraint tbl_ecocode_groups_name_unique unique (name);


alter table only public.tbl_ecocode_groups
add constraint tbl_ecocode_groups_pkey primary key (ecocode_group_id);


alter table only public.tbl_ecocode_systems
add constraint tbl_ecocode_systems_name_key unique (name);


alter table only public.tbl_ecocode_systems
add constraint tbl_ecocode_systems_name_unique unique (name);


alter table only public.tbl_ecocode_systems
add constraint tbl_ecocode_systems_pkey primary key (ecocode_system_id);


alter table only public.tbl_ecocodes
add constraint tbl_ecocodes_pkey primary key (ecocode_id);


alter table only public.tbl_feature_types
add constraint tbl_feature_types_pkey primary key (feature_type_id);


alter table only public.tbl_features
add constraint tbl_features_pkey primary key (feature_id);


alter table only public.tbl_geochron_refs
add constraint tbl_geochron_refs_pkey primary key (geochron_ref_id);


alter table only public.tbl_geochronology
add constraint tbl_geochronology_pkey primary key (geochron_id);


alter table only public.tbl_horizons
add constraint tbl_horizons_pkey primary key (horizon_id);


alter table only public.tbl_identification_levels
add constraint tbl_identification_levels_identification_level_name_key unique (identification_level_name);


alter table only public.tbl_identification_levels
add constraint tbl_identification_levels_identification_level_name_unique unique (identification_level_name);


alter table only public.tbl_identification_levels
add constraint tbl_identification_levels_pkey primary key (identification_level_id);


alter table only public.tbl_image_types
add constraint tbl_image_types_image_type_key unique (image_type);


alter table only public.tbl_image_types
add constraint tbl_image_types_image_type_unique unique (image_type);


alter table only public.tbl_image_types
add constraint tbl_image_types_pkey primary key (image_type_id);


alter table only public.tbl_imported_taxa_replacements
add constraint tbl_imported_taxa_replacements_pkey primary key (imported_taxa_replacement_id);


alter table only public.tbl_isotope_measurements
add constraint tbl_isotope_measurements_pkey primary key (isotope_measurement_id);


alter table only public.tbl_isotope_standards
add constraint tbl_isotope_standards_pkey primary key (isotope_standard_id);


alter table only public.tbl_isotope_types
add constraint tbl_isotope_types_pkey primary key (isotope_type_id);


alter table only public.tbl_isotope_value_specifiers
add constraint tbl_isotope_value_specifiers_pkey primary key (isotope_value_specifier_id);


alter table only public.tbl_isotopes
add constraint tbl_isotopes_pkey primary key (isotope_id);


alter table only public.tbl_languages
add constraint tbl_languages_pkey primary key (language_id);


alter table only public.tbl_lithology
add constraint tbl_lithology_pkey primary key (lithology_id);


alter table only public.tbl_location_types
add constraint tbl_location_types_location_type_key unique (location_type);


alter table only public.tbl_location_types
add constraint tbl_location_types_location_type_unique unique (location_type);


alter table only public.tbl_location_types
add constraint tbl_location_types_pkey primary key (location_type_id);


alter table only public.tbl_locations
add constraint tbl_locations_pkey primary key (location_id);


alter table only public.tbl_mcr_names
add constraint tbl_mcr_names_pkey primary key (taxon_id);


alter table only public.tbl_mcr_summary_data
add constraint tbl_mcr_summary_data_pkey primary key (mcr_summary_data_id);


alter table only public.tbl_mcrdata_birmbeetledat
add constraint tbl_mcrdata_birmbeetledat_pkey primary key (mcrdata_birmbeetledat_id);


alter table only public.tbl_measured_value_dimensions
add constraint tbl_measured_value_dimensions_pkey primary key (measured_value_dimension_id);


alter table only public.tbl_measured_values
add constraint tbl_measured_values_pkey primary key (measured_value_id);


alter table only public.tbl_method_groups
add constraint tbl_method_groups_group_name_key unique (group_name);


alter table only public.tbl_method_groups
add constraint tbl_method_groups_group_name_unique unique (group_name);


alter table only public.tbl_method_groups
add constraint tbl_method_groups_pkey primary key (method_group_id);


alter table only public.tbl_methods
add constraint tbl_methods_method_abbrev_or_alt_name_key unique (method_abbrev_or_alt_name);


alter table only public.tbl_methods
add constraint tbl_methods_method_abbrev_or_alt_name_unique unique (method_abbrev_or_alt_name);


alter table only public.tbl_methods
add constraint tbl_methods_pkey primary key (method_id);


alter table only public.tbl_modification_types
add constraint tbl_modification_types_modification_type_name_key unique (modification_type_name);


alter table only public.tbl_modification_types
add constraint tbl_modification_types_modification_type_name_unique unique (modification_type_name);


alter table only public.tbl_modification_types
add constraint tbl_modification_types_pkey primary key (modification_type_id);


alter table only public.tbl_physical_sample_features
add constraint tbl_physical_sample_features_pkey primary key (physical_sample_feature_id);


alter table only public.tbl_physical_samples
add constraint tbl_physical_samples_pkey primary key (physical_sample_id);


alter table only public.tbl_project_stages
add constraint tbl_project_stages_pkey primary key (project_stage_id);


alter table only public.tbl_project_stages
add constraint tbl_project_stages_stage_name_key unique (stage_name);


alter table only public.tbl_project_stages
add constraint tbl_project_stages_stage_name_unique unique (stage_name);


alter table only public.tbl_project_types
add constraint tbl_project_types_pkey primary key (project_type_id);


alter table only public.tbl_project_types
add constraint tbl_project_types_project_type_name_key unique (project_type_name);


alter table only public.tbl_project_types
add constraint tbl_project_types_project_type_name_unique unique (project_type_name);


alter table only public.tbl_projects
add constraint tbl_projects_pkey primary key (project_id);


alter table only public.tbl_projects
add constraint tbl_projects_project_abbrev_name_unique unique (project_abbrev_name);


alter table only public.tbl_property_types
add constraint tbl_property_types_pkey primary key (property_type_id);


alter table only public.tbl_property_types
add constraint tbl_property_types_property_type_name_key unique (property_type_name);


alter table only public.tbl_property_types
add constraint tbl_property_types_uuid_key unique (uuid);


alter table only public.tbl_rdb_codes
add constraint tbl_rdb_codes_pkey primary key (rdb_code_id);


alter table only public.tbl_rdb
add constraint tbl_rdb_pkey primary key (rdb_id);


alter table only public.tbl_rdb_systems
add constraint tbl_rdb_systems_pkey primary key (rdb_system_id);


alter table only public.tbl_record_types
add constraint tbl_record_types_pkey primary key (record_type_id);


alter table only public.tbl_record_types
add constraint tbl_record_types_record_type_name_key unique (record_type_name);


alter table only public.tbl_record_types
add constraint tbl_record_types_record_type_name_unique unique (record_type_name);


alter table only public.tbl_relative_age_refs
add constraint tbl_relative_age_refs_pkey primary key (relative_age_ref_id);


alter table only public.tbl_relative_age_types
add constraint tbl_relative_age_types_age_type_key unique (age_type);


alter table only public.tbl_relative_age_types
add constraint tbl_relative_age_types_age_type_unique unique (age_type);


alter table only public.tbl_relative_age_types
add constraint tbl_relative_age_types_pkey primary key (relative_age_type_id);


alter table only public.tbl_relative_ages
add constraint tbl_relative_ages_pkey primary key (relative_age_id);


alter table only public.tbl_relative_dates
add constraint tbl_relative_dates_pkey primary key (relative_date_id);


alter table only public.tbl_sample_alt_refs
add constraint tbl_sample_alt_refs_pkey primary key (sample_alt_ref_id);


alter table only public.tbl_sample_colours
add constraint tbl_sample_colours_pkey primary key (sample_colour_id);


alter table only public.tbl_sample_coordinates
add constraint tbl_sample_coordinates_pkey primary key (sample_coordinate_id);


alter table only public.tbl_sample_description_sample_group_contexts
add constraint tbl_sample_description_sample_group_contexts_pkey primary key (
    sample_description_sample_group_context_id
);


alter table only public.tbl_sample_description_types
add constraint tbl_sample_description_types_pkey primary key (sample_description_type_id);


alter table only public.tbl_sample_description_types
add constraint tbl_sample_description_types_type_name_key unique (type_name);


alter table only public.tbl_sample_description_types
add constraint tbl_sample_description_types_type_name_unique unique (type_name);


alter table only public.tbl_sample_descriptions
add constraint tbl_sample_descriptions_pkey primary key (sample_description_id);


alter table only public.tbl_sample_dimensions
add constraint tbl_sample_dimensions_pkey primary key (sample_dimension_id);


alter table only public.tbl_sample_group_coordinates
add constraint tbl_sample_group_coordinates_pkey primary key (sample_group_position_id);


alter table only public.tbl_sample_group_description_type_sampling_contexts
add constraint tbl_sample_group_description_type_sampling_contexts_pkey primary key (
    sample_group_description_type_sampling_context_id
);


alter table only public.tbl_sample_group_description_types
add constraint tbl_sample_group_description_types_pkey primary key (sample_group_description_type_id);


alter table only public.tbl_sample_group_description_types
add constraint tbl_sample_group_description_types_type_name_key unique (type_name);


alter table only public.tbl_sample_group_description_types
add constraint tbl_sample_group_description_types_type_name_unique unique (type_name);


alter table only public.tbl_sample_group_descriptions
add constraint tbl_sample_group_descriptions_pkey primary key (sample_group_description_id);


alter table only public.tbl_sample_group_dimensions
add constraint tbl_sample_group_dimensions_pkey primary key (sample_group_dimension_id);


alter table only public.tbl_sample_group_images
add constraint tbl_sample_group_images_pkey primary key (sample_group_image_id);


alter table only public.tbl_sample_group_notes
add constraint tbl_sample_group_notes_pkey primary key (sample_group_note_id);


alter table only public.tbl_sample_group_references
add constraint tbl_sample_group_references_pkey primary key (sample_group_reference_id);


alter table only public.tbl_sample_group_sampling_contexts
add constraint tbl_sample_group_sampling_contexts_pkey primary key (sampling_context_id);


alter table only public.tbl_sample_groups
add constraint tbl_sample_groups_pkey primary key (sample_group_id);


alter table only public.tbl_sample_horizons
add constraint tbl_sample_horizons_pkey primary key (sample_horizon_id);


alter table only public.tbl_sample_images
add constraint tbl_sample_images_pkey primary key (sample_image_id);


alter table only public.tbl_sample_location_type_sampling_contexts
add constraint tbl_sample_location_type_sampling_contexts_pkey primary key (sample_location_type_sampling_context_id);


alter table only public.tbl_sample_location_types
add constraint tbl_sample_location_types_location_type_key unique (location_type);


alter table only public.tbl_sample_location_types
add constraint tbl_sample_location_types_location_type_unique unique (location_type);


alter table only public.tbl_sample_location_types
add constraint tbl_sample_location_types_pkey primary key (sample_location_type_id);


alter table only public.tbl_sample_locations
add constraint tbl_sample_locations_pkey primary key (sample_location_id);


alter table only public.tbl_sample_notes
add constraint tbl_sample_notes_pkey primary key (sample_note_id);


alter table only public.tbl_sample_types
add constraint tbl_sample_types_pkey primary key (sample_type_id);


alter table only public.tbl_sample_types
add constraint tbl_sample_types_type_name_key unique (type_name);


alter table only public.tbl_sample_types
add constraint tbl_sample_types_type_name_unique unique (type_name);


alter table only public.tbl_season_types
add constraint tbl_season_types_pkey primary key (season_type_id);


alter table only public.tbl_season_types
add constraint tbl_season_types_season_type_key unique (season_type);


alter table only public.tbl_season_types
add constraint tbl_season_types_season_type_unique unique (season_type);


alter table only public.tbl_seasons
add constraint tbl_seasons_pkey primary key (season_id);


alter table only public.tbl_seasons
add constraint tbl_seasons_season_name_key unique (season_name);


alter table only public.tbl_seasons
add constraint tbl_seasons_season_name_unique unique (season_name);


alter table only public.tbl_site_images
add constraint tbl_site_images_pkey primary key (site_image_id);


alter table only public.tbl_site_locations
add constraint tbl_site_locations_pkey primary key (site_location_id);


alter table only public.tbl_site_natgridrefs
add constraint tbl_site_natgridrefs_pkey primary key (site_natgridref_id);


alter table only public.tbl_site_other_records
add constraint tbl_site_other_records_pkey primary key (site_other_records_id);


alter table only public.tbl_site_preservation_status
add constraint tbl_site_preservation_status_pkey primary key (site_preservation_status_id);


alter table only public.tbl_site_properties
add constraint tbl_site_properties_pkey primary key (site_property_id);


alter table only public.tbl_site_references
add constraint tbl_site_references_pkey primary key (site_reference_id);


alter table only public.tbl_site_site_types
add constraint tbl_site_site_types_pkey primary key (site_site_type_id);


alter table only public.tbl_site_type_groups
add constraint tbl_site_type_groups_pkey primary key (site_type_group_id);


alter table only public.tbl_site_type_groups
add constraint tbl_site_type_groups_site_type_group_abbrev_key unique (site_type_group_abbrev);


alter table only public.tbl_site_types
add constraint tbl_site_types_pkey primary key (site_type_id);


alter table only public.tbl_site_types
add constraint tbl_site_types_site_type_abbrev_key unique (site_type_abbrev);


alter table only public.tbl_site_types
add constraint tbl_site_types_site_type_key unique (site_type);


alter table only public.tbl_sites
add constraint tbl_sites_pkey primary key (site_id);


alter table only public.tbl_species_association_types
add constraint tbl_species_association_types_association_type_name_key unique (association_type_name);


alter table only public.tbl_species_association_types
add constraint tbl_species_association_types_association_type_name_unique unique (association_type_name);


alter table only public.tbl_species_association_types
add constraint tbl_species_association_types_pkey primary key (association_type_id);


alter table only public.tbl_species_associations
add constraint tbl_species_associations_pkey primary key (species_association_id);


alter table only public.tbl_taxa_common_names
add constraint tbl_taxa_common_names_pkey primary key (taxon_common_name_id);


alter table only public.tbl_taxa_images
add constraint tbl_taxa_images_pkey primary key (taxa_images_id);


alter table only public.tbl_taxa_measured_attributes
add constraint tbl_taxa_measured_attributes_pkey primary key (measured_attribute_id);


alter table only public.tbl_taxa_reference_specimens
add constraint tbl_taxa_reference_specimens_pkey primary key (taxa_reference_specimen_id);


alter table only public.tbl_taxa_seasonality
add constraint tbl_taxa_seasonality_pkey primary key (seasonality_id);


alter table only public.tbl_taxa_synonyms
add constraint tbl_taxa_synonyms_pkey primary key (synonym_id);


alter table only public.tbl_taxa_tree_authors
add constraint tbl_taxa_tree_authors_pkey primary key (author_id);


alter table only public.tbl_taxa_tree_families
add constraint tbl_taxa_tree_families_pkey primary key (family_id);


alter table only public.tbl_taxa_tree_genera
add constraint tbl_taxa_tree_genera_pkey primary key (genus_id);


alter table only public.tbl_taxa_tree_master
add constraint tbl_taxa_tree_master_pkey primary key (taxon_id);


alter table only public.tbl_taxa_tree_orders
add constraint tbl_taxa_tree_orders_pkey primary key (order_id);


alter table only public.tbl_taxonomic_order_biblio
add constraint tbl_taxonomic_order_biblio_pkey primary key (taxonomic_order_biblio_id);


alter table only public.tbl_taxonomic_order
add constraint tbl_taxonomic_order_pkey primary key (taxonomic_order_id);


alter table only public.tbl_taxonomic_order_systems
add constraint tbl_taxonomic_order_systems_pkey primary key (taxonomic_order_system_id);


alter table only public.tbl_taxonomy_notes
add constraint tbl_taxonomy_notes_pkey primary key (taxonomy_notes_id);


alter table only public.tbl_temperatures
add constraint tbl_temperatures_pkey primary key (record_id);


alter table only public.tbl_tephra_dates
add constraint tbl_tephra_dates_pkey primary key (tephra_date_id);


alter table only public.tbl_tephra_refs
add constraint tbl_tephra_refs_pkey primary key (tephra_ref_id);


alter table only public.tbl_tephras
add constraint tbl_tephras_pkey primary key (tephra_id);


alter table only public.tbl_text_biology
add constraint tbl_text_biology_pkey primary key (biology_id);


alter table only public.tbl_text_distribution
add constraint tbl_text_distribution_pkey primary key (distribution_id);


alter table only public.tbl_text_identification_keys
add constraint tbl_text_identification_keys_pkey primary key (key_id);


alter table only public.tbl_units
add constraint tbl_units_pkey primary key (unit_id);


alter table only public.tbl_units
add constraint tbl_units_unit_abbrev_key unique (unit_abbrev);


alter table only public.tbl_units
add constraint tbl_units_unit_abbrev_unique unique (unit_abbrev);


alter table only public.tbl_units
add constraint tbl_units_unit_name_key unique (unit_name);


alter table only public.tbl_units
add constraint tbl_units_unit_name_unique unique (unit_name);


alter table only public.tbl_updates_log
add constraint tbl_updates_log_pkey primary key (updates_log_id);


alter table only public.tbl_value_classes
add constraint tbl_value_classes_pkey primary key (value_class_id);


alter table only public.tbl_value_qualifier_symbols
add constraint tbl_value_qualifier_symbols_pkey primary key (qualifier_symbol_id);


alter table only public.tbl_value_qualifier_symbols
add constraint tbl_value_qualifier_symbols_symbol_key unique (symbol);


alter table only public.tbl_value_qualifiers
add constraint tbl_value_qualifiers_pkey primary key (qualifier_id);


alter table only public.tbl_value_qualifiers
add constraint tbl_value_qualifiers_symbol_key unique (symbol);


alter table only public.tbl_value_type_items
add constraint tbl_value_type_items_pkey primary key (value_type_item_id);


alter table only public.tbl_value_types
add constraint tbl_value_types_name_key unique (name);


alter table only public.tbl_value_types
add constraint tbl_value_types_pkey primary key (value_type_id);


alter table only public.tbl_years_types
add constraint tbl_years_types_name_key unique (name);


alter table only public.tbl_years_types
add constraint tbl_years_types_name_unique unique (name);


alter table only public.tbl_years_types
add constraint tbl_years_types_pkey primary key (years_type_id);


alter table only public.tbl_aggregate_datasets
add constraint unique_tbl_aggregate_datasets_aggregate_dataset_uuid unique (aggregate_dataset_uuid);


alter table only public.tbl_biblio
add constraint unique_tbl_biblio_biblio_uuid unique (biblio_uuid);


alter table only public.tbl_dataset_masters
add constraint unique_tbl_dataset_masters_master_set_uuid unique (master_set_uuid);


alter table only public.tbl_datasets
add constraint unique_tbl_datasets_dataset_uuid unique (dataset_uuid);


alter table only public.tbl_ecocode_systems
add constraint unique_tbl_ecocode_systems_ecocode_system_uuid unique (ecocode_system_uuid);


alter table only public.tbl_geochronology
add constraint unique_tbl_geochronology_geochron_uuid unique (geochron_uuid);


alter table only public.tbl_methods
add constraint unique_tbl_methods_method_uuid unique (method_uuid);


alter table only public.tbl_rdb_systems
add constraint unique_tbl_rdb_systems_rdb_system_uuid unique (rdb_system_uuid);


alter table only public.tbl_relative_ages
add constraint unique_tbl_relative_ages_relative_age_uuid unique (relative_age_uuid);


alter table only public.tbl_sample_groups
add constraint unique_tbl_sample_groups_sample_group_uuid unique (sample_group_uuid);


alter table only public.tbl_site_other_records
add constraint unique_tbl_site_other_records_site_other_records_uuid unique (site_other_records_uuid);


alter table only public.tbl_sites
add constraint unique_tbl_sites_site_uuid unique (site_uuid);


alter table only public.tbl_species_associations
add constraint unique_tbl_species_associations_species_association_uuid unique (species_association_uuid);


alter table only public.tbl_taxa_synonyms
add constraint unique_tbl_taxa_synonyms_synonym_uuid unique (synonym_uuid);


alter table only public.tbl_taxonomic_order_systems
add constraint unique_tbl_taxonomic_order_systems_taxonomic_order_system_uuid unique (taxonomic_order_system_uuid);


alter table only public.tbl_taxonomy_notes
add constraint unique_tbl_taxonomy_notes_taxonomy_notes_uuid unique (taxonomy_notes_uuid);


alter table only public.tbl_tephras
add constraint unique_tbl_tephras_tephra_uuid unique (tephra_uuid);


alter table only public.tbl_text_biology
add constraint unique_tbl_text_biology_biology_uuid unique (biology_uuid);


alter table only public.tbl_text_distribution
add constraint unique_tbl_text_distribution_distribution_uuid unique (distribution_uuid);


alter table only public.tbl_text_identification_keys
add constraint unique_tbl_text_identification_keys_key_uuid unique (key_uuid);


alter table only public.tbl_site_references
add constraint uq_site_references unique (site_id, biblio_id);


alter table only public.tbl_site_site_types
add constraint uq_site_type_per_site unique (site_id, site_type_id);


alter table only public.tbl_sample_alt_refs
add constraint uq_tbl_sample_alt_refs unique (physical_sample_id, alt_ref, alt_ref_type_id);


alter table only public.tbl_abundance_elements
add constraint fk_abundance_elements_record_type_id foreign key (record_type_id) references public.tbl_record_types (
    record_type_id
) on update cascade;


alter table only public.tbl_abundance_ident_levels
add constraint fk_abundance_ident_levels_abundance_id foreign key (abundance_id) references public.tbl_abundances (
    abundance_id
);


alter table only public.tbl_abundance_ident_levels
add constraint fk_abundance_ident_levels_identification_level_id foreign key (
    identification_level_id
) references public.tbl_identification_levels (identification_level_id) on update cascade;


alter table only public.tbl_abundance_modifications
add constraint fk_abundance_modifications_abundance_id foreign key (abundance_id) references public.tbl_abundances (
    abundance_id
) on update cascade;


alter table only public.tbl_abundance_modifications
add constraint fk_abundance_modifications_modification_type_id foreign key (
    modification_type_id
) references public.tbl_modification_types (modification_type_id) on update cascade;


alter table only public.tbl_abundances
add constraint fk_abundances_abundance_elements_id foreign key (
    abundance_element_id
) references public.tbl_abundance_elements (abundance_element_id) on update cascade;


alter table only public.tbl_abundances
add constraint fk_abundances_analysis_entity_id foreign key (
    analysis_entity_id
) references public.tbl_analysis_entities (analysis_entity_id) on update cascade;


alter table only public.tbl_abundances
add constraint fk_abundances_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
) on update cascade on delete cascade;


alter table only public.tbl_aggregate_samples
add constraint fk_aggragate_samples_analysis_entity_id foreign key (
    analysis_entity_id
) references public.tbl_analysis_entities (analysis_entity_id) on update cascade;


alter table only public.tbl_aggregate_datasets
add constraint fk_aggregate_datasets_aggregate_order_type_id foreign key (
    aggregate_order_type_id
) references public.tbl_aggregate_order_types (aggregate_order_type_id) on update cascade;


alter table only public.tbl_aggregate_datasets
add constraint fk_aggregate_datasets_biblio_id foreign key (biblio_id) references public.tbl_biblio (
    biblio_id
) on update cascade;


alter table only public.tbl_aggregate_sample_ages
add constraint fk_aggregate_sample_ages_aggregate_dataset_id foreign key (
    aggregate_dataset_id
) references public.tbl_aggregate_datasets (aggregate_dataset_id) on update cascade;


alter table only public.tbl_aggregate_sample_ages
add constraint fk_aggregate_sample_ages_analysis_entity_age_id foreign key (
    analysis_entity_age_id
) references public.tbl_analysis_entity_ages (analysis_entity_age_id) on update cascade;


alter table only public.tbl_aggregate_samples
add constraint fk_aggregate_samples_aggregate_dataset_id foreign key (
    aggregate_dataset_id
) references public.tbl_aggregate_datasets (aggregate_dataset_id) on update cascade;


alter table only public.tbl_analysis_entities
add constraint fk_analysis_entities_dataset_id foreign key (dataset_id) references public.tbl_datasets (
    dataset_id
) on update cascade;


alter table only public.tbl_analysis_entities
add constraint fk_analysis_entities_physical_sample_id foreign key (
    physical_sample_id
) references public.tbl_physical_samples (physical_sample_id);


alter table only public.tbl_analysis_entity_ages
add constraint fk_analysis_entity_ages_analysis_entity_id foreign key (
    analysis_entity_id
) references public.tbl_analysis_entities (analysis_entity_id) on update cascade;


alter table only public.tbl_analysis_entity_ages
add constraint fk_analysis_entity_ages_chronology_id foreign key (chronology_id) references public.tbl_chronologies (
    chronology_id
) on update cascade;


alter table only public.tbl_analysis_entity_dimensions
add constraint fk_analysis_entity_dimensions_analysis_entity_id foreign key (
    analysis_entity_id
) references public.tbl_analysis_entities (analysis_entity_id) on update cascade on delete cascade;


alter table only public.tbl_analysis_entity_dimensions
add constraint fk_analysis_entity_dimensions_dimension_id foreign key (dimension_id) references public.tbl_dimensions (
    dimension_id
) on update cascade;


alter table only public.tbl_analysis_entity_prep_methods
add constraint fk_analysis_entity_prep_methods_analysis_entity_id foreign key (
    analysis_entity_id
) references public.tbl_analysis_entities (analysis_entity_id);


alter table only public.tbl_analysis_entity_prep_methods
add constraint fk_analysis_entity_prep_methods_method_id foreign key (method_id) references public.tbl_methods (
    method_id
);


alter table only public.tbl_ceramics
add constraint fk_ceramics_analysis_entity_id foreign key (
    analysis_entity_id
) references public.tbl_analysis_entities (analysis_entity_id);


alter table only public.tbl_ceramics
add constraint fk_ceramics_ceramics_lookup_id foreign key (ceramics_lookup_id) references public.tbl_ceramics_lookup (
    ceramics_lookup_id
);


alter table only public.tbl_ceramics_lookup
add constraint fk_ceramics_lookup_method_id foreign key (method_id) references public.tbl_methods (method_id);


alter table only public.tbl_ceramics_measurements
add constraint fk_ceramics_measurements_method_id foreign key (method_id) references public.tbl_methods (method_id);


alter table only public.tbl_chronologies
add constraint fk_chronologies_contact_id foreign key (contact_id) references public.tbl_contacts (
    contact_id
) on update cascade;


alter table only public.tbl_colours
add constraint fk_colours_method_id foreign key (method_id) references public.tbl_methods (method_id) on update cascade;


alter table only public.tbl_coordinate_method_dimensions
add constraint fk_coordinate_method_dimensions_dimensions_id foreign key (
    dimension_id
) references public.tbl_dimensions (dimension_id) on update cascade;


alter table only public.tbl_coordinate_method_dimensions
add constraint fk_coordinate_method_dimensions_method_id foreign key (method_id) references public.tbl_methods (
    method_id
) on update cascade;


alter table only public.tbl_data_types
add constraint fk_data_types_data_type_group_id foreign key (
    data_type_group_id
) references public.tbl_data_type_groups (data_type_group_id) on update cascade;


alter table only public.tbl_dataset_contacts
add constraint fk_dataset_contacts_contact_id foreign key (contact_id) references public.tbl_contacts (
    contact_id
) on update cascade;


alter table only public.tbl_dataset_contacts
add constraint fk_dataset_contacts_contact_type_id foreign key (contact_type_id) references public.tbl_contact_types (
    contact_type_id
) on update cascade;


alter table only public.tbl_dataset_contacts
add constraint fk_dataset_contacts_dataset_id foreign key (dataset_id) references public.tbl_datasets (
    dataset_id
) on update cascade;


alter table only public.tbl_dataset_masters
add constraint fk_dataset_masters_biblio_id foreign key (biblio_id) references public.tbl_biblio (biblio_id);


alter table only public.tbl_dataset_masters
add constraint fk_dataset_masters_contact_id foreign key (contact_id) references public.tbl_contacts (
    contact_id
) on update cascade;


alter table only public.tbl_dataset_submissions
add constraint fk_dataset_submission_submission_type_id foreign key (
    submission_type_id
) references public.tbl_dataset_submission_types (submission_type_id) on update cascade;


alter table only public.tbl_dataset_submissions
add constraint fk_dataset_submissions_contact_id foreign key (contact_id) references public.tbl_contacts (
    contact_id
) on update cascade;


alter table only public.tbl_dataset_submissions
add constraint fk_dataset_submissions_dataset_id foreign key (dataset_id) references public.tbl_datasets (
    dataset_id
) on update cascade;


alter table only public.tbl_datasets
add constraint fk_datasets_biblio_id foreign key (biblio_id) references public.tbl_biblio (biblio_id) on update cascade;


alter table only public.tbl_datasets
add constraint fk_datasets_data_type_id foreign key (data_type_id) references public.tbl_data_types (
    data_type_id
) on update cascade;


alter table only public.tbl_datasets
add constraint fk_datasets_master_set_id foreign key (master_set_id) references public.tbl_dataset_masters (
    master_set_id
) on update cascade;


alter table only public.tbl_datasets
add constraint fk_datasets_method_id foreign key (method_id) references public.tbl_methods (
    method_id
) on update cascade;


alter table only public.tbl_datasets
add constraint fk_datasets_project_id foreign key (project_id) references public.tbl_projects (project_id);


alter table only public.tbl_datasets
add constraint fk_datasets_updated_dataset_id foreign key (updated_dataset_id) references public.tbl_datasets (
    dataset_id
) on update cascade;


alter table only public.tbl_dating_labs
add constraint fk_dating_labs_contact_id foreign key (contact_id) references public.tbl_contacts (contact_id);


alter table only public.tbl_dating_material
add constraint fk_dating_material_abundance_elements_id foreign key (
    abundance_element_id
) references public.tbl_abundance_elements (abundance_element_id);


alter table only public.tbl_dating_material
add constraint fk_dating_material_geochronology_geochron_id foreign key (
    geochron_id
) references public.tbl_geochronology (geochron_id);


alter table only public.tbl_dating_material
add constraint fk_dating_material_taxa_tree_master_taxon_id foreign key (
    taxon_id
) references public.tbl_taxa_tree_master (taxon_id);


alter table only public.tbl_dendro
add constraint fk_dendro_analysis_entity_id foreign key (analysis_entity_id) references public.tbl_analysis_entities (
    analysis_entity_id
);


alter table only public.tbl_dendro_date_notes
add constraint fk_dendro_date_notes_dendro_date_id foreign key (dendro_date_id) references public.tbl_dendro_dates (
    dendro_date_id
);


alter table only public.tbl_dendro_dates
add constraint fk_dendro_dates_analysis_entity_id foreign key (
    analysis_entity_id
) references public.tbl_analysis_entities (analysis_entity_id);


alter table only public.tbl_dendro_dates
add constraint fk_dendro_dates_dating_uncertainty_id foreign key (
    dating_uncertainty_id
) references public.tbl_dating_uncertainty (dating_uncertainty_id);


alter table only public.tbl_dendro
add constraint fk_dendro_dendro_lookup_id foreign key (dendro_lookup_id) references public.tbl_dendro_lookup (
    dendro_lookup_id
);


alter table only public.tbl_dendro_dates
add constraint fk_dendro_lookup_dendro_lookup_id foreign key (dendro_lookup_id) references public.tbl_dendro_lookup (
    dendro_lookup_id
);


alter table only public.tbl_dendro_lookup
add constraint fk_dendro_lookup_method_id foreign key (method_id) references public.tbl_methods (method_id);


alter table only public.tbl_dimensions
add constraint fk_dimensions_method_group_id foreign key (method_group_id) references public.tbl_method_groups (
    method_group_id
);


alter table only public.tbl_dimensions
add constraint fk_dimensions_unit_id foreign key (unit_id) references public.tbl_units (unit_id) on update cascade;


alter table only public.tbl_ecocode_definitions
add constraint fk_ecocode_definitions_ecocode_group_id foreign key (
    ecocode_group_id
) references public.tbl_ecocode_groups (ecocode_group_id) on update cascade;


alter table only public.tbl_ecocode_groups
add constraint fk_ecocode_groups_ecocode_system_id foreign key (
    ecocode_system_id
) references public.tbl_ecocode_systems (ecocode_system_id) on update cascade;


alter table only public.tbl_ecocode_systems
add constraint fk_ecocode_systems_biblio_id foreign key (biblio_id) references public.tbl_biblio (
    biblio_id
) on update cascade;


alter table only public.tbl_ecocodes
add constraint fk_ecocodes_ecocodedef_id foreign key (
    ecocode_definition_id
) references public.tbl_ecocode_definitions (ecocode_definition_id) on update cascade;


alter table only public.tbl_ecocodes
add constraint fk_ecocodes_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
) on update cascade;


alter table only public.tbl_features
add constraint fk_feature_type_id_feature_type_id foreign key (feature_type_id) references public.tbl_feature_types (
    feature_type_id
) on update cascade on delete cascade;


alter table only public.tbl_geochron_refs
add constraint fk_geochron_refs_biblio_id foreign key (biblio_id) references public.tbl_biblio (
    biblio_id
) on update cascade;


alter table only public.tbl_geochron_refs
add constraint fk_geochron_refs_geochron_id foreign key (geochron_id) references public.tbl_geochronology (
    geochron_id
) on update cascade;


alter table only public.tbl_geochronology
add constraint fk_geochronology_analysis_entity_id foreign key (
    analysis_entity_id
) references public.tbl_analysis_entities (analysis_entity_id) on update cascade;


alter table only public.tbl_geochronology
add constraint fk_geochronology_dating_labs_id foreign key (dating_lab_id) references public.tbl_dating_labs (
    dating_lab_id
) on update cascade;


alter table only public.tbl_geochronology
add constraint fk_geochronology_dating_uncertainty_id foreign key (
    dating_uncertainty_id
) references public.tbl_dating_uncertainty (dating_uncertainty_id);


alter table only public.tbl_horizons
add constraint fk_horizons_method_id foreign key (method_id) references public.tbl_methods (
    method_id
) on update cascade;


alter table only public.tbl_imported_taxa_replacements
add constraint fk_imported_taxa_replacements_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
) on update cascade on delete cascade;


alter table only public.tbl_isotope_measurements
add constraint fk_isotope_isotope_type_id foreign key (isotope_type_id) references public.tbl_isotope_types (
    isotope_type_id
);


alter table only public.tbl_isotope_measurements
add constraint fk_isotope_measurements_isotope_standard_id foreign key (
    isotope_standard_id
) references public.tbl_isotope_standards (isotope_standard_id);


alter table only public.tbl_isotope_measurements
add constraint fk_isotope_method_id foreign key (method_id) references public.tbl_methods (method_id);


alter table only public.tbl_isotopes
add constraint fk_isotopes_analysis_entity_id foreign key (
    analysis_entity_id
) references public.tbl_analysis_entities (analysis_entity_id);


alter table only public.tbl_isotopes
add constraint fk_isotopes_isotope_measurement_id foreign key (
    isotope_measurement_id
) references public.tbl_isotope_measurements (isotope_measurement_id);


alter table only public.tbl_isotopes
add constraint fk_isotopes_isotope_standard_id foreign key (
    isotope_standard_id
) references public.tbl_isotope_standards (isotope_standard_id);


alter table only public.tbl_isotopes
add constraint fk_isotopes_isotope_value_specifier_id foreign key (
    isotope_value_specifier_id
) references public.tbl_isotope_value_specifiers (isotope_value_specifier_id);


alter table only public.tbl_isotopes
add constraint fk_isotopes_unit_id foreign key (unit_id) references public.tbl_units (unit_id);


alter table only public.tbl_lithology
add constraint fk_lithology_sample_group_id foreign key (sample_group_id) references public.tbl_sample_groups (
    sample_group_id
) on update cascade;


alter table only public.tbl_site_locations
add constraint fk_locations_location_id foreign key (location_id) references public.tbl_locations (location_id);


alter table only public.tbl_locations
add constraint fk_locations_location_type_id foreign key (location_type_id) references public.tbl_location_types (
    location_type_id
) on update cascade;


alter table only public.tbl_site_locations
add constraint fk_locations_site_id foreign key (site_id) references public.tbl_sites (site_id);


alter table only public.tbl_mcr_names
add constraint fk_mcr_names_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
) on update cascade;


alter table only public.tbl_mcr_summary_data
add constraint fk_mcr_summary_data_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
) on update cascade;


alter table only public.tbl_mcrdata_birmbeetledat
add constraint fk_mcrdata_birmbeetledat_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
) on update cascade;


alter table only public.tbl_measured_value_dimensions
add constraint fk_measured_value_dimensions_dimension_id foreign key (dimension_id) references public.tbl_dimensions (
    dimension_id
) on update cascade;


alter table only public.tbl_measured_values
add constraint fk_measured_values_analysis_entity_id foreign key (
    analysis_entity_id
) references public.tbl_analysis_entities (analysis_entity_id);


alter table only public.tbl_measured_value_dimensions
add constraint fk_measured_weights_value_id foreign key (measured_value_id) references public.tbl_measured_values (
    measured_value_id
) on update cascade;


alter table only public.tbl_methods
add constraint fk_methods_biblio_id foreign key (biblio_id) references public.tbl_biblio (biblio_id) on update cascade;


alter table only public.tbl_methods
add constraint fk_methods_method_group_id foreign key (method_group_id) references public.tbl_method_groups (
    method_group_id
) on update cascade;


alter table only public.tbl_methods
add constraint fk_methods_record_type_id foreign key (record_type_id) references public.tbl_record_types (
    record_type_id
) on update cascade;


alter table only public.tbl_methods
add constraint fk_methods_unit_id foreign key (unit_id) references public.tbl_units (unit_id) on update cascade;


alter table only public.tbl_physical_sample_features
add constraint fk_physical_sample_features_feature_id foreign key (feature_id) references public.tbl_features (
    feature_id
) on update cascade on delete cascade;


alter table only public.tbl_physical_sample_features
add constraint fk_physical_sample_features_physical_sample_id foreign key (
    physical_sample_id
) references public.tbl_physical_samples (physical_sample_id) on update cascade on delete cascade;


alter table only public.tbl_physical_samples
add constraint fk_physical_samples_sample_name_type_id foreign key (
    alt_ref_type_id
) references public.tbl_alt_ref_types (alt_ref_type_id) on update cascade;


alter table only public.tbl_physical_samples
add constraint fk_physical_samples_sample_type_id foreign key (sample_type_id) references public.tbl_sample_types (
    sample_type_id
) on update cascade;


alter table only public.tbl_projects
add constraint fk_projects_project_stage_id foreign key (project_stage_id) references public.tbl_project_stages (
    project_stage_id
);


alter table only public.tbl_projects
add constraint fk_projects_project_type_id foreign key (project_type_id) references public.tbl_project_types (
    project_type_id
);


alter table only public.tbl_rdb_codes
add constraint fk_rdb_codes_rdb_system_id foreign key (rdb_system_id) references public.tbl_rdb_systems (rdb_system_id);


alter table only public.tbl_rdb
add constraint fk_rdb_rdb_code_id foreign key (rdb_code_id) references public.tbl_rdb_codes (rdb_code_id);


alter table only public.tbl_rdb_systems
add constraint fk_rdb_systems_biblio_id foreign key (biblio_id) references public.tbl_biblio (
    biblio_id
) on update cascade;


alter table only public.tbl_rdb_systems
add constraint fk_rdb_systems_location_id foreign key (location_id) references public.tbl_locations (location_id);


alter table only public.tbl_rdb
add constraint fk_rdb_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
) on update cascade on delete cascade;


alter table only public.tbl_relative_age_refs
add constraint fk_relative_age_refs_biblio_id foreign key (biblio_id) references public.tbl_biblio (
    biblio_id
) on update cascade;


alter table only public.tbl_relative_age_refs
add constraint fk_relative_age_refs_relative_age_id foreign key (relative_age_id) references public.tbl_relative_ages (
    relative_age_id
) on update cascade;


alter table only public.tbl_relative_ages
add constraint fk_relative_ages_location_id foreign key (location_id) references public.tbl_locations (location_id);


alter table only public.tbl_relative_ages
add constraint fk_relative_ages_relative_age_type_id foreign key (
    relative_age_type_id
) references public.tbl_relative_age_types (relative_age_type_id);


alter table only public.tbl_relative_dates
add constraint fk_relative_dates_dating_uncertainty_id foreign key (
    dating_uncertainty_id
) references public.tbl_dating_uncertainty (dating_uncertainty_id);


alter table only public.tbl_relative_dates
add constraint fk_relative_dates_method_id foreign key (method_id) references public.tbl_methods (method_id);


alter table only public.tbl_relative_dates
add constraint fk_relative_dates_relative_age_id foreign key (relative_age_id) references public.tbl_relative_ages (
    relative_age_id
) on update cascade;


alter table only public.tbl_sample_alt_refs
add constraint fk_sample_alt_refs_alt_ref_type_id foreign key (alt_ref_type_id) references public.tbl_alt_ref_types (
    alt_ref_type_id
) on update cascade;


alter table only public.tbl_sample_alt_refs
add constraint fk_sample_alt_refs_physical_sample_id foreign key (
    physical_sample_id
) references public.tbl_physical_samples (physical_sample_id) on update cascade;


alter table only public.tbl_sample_colours
add constraint fk_sample_colours_colour_id foreign key (colour_id) references public.tbl_colours (
    colour_id
) on update cascade;


alter table only public.tbl_sample_colours
add constraint fk_sample_colours_physical_sample_id foreign key (
    physical_sample_id
) references public.tbl_physical_samples (physical_sample_id) on update cascade;


alter table only public.tbl_sample_coordinates
add constraint fk_sample_coordinates_coordinate_method_dimension_id foreign key (
    coordinate_method_dimension_id
) references public.tbl_coordinate_method_dimensions (coordinate_method_dimension_id) on update cascade;


alter table only public.tbl_sample_coordinates
add constraint fk_sample_coordinates_physical_sample_id foreign key (
    physical_sample_id
) references public.tbl_physical_samples (physical_sample_id);


alter table only public.tbl_sample_description_sample_group_contexts
add constraint fk_sample_description_sample_group_contexts_sampling_context_id foreign key (
    sampling_context_id
) references public.tbl_sample_group_sampling_contexts (sampling_context_id);


alter table only public.tbl_sample_description_sample_group_contexts
add constraint fk_sample_description_types_sample_group_context_id foreign key (
    sample_description_type_id
) references public.tbl_sample_description_types (sample_description_type_id);


alter table only public.tbl_sample_descriptions
add constraint fk_sample_descriptions_physical_sample_id foreign key (
    physical_sample_id
) references public.tbl_physical_samples (physical_sample_id);


alter table only public.tbl_sample_descriptions
add constraint fk_sample_descriptions_sample_description_type_id foreign key (
    sample_description_type_id
) references public.tbl_sample_description_types (sample_description_type_id);


alter table only public.tbl_sample_dimensions
add constraint fk_sample_dimensions_dimension_id foreign key (dimension_id) references public.tbl_dimensions (
    dimension_id
) on update cascade;


alter table only public.tbl_sample_dimensions
add constraint fk_sample_dimensions_measurement_method_id foreign key (method_id) references public.tbl_methods (
    method_id
) on update cascade;


alter table only public.tbl_sample_dimensions
add constraint fk_sample_dimensions_physical_sample_id foreign key (
    physical_sample_id
) references public.tbl_physical_samples (physical_sample_id) on update cascade;


alter table only public.tbl_sample_group_description_type_sampling_contexts
add constraint fk_sample_group_description_type_sampling_context_id foreign key (
    sample_group_description_type_id
) references public.tbl_sample_group_description_types (sample_group_description_type_id);


alter table only public.tbl_sample_group_descriptions
add constraint fk_sample_group_descriptions_sample_group_description_type_id foreign key (
    sample_group_description_type_id
) references public.tbl_sample_group_description_types (sample_group_description_type_id) on update cascade;


alter table only public.tbl_sample_group_dimensions
add constraint fk_sample_group_dimensions_dimension_id foreign key (dimension_id) references public.tbl_dimensions (
    dimension_id
) on update cascade;


alter table only public.tbl_sample_group_dimensions
add constraint fk_sample_group_dimensions_sample_group_id foreign key (
    sample_group_id
) references public.tbl_sample_groups (sample_group_id) on update cascade;


alter table only public.tbl_sample_group_images
add constraint fk_sample_group_images_image_type_id foreign key (image_type_id) references public.tbl_image_types (
    image_type_id
) on update cascade;


alter table only public.tbl_sample_group_images
add constraint fk_sample_group_images_sample_group_id foreign key (
    sample_group_id
) references public.tbl_sample_groups (sample_group_id);


alter table only public.tbl_sample_group_coordinates
add constraint fk_sample_group_positions_coordinate_method_dimension_id foreign key (
    coordinate_method_dimension_id
) references public.tbl_coordinate_method_dimensions (coordinate_method_dimension_id) on update cascade;


alter table only public.tbl_sample_group_coordinates
add constraint fk_sample_group_positions_sample_group_id foreign key (
    sample_group_id
) references public.tbl_sample_groups (sample_group_id);


alter table only public.tbl_sample_group_references
add constraint fk_sample_group_references_biblio_id foreign key (biblio_id) references public.tbl_biblio (
    biblio_id
) on update cascade;


alter table only public.tbl_sample_group_references
add constraint fk_sample_group_references_sample_group_id foreign key (
    sample_group_id
) references public.tbl_sample_groups (sample_group_id) on update cascade;


alter table only public.tbl_sample_groups
add constraint fk_sample_group_sampling_context_id foreign key (
    sampling_context_id
) references public.tbl_sample_group_sampling_contexts (sampling_context_id) on update cascade;


alter table only public.tbl_sample_group_description_type_sampling_contexts
add constraint fk_sample_group_sampling_context_id0 foreign key (
    sampling_context_id
) references public.tbl_sample_group_sampling_contexts (sampling_context_id);


alter table only public.tbl_sample_groups
add constraint fk_sample_groups_method_id foreign key (method_id) references public.tbl_methods (
    method_id
) on update cascade;


alter table only public.tbl_sample_group_descriptions
add constraint fk_sample_groups_sample_group_descriptions_id foreign key (
    sample_group_id
) references public.tbl_sample_groups (sample_group_id) on update cascade;


alter table only public.tbl_sample_groups
add constraint fk_sample_groups_site_id foreign key (site_id) references public.tbl_sites (site_id) on update cascade;


alter table only public.tbl_sample_horizons
add constraint fk_sample_horizons_horizon_id foreign key (horizon_id) references public.tbl_horizons (
    horizon_id
) on update cascade;


alter table only public.tbl_sample_horizons
add constraint fk_sample_horizons_physical_sample_id foreign key (
    physical_sample_id
) references public.tbl_physical_samples (physical_sample_id) on update cascade;


alter table only public.tbl_sample_images
add constraint fk_sample_images_image_type_id foreign key (image_type_id) references public.tbl_image_types (
    image_type_id
) on update cascade;


alter table only public.tbl_sample_images
add constraint fk_sample_images_physical_sample_id foreign key (
    physical_sample_id
) references public.tbl_physical_samples (physical_sample_id) on update cascade;


alter table only public.tbl_sample_location_type_sampling_contexts
add constraint fk_sample_location_sampling_contexts_sampling_context_id foreign key (
    sample_location_type_id
) references public.tbl_sample_location_types (sample_location_type_id);


alter table only public.tbl_sample_location_type_sampling_contexts
add constraint fk_sample_location_type_sampling_context_id foreign key (
    sampling_context_id
) references public.tbl_sample_group_sampling_contexts (sampling_context_id);


alter table only public.tbl_sample_locations
add constraint fk_sample_locations_physical_sample_id foreign key (
    physical_sample_id
) references public.tbl_physical_samples (physical_sample_id);


alter table only public.tbl_sample_locations
add constraint fk_sample_locations_sample_location_type_id foreign key (
    sample_location_type_id
) references public.tbl_sample_location_types (sample_location_type_id);


alter table only public.tbl_sample_notes
add constraint fk_sample_notes_physical_sample_id foreign key (
    physical_sample_id
) references public.tbl_physical_samples (physical_sample_id) on update cascade;


alter table only public.tbl_physical_samples
add constraint fk_samples_sample_group_id foreign key (sample_group_id) references public.tbl_sample_groups (
    sample_group_id
) on update cascade;


alter table only public.tbl_seasons
add constraint fk_seasons_season_type_id foreign key (season_type_id) references public.tbl_season_types (
    season_type_id
) on update cascade;


alter table only public.tbl_site_images
add constraint fk_site_images_contact_id foreign key (contact_id) references public.tbl_contacts (
    contact_id
) on update cascade;


alter table only public.tbl_site_images
add constraint fk_site_images_image_type_id foreign key (image_type_id) references public.tbl_image_types (
    image_type_id
) on update cascade;


alter table only public.tbl_site_images
add constraint fk_site_images_site_id foreign key (site_id) references public.tbl_sites (site_id);


alter table only public.tbl_site_natgridrefs
add constraint fk_site_natgridrefs_method_id foreign key (method_id) references public.tbl_methods (method_id);


alter table only public.tbl_site_natgridrefs
add constraint fk_site_natgridrefs_sites_id foreign key (site_id) references public.tbl_sites (site_id);


alter table only public.tbl_site_other_records
add constraint fk_site_other_records_biblio_id foreign key (biblio_id) references public.tbl_biblio (
    biblio_id
) on update cascade;


alter table only public.tbl_site_other_records
add constraint fk_site_other_records_record_type_id foreign key (record_type_id) references public.tbl_record_types (
    record_type_id
) on update cascade;


alter table only public.tbl_site_other_records
add constraint fk_site_other_records_site_id foreign key (site_id) references public.tbl_sites (
    site_id
) on update cascade;


alter table only public.tbl_site_preservation_status
add constraint "fk_site_preservation_status_site_id " foreign key (site_id) references public.tbl_sites (
    site_id
) on update cascade;


alter table only public.tbl_sites
add constraint fk_site_preservation_status_site_preservation_status_id foreign key (
    site_preservation_status_id
) references public.tbl_site_preservation_status (site_preservation_status_id) on update cascade;


alter table only public.tbl_site_references
add constraint fk_site_references_biblio_id foreign key (biblio_id) references public.tbl_biblio (
    biblio_id
) on update cascade;


alter table only public.tbl_site_references
add constraint fk_site_references_site_id foreign key (site_id) references public.tbl_sites (site_id) on update cascade;


alter table only public.tbl_species_associations
add constraint fk_species_associations_associated_taxon_id foreign key (
    taxon_id
) references public.tbl_taxa_tree_master (taxon_id) on update cascade;


alter table only public.tbl_species_associations
add constraint fk_species_associations_association_type_id foreign key (
    association_type_id
) references public.tbl_species_association_types (association_type_id);


alter table only public.tbl_species_associations
add constraint fk_species_associations_biblio_id foreign key (biblio_id) references public.tbl_biblio (
    biblio_id
) on update cascade;


alter table only public.tbl_species_associations
add constraint fk_species_associations_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
);


alter table only public.tbl_taxa_common_names
add constraint fk_taxa_common_names_language_id foreign key (language_id) references public.tbl_languages (
    language_id
) on update cascade;


alter table only public.tbl_taxa_common_names
add constraint fk_taxa_common_names_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
) on update cascade;


alter table only public.tbl_taxa_images
add constraint fk_taxa_images_image_type_id foreign key (image_type_id) references public.tbl_image_types (
    image_type_id
);


alter table only public.tbl_taxa_images
add constraint fk_taxa_images_taxa_tree_master_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
);


alter table only public.tbl_taxa_measured_attributes
add constraint fk_taxa_measured_attributes_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
) on update cascade on delete cascade;


alter table only public.tbl_taxa_reference_specimens
add constraint fk_taxa_reference_specimens_contact_id foreign key (contact_id) references public.tbl_contacts (
    contact_id
);


alter table only public.tbl_taxa_reference_specimens
add constraint fk_taxa_reference_specimens_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
);


alter table only public.tbl_taxa_seasonality
add constraint fk_taxa_seasonality_activity_type_id foreign key (
    activity_type_id
) references public.tbl_activity_types (activity_type_id) on update cascade;


alter table only public.tbl_taxa_seasonality
add constraint fk_taxa_seasonality_location_id foreign key (location_id) references public.tbl_locations (location_id);


alter table only public.tbl_taxa_seasonality
add constraint fk_taxa_seasonality_season_id foreign key (season_id) references public.tbl_seasons (
    season_id
) on update cascade;


alter table only public.tbl_taxa_seasonality
add constraint fk_taxa_seasonality_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
) on update cascade on delete cascade;


alter table only public.tbl_taxa_synonyms
add constraint fk_taxa_synonyms_biblio_id foreign key (biblio_id) references public.tbl_biblio (
    biblio_id
) on update cascade;


alter table only public.tbl_taxa_synonyms
add constraint fk_taxa_synonyms_family_id foreign key (family_id) references public.tbl_taxa_tree_families (
    family_id
) on update cascade;


alter table only public.tbl_taxa_synonyms
add constraint fk_taxa_synonyms_genus_id foreign key (genus_id) references public.tbl_taxa_tree_genera (
    genus_id
) on update cascade;


alter table only public.tbl_taxa_synonyms
add constraint fk_taxa_synonyms_taxa_tree_author_id foreign key (author_id) references public.tbl_taxa_tree_authors (
    author_id
);


alter table only public.tbl_taxa_synonyms
add constraint fk_taxa_synonyms_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
) on update cascade on delete cascade;


alter table only public.tbl_taxa_tree_families
add constraint fk_taxa_tree_families_order_id foreign key (order_id) references public.tbl_taxa_tree_orders (
    order_id
) on update cascade on delete cascade;


alter table only public.tbl_taxa_tree_genera
add constraint fk_taxa_tree_genera_family_id foreign key (family_id) references public.tbl_taxa_tree_families (
    family_id
) on update cascade on delete cascade;


alter table only public.tbl_taxa_tree_master
add constraint fk_taxa_tree_master_author_id foreign key (author_id) references public.tbl_taxa_tree_authors (
    author_id
) on update cascade;


alter table only public.tbl_taxa_tree_master
add constraint fk_taxa_tree_master_genus_id foreign key (genus_id) references public.tbl_taxa_tree_genera (
    genus_id
) on update cascade on delete cascade;


alter table only public.tbl_taxa_tree_orders
add constraint fk_taxa_tree_orders_record_type_id foreign key (record_type_id) references public.tbl_record_types (
    record_type_id
) on update cascade;


alter table only public.tbl_taxonomic_order_biblio
add constraint fk_taxonomic_order_biblio_biblio_id foreign key (biblio_id) references public.tbl_biblio (
    biblio_id
) on update cascade;


alter table only public.tbl_taxonomic_order_biblio
add constraint fk_taxonomic_order_biblio_taxonomic_order_system_id foreign key (
    taxonomic_order_system_id
) references public.tbl_taxonomic_order_systems (taxonomic_order_system_id) on update cascade;


alter table only public.tbl_taxonomic_order
add constraint fk_taxonomic_order_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
) on update cascade on delete cascade;


alter table only public.tbl_taxonomic_order
add constraint fk_taxonomic_order_taxonomic_order_system_id foreign key (
    taxonomic_order_system_id
) references public.tbl_taxonomic_order_systems (taxonomic_order_system_id) on update cascade;


alter table only public.tbl_taxonomy_notes
add constraint fk_taxonomy_notes_biblio_id foreign key (biblio_id) references public.tbl_biblio (
    biblio_id
) on update cascade;


alter table only public.tbl_taxonomy_notes
add constraint fk_taxonomy_notes_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
) on update cascade on delete cascade;


alter table only public.tbl_dendro_dates
add constraint fk_tbl_age_types_age_type_id foreign key (age_type_id) references public.tbl_age_types (age_type_id);


alter table only public.tbl_dataset_methods
add constraint fk_tbl_dataset_methods_to_tbl_datasets foreign key (dataset_id) references public.tbl_datasets (
    dataset_id
);


alter table only public.tbl_dataset_methods
add constraint fk_tbl_dataset_methods_to_tbl_methods foreign key (method_id) references public.tbl_methods (method_id);


alter table only public.tbl_rdb
add constraint fk_tbl_rdb_tbl_location_id foreign key (location_id) references public.tbl_locations (location_id);


alter table only public.tbl_relative_dates
add constraint fk_tbl_relative_dates_to_tbl_analysis_entities foreign key (
    analysis_entity_id
) references public.tbl_analysis_entities (analysis_entity_id);


alter table only public.tbl_sample_group_notes
add constraint fk_tbl_sample_group_notes_sample_groups foreign key (
    sample_group_id
) references public.tbl_sample_groups (sample_group_id) on update cascade;


alter table only public.tbl_tephra_dates
add constraint fk_tephra_dates_analysis_entity_id foreign key (
    analysis_entity_id
) references public.tbl_analysis_entities (analysis_entity_id) on update cascade;


alter table only public.tbl_tephra_dates
add constraint fk_tephra_dates_dating_uncertainty_id foreign key (
    dating_uncertainty_id
) references public.tbl_dating_uncertainty (dating_uncertainty_id);


alter table only public.tbl_tephra_dates
add constraint fk_tephra_dates_tephra_id foreign key (tephra_id) references public.tbl_tephras (
    tephra_id
) on update cascade;


alter table only public.tbl_tephra_refs
add constraint fk_tephra_refs_biblio_id foreign key (biblio_id) references public.tbl_biblio (
    biblio_id
) on update cascade;


alter table only public.tbl_tephra_refs
add constraint fk_tephra_refs_tephra_id foreign key (tephra_id) references public.tbl_tephras (
    tephra_id
) on update cascade;


alter table only public.tbl_text_biology
add constraint fk_text_biology_biblio_id foreign key (biblio_id) references public.tbl_biblio (
    biblio_id
) on update cascade;


alter table only public.tbl_text_biology
add constraint fk_text_biology_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
) on update cascade on delete cascade;


alter table only public.tbl_text_distribution
add constraint fk_text_distribution_biblio_id foreign key (biblio_id) references public.tbl_biblio (
    biblio_id
) on update cascade;


alter table only public.tbl_text_distribution
add constraint fk_text_distribution_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
) on update cascade on delete cascade;


alter table only public.tbl_text_identification_keys
add constraint fk_text_identification_keys_biblio_id foreign key (biblio_id) references public.tbl_biblio (
    biblio_id
) on update cascade;


alter table only public.tbl_text_identification_keys
add constraint fk_text_identification_keys_taxon_id foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
) on update cascade on delete cascade;


alter table only public.tbl_abundance_properties
add constraint tbl_abundance_properties_abundance_id_fkey foreign key (abundance_id) references public.tbl_abundances (
    abundance_id
) on delete cascade;


alter table only public.tbl_abundance_properties
add constraint tbl_abundance_properties_property_type_id_fkey foreign key (
    property_type_id
) references public.tbl_property_types (property_type_id) on delete cascade;


alter table only public.tbl_analysis_boolean_values
add constraint tbl_analysis_boolean_values_analysis_value_id_fkey foreign key (
    analysis_value_id
) references public.tbl_analysis_values (analysis_value_id) on delete cascade;


alter table only public.tbl_analysis_categorical_values
add constraint tbl_analysis_categorical_values_analysis_value_id_fkey foreign key (
    analysis_value_id
) references public.tbl_analysis_values (analysis_value_id) on delete cascade;


alter table only public.tbl_analysis_categorical_values
add constraint tbl_analysis_categorical_values_value_type_item_id_fkey foreign key (
    value_type_item_id
) references public.tbl_value_type_items (value_type_item_id);


alter table only public.tbl_analysis_dating_ranges
add constraint tbl_analysis_dating_ranges_age_type_id_fkey foreign key (age_type_id) references public.tbl_age_types (
    age_type_id
);


alter table only public.tbl_analysis_dating_ranges
add constraint tbl_analysis_dating_ranges_analysis_value_id_fkey foreign key (
    analysis_value_id
) references public.tbl_analysis_values (analysis_value_id) on delete cascade;


alter table only public.tbl_analysis_dating_ranges
add constraint tbl_analysis_dating_ranges_dating_uncertainty_id_fkey foreign key (
    dating_uncertainty_id
) references public.tbl_dating_uncertainty (dating_uncertainty_id);


alter table only public.tbl_analysis_dating_ranges
add constraint tbl_analysis_dating_ranges_high_qualifier_fkey foreign key (
    high_qualifier
) references public.tbl_value_qualifier_symbols (symbol);


alter table only public.tbl_analysis_dating_ranges
add constraint tbl_analysis_dating_ranges_low_qualifier_fkey foreign key (
    low_qualifier
) references public.tbl_value_qualifier_symbols (symbol);


alter table only public.tbl_analysis_dating_ranges
add constraint tbl_analysis_dating_ranges_season_id_fkey foreign key (season_id) references public.tbl_seasons (
    season_id
);


alter table only public.tbl_analysis_identifiers
add constraint tbl_analysis_identifiers_analysis_value_id_fkey foreign key (
    analysis_value_id
) references public.tbl_analysis_values (analysis_value_id) on delete cascade;


alter table only public.tbl_analysis_integer_ranges
add constraint tbl_analysis_integer_ranges_analysis_value_id_fkey foreign key (
    analysis_value_id
) references public.tbl_analysis_values (analysis_value_id) on delete cascade;


alter table only public.tbl_analysis_integer_ranges
add constraint tbl_analysis_integer_ranges_high_qualifier_fkey foreign key (
    high_qualifier
) references public.tbl_value_qualifier_symbols (symbol);


alter table only public.tbl_analysis_integer_ranges
add constraint tbl_analysis_integer_ranges_low_qualifier_fkey foreign key (
    low_qualifier
) references public.tbl_value_qualifier_symbols (symbol);


alter table only public.tbl_analysis_integer_values
add constraint tbl_analysis_integer_values_analysis_value_id_fkey foreign key (
    analysis_value_id
) references public.tbl_analysis_values (analysis_value_id) on delete cascade;


alter table only public.tbl_analysis_integer_values
add constraint tbl_analysis_integer_values_qualifier_fkey foreign key (
    qualifier
) references public.tbl_value_qualifier_symbols (symbol);


alter table only public.tbl_analysis_notes
add constraint tbl_analysis_notes_analysis_value_id_fkey foreign key (
    analysis_value_id
) references public.tbl_analysis_values (analysis_value_id) on delete cascade;


alter table only public.tbl_analysis_numerical_ranges
add constraint tbl_analysis_numerical_ranges_analysis_value_id_fkey foreign key (
    analysis_value_id
) references public.tbl_analysis_values (analysis_value_id) on delete cascade;


alter table only public.tbl_analysis_numerical_ranges
add constraint tbl_analysis_numerical_ranges_high_qualifier_fkey foreign key (
    high_qualifier
) references public.tbl_value_qualifier_symbols (symbol);


alter table only public.tbl_analysis_numerical_ranges
add constraint tbl_analysis_numerical_ranges_low_qualifier_fkey foreign key (
    low_qualifier
) references public.tbl_value_qualifier_symbols (symbol);


alter table only public.tbl_analysis_numerical_values
add constraint tbl_analysis_numerical_values_analysis_value_id_fkey foreign key (
    analysis_value_id
) references public.tbl_analysis_values (analysis_value_id) on delete cascade;


alter table only public.tbl_analysis_numerical_values
add constraint tbl_analysis_numerical_values_qualifier_fkey foreign key (
    qualifier
) references public.tbl_value_qualifier_symbols (symbol);


alter table only public.tbl_analysis_taxon_counts
add constraint tbl_analysis_taxon_counts_analysis_value_id_fkey foreign key (
    analysis_value_id
) references public.tbl_analysis_values (analysis_value_id) on delete cascade;


alter table only public.tbl_analysis_taxon_counts
add constraint tbl_analysis_taxon_counts_taxon_id_fkey foreign key (taxon_id) references public.tbl_taxa_tree_master (
    taxon_id
);


alter table only public.tbl_analysis_value_dimensions
add constraint tbl_analysis_value_dimensions_analysis_value_id_fkey foreign key (
    analysis_value_id
) references public.tbl_analysis_values (analysis_value_id) on delete cascade;


alter table only public.tbl_analysis_value_dimensions
add constraint tbl_analysis_value_dimensions_dimension_id_fkey foreign key (
    dimension_id
) references public.tbl_dimensions (dimension_id);


alter table only public.tbl_analysis_values
add constraint tbl_analysis_values_analysis_entity_id_fkey foreign key (
    analysis_entity_id
) references public.tbl_analysis_entities (analysis_entity_id) on delete cascade;


alter table only public.tbl_analysis_values
add constraint tbl_analysis_values_value_class_id_fkey foreign key (
    value_class_id
) references public.tbl_value_classes (value_class_id);


alter table only public.tbl_property_types
add constraint tbl_property_types_value_class_id_fkey foreign key (
    value_class_id
) references public.tbl_value_classes (value_class_id) on delete cascade;


alter table only public.tbl_property_types
add constraint tbl_property_types_value_type_id_fkey foreign key (value_type_id) references public.tbl_value_types (
    value_type_id
) on delete cascade;


alter table only public.tbl_sample_dimensions
add constraint tbl_sample_dimensions_qualifier_id_fkey foreign key (
    qualifier_id
) references public.tbl_value_qualifiers (qualifier_id);


alter table only public.tbl_sample_group_dimensions
add constraint tbl_sample_group_dimensions_qualifier_id_fkey foreign key (
    qualifier_id
) references public.tbl_value_qualifiers (qualifier_id);


alter table only public.tbl_site_properties
add constraint tbl_site_properties_property_type_id_fkey foreign key (
    property_type_id
) references public.tbl_property_types (property_type_id) on delete cascade;


alter table only public.tbl_site_properties
add constraint tbl_site_properties_site_id_fkey foreign key (site_id) references public.tbl_sites (
    site_id
) on delete cascade;


alter table only public.tbl_site_site_types
add constraint tbl_site_site_types_site_id_fkey foreign key (site_id) references public.tbl_sites (
    site_id
) on update cascade on delete cascade;


alter table only public.tbl_site_site_types
add constraint tbl_site_site_types_site_type_id_fkey foreign key (site_type_id) references public.tbl_site_types (
    site_type_id
) on update cascade on delete restrict;


alter table only public.tbl_site_types
add constraint tbl_site_types_site_type_group_id_fkey foreign key (
    site_type_group_id
) references public.tbl_site_type_groups (site_type_group_id) on update cascade on delete restrict;


alter table only public.tbl_value_classes
add constraint tbl_value_classes_method_id_fkey foreign key (method_id) references public.tbl_methods (method_id);


alter table only public.tbl_value_classes
add constraint tbl_value_classes_parent_id_fkey foreign key (parent_id) references public.tbl_value_classes (
    value_class_id
);


alter table only public.tbl_value_classes
add constraint tbl_value_classes_value_type_id_fkey foreign key (value_type_id) references public.tbl_value_types (
    value_type_id
);


alter table only public.tbl_value_qualifier_symbols
add constraint tbl_value_qualifier_symbols_cardinal_qualifier_id_fkey foreign key (
    cardinal_qualifier_id
) references public.tbl_value_qualifiers (qualifier_id);


alter table only public.tbl_value_type_items
add constraint tbl_value_type_items_value_type_id_fkey foreign key (value_type_id) references public.tbl_value_types (
    value_type_id
) on delete cascade;


alter table only public.tbl_value_types
add constraint tbl_value_types_data_type_id_fkey foreign key (data_type_id) references public.tbl_data_types (
    data_type_id
);


alter table only public.tbl_value_types
add constraint tbl_value_types_unit_id_fkey foreign key (unit_id) references public.tbl_units (unit_id);
