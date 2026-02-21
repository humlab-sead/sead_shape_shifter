
ALTER TABLE ONLY public.tbl_abundance_elements
    ADD CONSTRAINT tbl_abundance_elements_pkey PRIMARY KEY (abundance_element_id);


ALTER TABLE ONLY public.tbl_abundance_ident_levels
    ADD CONSTRAINT tbl_abundance_ident_levels_pkey PRIMARY KEY (abundance_ident_level_id);


ALTER TABLE ONLY public.tbl_abundance_modifications
    ADD CONSTRAINT tbl_abundance_modifications_pkey PRIMARY KEY (abundance_modification_id);


ALTER TABLE ONLY public.tbl_abundance_properties
    ADD CONSTRAINT tbl_abundance_properties_pkey PRIMARY KEY (abundance_property_id);


ALTER TABLE ONLY public.tbl_abundances
    ADD CONSTRAINT tbl_abundances_pkey PRIMARY KEY (abundance_id);


ALTER TABLE ONLY public.tbl_activity_types
    ADD CONSTRAINT tbl_activity_types_activity_type_key UNIQUE (activity_type);


ALTER TABLE ONLY public.tbl_activity_types
    ADD CONSTRAINT tbl_activity_types_activity_type_unique UNIQUE (activity_type);


ALTER TABLE ONLY public.tbl_activity_types
    ADD CONSTRAINT tbl_activity_types_pkey PRIMARY KEY (activity_type_id);


ALTER TABLE ONLY public.tbl_age_types
    ADD CONSTRAINT tbl_age_types_pkey PRIMARY KEY (age_type_id);


ALTER TABLE ONLY public.tbl_aggregate_datasets
    ADD CONSTRAINT tbl_aggregate_datasets_pkey PRIMARY KEY (aggregate_dataset_id);


ALTER TABLE ONLY public.tbl_aggregate_order_types
    ADD CONSTRAINT tbl_aggregate_order_types_aggregate_order_type_key UNIQUE (aggregate_order_type);


ALTER TABLE ONLY public.tbl_aggregate_order_types
    ADD CONSTRAINT tbl_aggregate_order_types_aggregate_order_type_unique UNIQUE (aggregate_order_type);


ALTER TABLE ONLY public.tbl_aggregate_order_types
    ADD CONSTRAINT tbl_aggregate_order_types_pkey PRIMARY KEY (aggregate_order_type_id);


ALTER TABLE ONLY public.tbl_aggregate_sample_ages
    ADD CONSTRAINT tbl_aggregate_sample_ages_pkey PRIMARY KEY (aggregate_sample_age_id);


ALTER TABLE ONLY public.tbl_aggregate_samples
    ADD CONSTRAINT tbl_aggregate_samples_pkey PRIMARY KEY (aggregate_sample_id);


ALTER TABLE ONLY public.tbl_alt_ref_types
    ADD CONSTRAINT tbl_alt_ref_types_alt_ref_type_key UNIQUE (alt_ref_type);


ALTER TABLE ONLY public.tbl_alt_ref_types
    ADD CONSTRAINT tbl_alt_ref_types_alt_ref_type_unique UNIQUE (alt_ref_type);


ALTER TABLE ONLY public.tbl_alt_ref_types
    ADD CONSTRAINT tbl_alt_ref_types_pkey PRIMARY KEY (alt_ref_type_id);


ALTER TABLE ONLY public.tbl_analysis_boolean_values
    ADD CONSTRAINT tbl_analysis_boolean_values_analysis_value_id_key UNIQUE (analysis_value_id);


ALTER TABLE ONLY public.tbl_analysis_boolean_values
    ADD CONSTRAINT tbl_analysis_boolean_values_pkey PRIMARY KEY (analysis_boolean_value_id);


ALTER TABLE ONLY public.tbl_analysis_categorical_values
    ADD CONSTRAINT tbl_analysis_categorical_values_pkey PRIMARY KEY (analysis_categorical_value_id);


ALTER TABLE ONLY public.tbl_analysis_dating_ranges
    ADD CONSTRAINT tbl_analysis_dating_ranges_pkey PRIMARY KEY (analysis_dating_range_id);


ALTER TABLE ONLY public.tbl_analysis_entities
    ADD CONSTRAINT tbl_analysis_entities_pkey PRIMARY KEY (analysis_entity_id);


ALTER TABLE ONLY public.tbl_analysis_entity_ages
    ADD CONSTRAINT tbl_analysis_entity_ages_pkey PRIMARY KEY (analysis_entity_age_id);


ALTER TABLE ONLY public.tbl_analysis_entity_dimensions
    ADD CONSTRAINT tbl_analysis_entity_dimensions_pkey PRIMARY KEY (analysis_entity_dimension_id);


ALTER TABLE ONLY public.tbl_analysis_entity_prep_methods
    ADD CONSTRAINT tbl_analysis_entity_prep_methods_pkey PRIMARY KEY (analysis_entity_prep_method_id);


ALTER TABLE ONLY public.tbl_analysis_identifiers
    ADD CONSTRAINT tbl_analysis_identifiers_pkey PRIMARY KEY (analysis_identifier_id);


ALTER TABLE ONLY public.tbl_analysis_integer_ranges
    ADD CONSTRAINT tbl_analysis_integer_ranges_pkey PRIMARY KEY (analysis_integer_range_id);


ALTER TABLE ONLY public.tbl_analysis_integer_values
    ADD CONSTRAINT tbl_analysis_integer_values_pkey PRIMARY KEY (analysis_integer_value_id);


ALTER TABLE ONLY public.tbl_analysis_notes
    ADD CONSTRAINT tbl_analysis_notes_pkey PRIMARY KEY (analysis_note_id);


ALTER TABLE ONLY public.tbl_analysis_numerical_ranges
    ADD CONSTRAINT tbl_analysis_numerical_ranges_pkey PRIMARY KEY (analysis_numerical_range_id);


ALTER TABLE ONLY public.tbl_analysis_numerical_values
    ADD CONSTRAINT tbl_analysis_numerical_values_pkey PRIMARY KEY (analysis_numerical_value_id);


ALTER TABLE ONLY public.tbl_analysis_taxon_counts
    ADD CONSTRAINT tbl_analysis_taxon_counts_pkey PRIMARY KEY (analysis_taxon_count_id);


ALTER TABLE ONLY public.tbl_analysis_value_dimensions
    ADD CONSTRAINT tbl_analysis_value_dimensions_pkey PRIMARY KEY (analysis_value_dimension_id);


ALTER TABLE ONLY public.tbl_analysis_values
    ADD CONSTRAINT tbl_analysis_values_pkey PRIMARY KEY (analysis_value_id);


ALTER TABLE ONLY public.tbl_biblio
    ADD CONSTRAINT tbl_biblio_pkey PRIMARY KEY (biblio_id);


ALTER TABLE ONLY public.tbl_ceramics_lookup
    ADD CONSTRAINT tbl_ceramics_lookup_pkey PRIMARY KEY (ceramics_lookup_id);


ALTER TABLE ONLY public.tbl_ceramics_measurements
    ADD CONSTRAINT tbl_ceramics_measurements_pkey PRIMARY KEY (ceramics_measurement_id);


ALTER TABLE ONLY public.tbl_ceramics
    ADD CONSTRAINT tbl_ceramics_pkey PRIMARY KEY (ceramics_id);


ALTER TABLE ONLY public.tbl_chronologies
    ADD CONSTRAINT tbl_chronologies_chronology_name_key UNIQUE (chronology_name);


ALTER TABLE ONLY public.tbl_chronologies
    ADD CONSTRAINT tbl_chronologies_chronology_name_unique UNIQUE (chronology_name);


ALTER TABLE ONLY public.tbl_chronologies
    ADD CONSTRAINT tbl_chronologies_pkey PRIMARY KEY (chronology_id);


ALTER TABLE ONLY public.tbl_colours
    ADD CONSTRAINT tbl_colours_colour_name_key UNIQUE (colour_name);


ALTER TABLE ONLY public.tbl_colours
    ADD CONSTRAINT tbl_colours_colour_name_unique UNIQUE (colour_name);


ALTER TABLE ONLY public.tbl_colours
    ADD CONSTRAINT tbl_colours_pkey PRIMARY KEY (colour_id);


ALTER TABLE ONLY public.tbl_contact_types
    ADD CONSTRAINT tbl_contact_types_pkey PRIMARY KEY (contact_type_id);


ALTER TABLE ONLY public.tbl_contacts
    ADD CONSTRAINT tbl_contacts_pkey PRIMARY KEY (contact_id);


ALTER TABLE ONLY public.tbl_coordinate_method_dimensions
    ADD CONSTRAINT tbl_coordinate_method_dimensions_pkey PRIMARY KEY (coordinate_method_dimension_id);


ALTER TABLE ONLY public.tbl_data_type_groups
    ADD CONSTRAINT tbl_data_type_groups_data_type_group_name_key UNIQUE (data_type_group_name);


ALTER TABLE ONLY public.tbl_data_type_groups
    ADD CONSTRAINT tbl_data_type_groups_data_type_group_name_unique UNIQUE (data_type_group_name);


ALTER TABLE ONLY public.tbl_data_type_groups
    ADD CONSTRAINT tbl_data_type_groups_pkey PRIMARY KEY (data_type_group_id);


ALTER TABLE ONLY public.tbl_data_types
    ADD CONSTRAINT tbl_data_types_data_type_name_key UNIQUE (data_type_name);


ALTER TABLE ONLY public.tbl_data_types
    ADD CONSTRAINT tbl_data_types_data_type_name_unique UNIQUE (data_type_name);


ALTER TABLE ONLY public.tbl_data_types
    ADD CONSTRAINT tbl_data_types_pkey PRIMARY KEY (data_type_id);


ALTER TABLE ONLY public.tbl_dataset_contacts
    ADD CONSTRAINT tbl_dataset_contacts_pkey PRIMARY KEY (dataset_contact_id);


ALTER TABLE ONLY public.tbl_dataset_masters
    ADD CONSTRAINT tbl_dataset_masters_master_name_key UNIQUE (master_name);


ALTER TABLE ONLY public.tbl_dataset_masters
    ADD CONSTRAINT tbl_dataset_masters_master_name_unique UNIQUE (master_name);


ALTER TABLE ONLY public.tbl_dataset_masters
    ADD CONSTRAINT tbl_dataset_masters_pkey PRIMARY KEY (master_set_id);


ALTER TABLE ONLY public.tbl_dataset_methods
    ADD CONSTRAINT tbl_dataset_methods_pkey PRIMARY KEY (dataset_method_id);


ALTER TABLE ONLY public.tbl_dataset_submission_types
    ADD CONSTRAINT tbl_dataset_submission_types_pkey PRIMARY KEY (submission_type_id);


ALTER TABLE ONLY public.tbl_dataset_submissions
    ADD CONSTRAINT tbl_dataset_submissions_pkey PRIMARY KEY (dataset_submission_id);


ALTER TABLE ONLY public.tbl_datasets
    ADD CONSTRAINT tbl_datasets_pkey PRIMARY KEY (dataset_id);


ALTER TABLE ONLY public.tbl_dating_labs
    ADD CONSTRAINT tbl_dating_labs_pkey PRIMARY KEY (dating_lab_id);


ALTER TABLE ONLY public.tbl_dating_material
    ADD CONSTRAINT tbl_dating_material_pkey PRIMARY KEY (dating_material_id);


ALTER TABLE ONLY public.tbl_dating_uncertainty
    ADD CONSTRAINT tbl_dating_uncertainty_pkey PRIMARY KEY (dating_uncertainty_id);


ALTER TABLE ONLY public.tbl_dating_uncertainty
    ADD CONSTRAINT tbl_dating_uncertainty_uncertainty_key UNIQUE (uncertainty);


ALTER TABLE ONLY public.tbl_dating_uncertainty
    ADD CONSTRAINT tbl_dating_uncertainty_uncertainty_unique UNIQUE (uncertainty);


ALTER TABLE ONLY public.tbl_dendro_date_notes
    ADD CONSTRAINT tbl_dendro_date_notes_pkey PRIMARY KEY (dendro_date_note_id);


ALTER TABLE ONLY public.tbl_dendro_dates
    ADD CONSTRAINT tbl_dendro_dates_pkey PRIMARY KEY (dendro_date_id);


ALTER TABLE ONLY public.tbl_dendro_lookup
    ADD CONSTRAINT tbl_dendro_lookup_pkey PRIMARY KEY (dendro_lookup_id);


ALTER TABLE ONLY public.tbl_dendro
    ADD CONSTRAINT tbl_dendro_pkey PRIMARY KEY (dendro_id);


ALTER TABLE ONLY public.tbl_dimensions
    ADD CONSTRAINT tbl_dimensions_pkey PRIMARY KEY (dimension_id);


ALTER TABLE ONLY public.tbl_ecocode_definitions
    ADD CONSTRAINT tbl_ecocode_definitions_pkey PRIMARY KEY (ecocode_definition_id);


ALTER TABLE ONLY public.tbl_ecocode_groups
    ADD CONSTRAINT tbl_ecocode_groups_name_key UNIQUE (name);


ALTER TABLE ONLY public.tbl_ecocode_groups
    ADD CONSTRAINT tbl_ecocode_groups_name_unique UNIQUE (name);


ALTER TABLE ONLY public.tbl_ecocode_groups
    ADD CONSTRAINT tbl_ecocode_groups_pkey PRIMARY KEY (ecocode_group_id);


ALTER TABLE ONLY public.tbl_ecocode_systems
    ADD CONSTRAINT tbl_ecocode_systems_name_key UNIQUE (name);


ALTER TABLE ONLY public.tbl_ecocode_systems
    ADD CONSTRAINT tbl_ecocode_systems_name_unique UNIQUE (name);


ALTER TABLE ONLY public.tbl_ecocode_systems
    ADD CONSTRAINT tbl_ecocode_systems_pkey PRIMARY KEY (ecocode_system_id);


ALTER TABLE ONLY public.tbl_ecocodes
    ADD CONSTRAINT tbl_ecocodes_pkey PRIMARY KEY (ecocode_id);


ALTER TABLE ONLY public.tbl_feature_types
    ADD CONSTRAINT tbl_feature_types_pkey PRIMARY KEY (feature_type_id);


ALTER TABLE ONLY public.tbl_features
    ADD CONSTRAINT tbl_features_pkey PRIMARY KEY (feature_id);


ALTER TABLE ONLY public.tbl_geochron_refs
    ADD CONSTRAINT tbl_geochron_refs_pkey PRIMARY KEY (geochron_ref_id);


ALTER TABLE ONLY public.tbl_geochronology
    ADD CONSTRAINT tbl_geochronology_pkey PRIMARY KEY (geochron_id);


ALTER TABLE ONLY public.tbl_horizons
    ADD CONSTRAINT tbl_horizons_pkey PRIMARY KEY (horizon_id);


ALTER TABLE ONLY public.tbl_identification_levels
    ADD CONSTRAINT tbl_identification_levels_identification_level_name_key UNIQUE (identification_level_name);


ALTER TABLE ONLY public.tbl_identification_levels
    ADD CONSTRAINT tbl_identification_levels_identification_level_name_unique UNIQUE (identification_level_name);


ALTER TABLE ONLY public.tbl_identification_levels
    ADD CONSTRAINT tbl_identification_levels_pkey PRIMARY KEY (identification_level_id);


ALTER TABLE ONLY public.tbl_image_types
    ADD CONSTRAINT tbl_image_types_image_type_key UNIQUE (image_type);


ALTER TABLE ONLY public.tbl_image_types
    ADD CONSTRAINT tbl_image_types_image_type_unique UNIQUE (image_type);


ALTER TABLE ONLY public.tbl_image_types
    ADD CONSTRAINT tbl_image_types_pkey PRIMARY KEY (image_type_id);


ALTER TABLE ONLY public.tbl_imported_taxa_replacements
    ADD CONSTRAINT tbl_imported_taxa_replacements_pkey PRIMARY KEY (imported_taxa_replacement_id);


ALTER TABLE ONLY public.tbl_isotope_measurements
    ADD CONSTRAINT tbl_isotope_measurements_pkey PRIMARY KEY (isotope_measurement_id);


ALTER TABLE ONLY public.tbl_isotope_standards
    ADD CONSTRAINT tbl_isotope_standards_pkey PRIMARY KEY (isotope_standard_id);


ALTER TABLE ONLY public.tbl_isotope_types
    ADD CONSTRAINT tbl_isotope_types_pkey PRIMARY KEY (isotope_type_id);


ALTER TABLE ONLY public.tbl_isotope_value_specifiers
    ADD CONSTRAINT tbl_isotope_value_specifiers_pkey PRIMARY KEY (isotope_value_specifier_id);


ALTER TABLE ONLY public.tbl_isotopes
    ADD CONSTRAINT tbl_isotopes_pkey PRIMARY KEY (isotope_id);


ALTER TABLE ONLY public.tbl_languages
    ADD CONSTRAINT tbl_languages_pkey PRIMARY KEY (language_id);


ALTER TABLE ONLY public.tbl_lithology
    ADD CONSTRAINT tbl_lithology_pkey PRIMARY KEY (lithology_id);


ALTER TABLE ONLY public.tbl_location_types
    ADD CONSTRAINT tbl_location_types_location_type_key UNIQUE (location_type);


ALTER TABLE ONLY public.tbl_location_types
    ADD CONSTRAINT tbl_location_types_location_type_unique UNIQUE (location_type);


ALTER TABLE ONLY public.tbl_location_types
    ADD CONSTRAINT tbl_location_types_pkey PRIMARY KEY (location_type_id);


ALTER TABLE ONLY public.tbl_locations
    ADD CONSTRAINT tbl_locations_pkey PRIMARY KEY (location_id);


ALTER TABLE ONLY public.tbl_mcr_names
    ADD CONSTRAINT tbl_mcr_names_pkey PRIMARY KEY (taxon_id);


ALTER TABLE ONLY public.tbl_mcr_summary_data
    ADD CONSTRAINT tbl_mcr_summary_data_pkey PRIMARY KEY (mcr_summary_data_id);


ALTER TABLE ONLY public.tbl_mcrdata_birmbeetledat
    ADD CONSTRAINT tbl_mcrdata_birmbeetledat_pkey PRIMARY KEY (mcrdata_birmbeetledat_id);


ALTER TABLE ONLY public.tbl_measured_value_dimensions
    ADD CONSTRAINT tbl_measured_value_dimensions_pkey PRIMARY KEY (measured_value_dimension_id);


ALTER TABLE ONLY public.tbl_measured_values
    ADD CONSTRAINT tbl_measured_values_pkey PRIMARY KEY (measured_value_id);


ALTER TABLE ONLY public.tbl_method_groups
    ADD CONSTRAINT tbl_method_groups_group_name_key UNIQUE (group_name);


ALTER TABLE ONLY public.tbl_method_groups
    ADD CONSTRAINT tbl_method_groups_group_name_unique UNIQUE (group_name);


ALTER TABLE ONLY public.tbl_method_groups
    ADD CONSTRAINT tbl_method_groups_pkey PRIMARY KEY (method_group_id);


ALTER TABLE ONLY public.tbl_methods
    ADD CONSTRAINT tbl_methods_method_abbrev_or_alt_name_key UNIQUE (method_abbrev_or_alt_name);


ALTER TABLE ONLY public.tbl_methods
    ADD CONSTRAINT tbl_methods_method_abbrev_or_alt_name_unique UNIQUE (method_abbrev_or_alt_name);


ALTER TABLE ONLY public.tbl_methods
    ADD CONSTRAINT tbl_methods_pkey PRIMARY KEY (method_id);


ALTER TABLE ONLY public.tbl_modification_types
    ADD CONSTRAINT tbl_modification_types_modification_type_name_key UNIQUE (modification_type_name);


ALTER TABLE ONLY public.tbl_modification_types
    ADD CONSTRAINT tbl_modification_types_modification_type_name_unique UNIQUE (modification_type_name);


ALTER TABLE ONLY public.tbl_modification_types
    ADD CONSTRAINT tbl_modification_types_pkey PRIMARY KEY (modification_type_id);


ALTER TABLE ONLY public.tbl_physical_sample_features
    ADD CONSTRAINT tbl_physical_sample_features_pkey PRIMARY KEY (physical_sample_feature_id);


ALTER TABLE ONLY public.tbl_physical_samples
    ADD CONSTRAINT tbl_physical_samples_pkey PRIMARY KEY (physical_sample_id);


ALTER TABLE ONLY public.tbl_project_stages
    ADD CONSTRAINT tbl_project_stages_pkey PRIMARY KEY (project_stage_id);


ALTER TABLE ONLY public.tbl_project_stages
    ADD CONSTRAINT tbl_project_stages_stage_name_key UNIQUE (stage_name);


ALTER TABLE ONLY public.tbl_project_stages
    ADD CONSTRAINT tbl_project_stages_stage_name_unique UNIQUE (stage_name);


ALTER TABLE ONLY public.tbl_project_types
    ADD CONSTRAINT tbl_project_types_pkey PRIMARY KEY (project_type_id);


ALTER TABLE ONLY public.tbl_project_types
    ADD CONSTRAINT tbl_project_types_project_type_name_key UNIQUE (project_type_name);


ALTER TABLE ONLY public.tbl_project_types
    ADD CONSTRAINT tbl_project_types_project_type_name_unique UNIQUE (project_type_name);


ALTER TABLE ONLY public.tbl_projects
    ADD CONSTRAINT tbl_projects_pkey PRIMARY KEY (project_id);


ALTER TABLE ONLY public.tbl_projects
    ADD CONSTRAINT tbl_projects_project_abbrev_name_unique UNIQUE (project_abbrev_name);


ALTER TABLE ONLY public.tbl_property_types
    ADD CONSTRAINT tbl_property_types_pkey PRIMARY KEY (property_type_id);


ALTER TABLE ONLY public.tbl_property_types
    ADD CONSTRAINT tbl_property_types_property_type_name_key UNIQUE (property_type_name);


ALTER TABLE ONLY public.tbl_property_types
    ADD CONSTRAINT tbl_property_types_uuid_key UNIQUE (uuid);


ALTER TABLE ONLY public.tbl_rdb_codes
    ADD CONSTRAINT tbl_rdb_codes_pkey PRIMARY KEY (rdb_code_id);


ALTER TABLE ONLY public.tbl_rdb
    ADD CONSTRAINT tbl_rdb_pkey PRIMARY KEY (rdb_id);


ALTER TABLE ONLY public.tbl_rdb_systems
    ADD CONSTRAINT tbl_rdb_systems_pkey PRIMARY KEY (rdb_system_id);


ALTER TABLE ONLY public.tbl_record_types
    ADD CONSTRAINT tbl_record_types_pkey PRIMARY KEY (record_type_id);


ALTER TABLE ONLY public.tbl_record_types
    ADD CONSTRAINT tbl_record_types_record_type_name_key UNIQUE (record_type_name);


ALTER TABLE ONLY public.tbl_record_types
    ADD CONSTRAINT tbl_record_types_record_type_name_unique UNIQUE (record_type_name);


ALTER TABLE ONLY public.tbl_relative_age_refs
    ADD CONSTRAINT tbl_relative_age_refs_pkey PRIMARY KEY (relative_age_ref_id);


ALTER TABLE ONLY public.tbl_relative_age_types
    ADD CONSTRAINT tbl_relative_age_types_age_type_key UNIQUE (age_type);


ALTER TABLE ONLY public.tbl_relative_age_types
    ADD CONSTRAINT tbl_relative_age_types_age_type_unique UNIQUE (age_type);


ALTER TABLE ONLY public.tbl_relative_age_types
    ADD CONSTRAINT tbl_relative_age_types_pkey PRIMARY KEY (relative_age_type_id);


ALTER TABLE ONLY public.tbl_relative_ages
    ADD CONSTRAINT tbl_relative_ages_pkey PRIMARY KEY (relative_age_id);


ALTER TABLE ONLY public.tbl_relative_dates
    ADD CONSTRAINT tbl_relative_dates_pkey PRIMARY KEY (relative_date_id);


ALTER TABLE ONLY public.tbl_sample_alt_refs
    ADD CONSTRAINT tbl_sample_alt_refs_pkey PRIMARY KEY (sample_alt_ref_id);


ALTER TABLE ONLY public.tbl_sample_colours
    ADD CONSTRAINT tbl_sample_colours_pkey PRIMARY KEY (sample_colour_id);


ALTER TABLE ONLY public.tbl_sample_coordinates
    ADD CONSTRAINT tbl_sample_coordinates_pkey PRIMARY KEY (sample_coordinate_id);


ALTER TABLE ONLY public.tbl_sample_description_sample_group_contexts
    ADD CONSTRAINT tbl_sample_description_sample_group_contexts_pkey PRIMARY KEY (sample_description_sample_group_context_id);


ALTER TABLE ONLY public.tbl_sample_description_types
    ADD CONSTRAINT tbl_sample_description_types_pkey PRIMARY KEY (sample_description_type_id);


ALTER TABLE ONLY public.tbl_sample_description_types
    ADD CONSTRAINT tbl_sample_description_types_type_name_key UNIQUE (type_name);


ALTER TABLE ONLY public.tbl_sample_description_types
    ADD CONSTRAINT tbl_sample_description_types_type_name_unique UNIQUE (type_name);


ALTER TABLE ONLY public.tbl_sample_descriptions
    ADD CONSTRAINT tbl_sample_descriptions_pkey PRIMARY KEY (sample_description_id);


ALTER TABLE ONLY public.tbl_sample_dimensions
    ADD CONSTRAINT tbl_sample_dimensions_pkey PRIMARY KEY (sample_dimension_id);


ALTER TABLE ONLY public.tbl_sample_group_coordinates
    ADD CONSTRAINT tbl_sample_group_coordinates_pkey PRIMARY KEY (sample_group_position_id);


ALTER TABLE ONLY public.tbl_sample_group_description_type_sampling_contexts
    ADD CONSTRAINT tbl_sample_group_description_type_sampling_contexts_pkey PRIMARY KEY (sample_group_description_type_sampling_context_id);


ALTER TABLE ONLY public.tbl_sample_group_description_types
    ADD CONSTRAINT tbl_sample_group_description_types_pkey PRIMARY KEY (sample_group_description_type_id);


ALTER TABLE ONLY public.tbl_sample_group_description_types
    ADD CONSTRAINT tbl_sample_group_description_types_type_name_key UNIQUE (type_name);


ALTER TABLE ONLY public.tbl_sample_group_description_types
    ADD CONSTRAINT tbl_sample_group_description_types_type_name_unique UNIQUE (type_name);


ALTER TABLE ONLY public.tbl_sample_group_descriptions
    ADD CONSTRAINT tbl_sample_group_descriptions_pkey PRIMARY KEY (sample_group_description_id);


ALTER TABLE ONLY public.tbl_sample_group_dimensions
    ADD CONSTRAINT tbl_sample_group_dimensions_pkey PRIMARY KEY (sample_group_dimension_id);


ALTER TABLE ONLY public.tbl_sample_group_images
    ADD CONSTRAINT tbl_sample_group_images_pkey PRIMARY KEY (sample_group_image_id);


ALTER TABLE ONLY public.tbl_sample_group_notes
    ADD CONSTRAINT tbl_sample_group_notes_pkey PRIMARY KEY (sample_group_note_id);


ALTER TABLE ONLY public.tbl_sample_group_references
    ADD CONSTRAINT tbl_sample_group_references_pkey PRIMARY KEY (sample_group_reference_id);


ALTER TABLE ONLY public.tbl_sample_group_sampling_contexts
    ADD CONSTRAINT tbl_sample_group_sampling_contexts_pkey PRIMARY KEY (sampling_context_id);


ALTER TABLE ONLY public.tbl_sample_groups
    ADD CONSTRAINT tbl_sample_groups_pkey PRIMARY KEY (sample_group_id);


ALTER TABLE ONLY public.tbl_sample_horizons
    ADD CONSTRAINT tbl_sample_horizons_pkey PRIMARY KEY (sample_horizon_id);


ALTER TABLE ONLY public.tbl_sample_images
    ADD CONSTRAINT tbl_sample_images_pkey PRIMARY KEY (sample_image_id);


ALTER TABLE ONLY public.tbl_sample_location_type_sampling_contexts
    ADD CONSTRAINT tbl_sample_location_type_sampling_contexts_pkey PRIMARY KEY (sample_location_type_sampling_context_id);


ALTER TABLE ONLY public.tbl_sample_location_types
    ADD CONSTRAINT tbl_sample_location_types_location_type_key UNIQUE (location_type);


ALTER TABLE ONLY public.tbl_sample_location_types
    ADD CONSTRAINT tbl_sample_location_types_location_type_unique UNIQUE (location_type);


ALTER TABLE ONLY public.tbl_sample_location_types
    ADD CONSTRAINT tbl_sample_location_types_pkey PRIMARY KEY (sample_location_type_id);


ALTER TABLE ONLY public.tbl_sample_locations
    ADD CONSTRAINT tbl_sample_locations_pkey PRIMARY KEY (sample_location_id);


ALTER TABLE ONLY public.tbl_sample_notes
    ADD CONSTRAINT tbl_sample_notes_pkey PRIMARY KEY (sample_note_id);


ALTER TABLE ONLY public.tbl_sample_types
    ADD CONSTRAINT tbl_sample_types_pkey PRIMARY KEY (sample_type_id);


ALTER TABLE ONLY public.tbl_sample_types
    ADD CONSTRAINT tbl_sample_types_type_name_key UNIQUE (type_name);


ALTER TABLE ONLY public.tbl_sample_types
    ADD CONSTRAINT tbl_sample_types_type_name_unique UNIQUE (type_name);


ALTER TABLE ONLY public.tbl_season_types
    ADD CONSTRAINT tbl_season_types_pkey PRIMARY KEY (season_type_id);


ALTER TABLE ONLY public.tbl_season_types
    ADD CONSTRAINT tbl_season_types_season_type_key UNIQUE (season_type);


ALTER TABLE ONLY public.tbl_season_types
    ADD CONSTRAINT tbl_season_types_season_type_unique UNIQUE (season_type);


ALTER TABLE ONLY public.tbl_seasons
    ADD CONSTRAINT tbl_seasons_pkey PRIMARY KEY (season_id);


ALTER TABLE ONLY public.tbl_seasons
    ADD CONSTRAINT tbl_seasons_season_name_key UNIQUE (season_name);


ALTER TABLE ONLY public.tbl_seasons
    ADD CONSTRAINT tbl_seasons_season_name_unique UNIQUE (season_name);


ALTER TABLE ONLY public.tbl_site_images
    ADD CONSTRAINT tbl_site_images_pkey PRIMARY KEY (site_image_id);


ALTER TABLE ONLY public.tbl_site_locations
    ADD CONSTRAINT tbl_site_locations_pkey PRIMARY KEY (site_location_id);


ALTER TABLE ONLY public.tbl_site_natgridrefs
    ADD CONSTRAINT tbl_site_natgridrefs_pkey PRIMARY KEY (site_natgridref_id);


ALTER TABLE ONLY public.tbl_site_other_records
    ADD CONSTRAINT tbl_site_other_records_pkey PRIMARY KEY (site_other_records_id);


ALTER TABLE ONLY public.tbl_site_preservation_status
    ADD CONSTRAINT tbl_site_preservation_status_pkey PRIMARY KEY (site_preservation_status_id);


ALTER TABLE ONLY public.tbl_site_properties
    ADD CONSTRAINT tbl_site_properties_pkey PRIMARY KEY (site_property_id);


ALTER TABLE ONLY public.tbl_site_references
    ADD CONSTRAINT tbl_site_references_pkey PRIMARY KEY (site_reference_id);


ALTER TABLE ONLY public.tbl_site_site_types
    ADD CONSTRAINT tbl_site_site_types_pkey PRIMARY KEY (site_site_type_id);


ALTER TABLE ONLY public.tbl_site_type_groups
    ADD CONSTRAINT tbl_site_type_groups_pkey PRIMARY KEY (site_type_group_id);


ALTER TABLE ONLY public.tbl_site_type_groups
    ADD CONSTRAINT tbl_site_type_groups_site_type_group_abbrev_key UNIQUE (site_type_group_abbrev);


ALTER TABLE ONLY public.tbl_site_types
    ADD CONSTRAINT tbl_site_types_pkey PRIMARY KEY (site_type_id);


ALTER TABLE ONLY public.tbl_site_types
    ADD CONSTRAINT tbl_site_types_site_type_abbrev_key UNIQUE (site_type_abbrev);


ALTER TABLE ONLY public.tbl_site_types
    ADD CONSTRAINT tbl_site_types_site_type_key UNIQUE (site_type);


ALTER TABLE ONLY public.tbl_sites
    ADD CONSTRAINT tbl_sites_pkey PRIMARY KEY (site_id);


ALTER TABLE ONLY public.tbl_species_association_types
    ADD CONSTRAINT tbl_species_association_types_association_type_name_key UNIQUE (association_type_name);


ALTER TABLE ONLY public.tbl_species_association_types
    ADD CONSTRAINT tbl_species_association_types_association_type_name_unique UNIQUE (association_type_name);


ALTER TABLE ONLY public.tbl_species_association_types
    ADD CONSTRAINT tbl_species_association_types_pkey PRIMARY KEY (association_type_id);


ALTER TABLE ONLY public.tbl_species_associations
    ADD CONSTRAINT tbl_species_associations_pkey PRIMARY KEY (species_association_id);


ALTER TABLE ONLY public.tbl_taxa_common_names
    ADD CONSTRAINT tbl_taxa_common_names_pkey PRIMARY KEY (taxon_common_name_id);


ALTER TABLE ONLY public.tbl_taxa_images
    ADD CONSTRAINT tbl_taxa_images_pkey PRIMARY KEY (taxa_images_id);


ALTER TABLE ONLY public.tbl_taxa_measured_attributes
    ADD CONSTRAINT tbl_taxa_measured_attributes_pkey PRIMARY KEY (measured_attribute_id);


ALTER TABLE ONLY public.tbl_taxa_reference_specimens
    ADD CONSTRAINT tbl_taxa_reference_specimens_pkey PRIMARY KEY (taxa_reference_specimen_id);


ALTER TABLE ONLY public.tbl_taxa_seasonality
    ADD CONSTRAINT tbl_taxa_seasonality_pkey PRIMARY KEY (seasonality_id);


ALTER TABLE ONLY public.tbl_taxa_synonyms
    ADD CONSTRAINT tbl_taxa_synonyms_pkey PRIMARY KEY (synonym_id);


ALTER TABLE ONLY public.tbl_taxa_tree_authors
    ADD CONSTRAINT tbl_taxa_tree_authors_pkey PRIMARY KEY (author_id);


ALTER TABLE ONLY public.tbl_taxa_tree_families
    ADD CONSTRAINT tbl_taxa_tree_families_pkey PRIMARY KEY (family_id);


ALTER TABLE ONLY public.tbl_taxa_tree_genera
    ADD CONSTRAINT tbl_taxa_tree_genera_pkey PRIMARY KEY (genus_id);


ALTER TABLE ONLY public.tbl_taxa_tree_master
    ADD CONSTRAINT tbl_taxa_tree_master_pkey PRIMARY KEY (taxon_id);


ALTER TABLE ONLY public.tbl_taxa_tree_orders
    ADD CONSTRAINT tbl_taxa_tree_orders_pkey PRIMARY KEY (order_id);


ALTER TABLE ONLY public.tbl_taxonomic_order_biblio
    ADD CONSTRAINT tbl_taxonomic_order_biblio_pkey PRIMARY KEY (taxonomic_order_biblio_id);


ALTER TABLE ONLY public.tbl_taxonomic_order
    ADD CONSTRAINT tbl_taxonomic_order_pkey PRIMARY KEY (taxonomic_order_id);


ALTER TABLE ONLY public.tbl_taxonomic_order_systems
    ADD CONSTRAINT tbl_taxonomic_order_systems_pkey PRIMARY KEY (taxonomic_order_system_id);


ALTER TABLE ONLY public.tbl_taxonomy_notes
    ADD CONSTRAINT tbl_taxonomy_notes_pkey PRIMARY KEY (taxonomy_notes_id);


ALTER TABLE ONLY public.tbl_temperatures
    ADD CONSTRAINT tbl_temperatures_pkey PRIMARY KEY (record_id);


ALTER TABLE ONLY public.tbl_tephra_dates
    ADD CONSTRAINT tbl_tephra_dates_pkey PRIMARY KEY (tephra_date_id);


ALTER TABLE ONLY public.tbl_tephra_refs
    ADD CONSTRAINT tbl_tephra_refs_pkey PRIMARY KEY (tephra_ref_id);


ALTER TABLE ONLY public.tbl_tephras
    ADD CONSTRAINT tbl_tephras_pkey PRIMARY KEY (tephra_id);


ALTER TABLE ONLY public.tbl_text_biology
    ADD CONSTRAINT tbl_text_biology_pkey PRIMARY KEY (biology_id);


ALTER TABLE ONLY public.tbl_text_distribution
    ADD CONSTRAINT tbl_text_distribution_pkey PRIMARY KEY (distribution_id);


ALTER TABLE ONLY public.tbl_text_identification_keys
    ADD CONSTRAINT tbl_text_identification_keys_pkey PRIMARY KEY (key_id);


ALTER TABLE ONLY public.tbl_units
    ADD CONSTRAINT tbl_units_pkey PRIMARY KEY (unit_id);


ALTER TABLE ONLY public.tbl_units
    ADD CONSTRAINT tbl_units_unit_abbrev_key UNIQUE (unit_abbrev);


ALTER TABLE ONLY public.tbl_units
    ADD CONSTRAINT tbl_units_unit_abbrev_unique UNIQUE (unit_abbrev);


ALTER TABLE ONLY public.tbl_units
    ADD CONSTRAINT tbl_units_unit_name_key UNIQUE (unit_name);


ALTER TABLE ONLY public.tbl_units
    ADD CONSTRAINT tbl_units_unit_name_unique UNIQUE (unit_name);


ALTER TABLE ONLY public.tbl_updates_log
    ADD CONSTRAINT tbl_updates_log_pkey PRIMARY KEY (updates_log_id);


ALTER TABLE ONLY public.tbl_value_classes
    ADD CONSTRAINT tbl_value_classes_pkey PRIMARY KEY (value_class_id);


ALTER TABLE ONLY public.tbl_value_qualifier_symbols
    ADD CONSTRAINT tbl_value_qualifier_symbols_pkey PRIMARY KEY (qualifier_symbol_id);


ALTER TABLE ONLY public.tbl_value_qualifier_symbols
    ADD CONSTRAINT tbl_value_qualifier_symbols_symbol_key UNIQUE (symbol);


ALTER TABLE ONLY public.tbl_value_qualifiers
    ADD CONSTRAINT tbl_value_qualifiers_pkey PRIMARY KEY (qualifier_id);


ALTER TABLE ONLY public.tbl_value_qualifiers
    ADD CONSTRAINT tbl_value_qualifiers_symbol_key UNIQUE (symbol);


ALTER TABLE ONLY public.tbl_value_type_items
    ADD CONSTRAINT tbl_value_type_items_pkey PRIMARY KEY (value_type_item_id);


ALTER TABLE ONLY public.tbl_value_types
    ADD CONSTRAINT tbl_value_types_name_key UNIQUE (name);


ALTER TABLE ONLY public.tbl_value_types
    ADD CONSTRAINT tbl_value_types_pkey PRIMARY KEY (value_type_id);


ALTER TABLE ONLY public.tbl_years_types
    ADD CONSTRAINT tbl_years_types_name_key UNIQUE (name);


ALTER TABLE ONLY public.tbl_years_types
    ADD CONSTRAINT tbl_years_types_name_unique UNIQUE (name);


ALTER TABLE ONLY public.tbl_years_types
    ADD CONSTRAINT tbl_years_types_pkey PRIMARY KEY (years_type_id);


ALTER TABLE ONLY public.tbl_aggregate_datasets
    ADD CONSTRAINT unique_tbl_aggregate_datasets_aggregate_dataset_uuid UNIQUE (aggregate_dataset_uuid);


ALTER TABLE ONLY public.tbl_biblio
    ADD CONSTRAINT unique_tbl_biblio_biblio_uuid UNIQUE (biblio_uuid);


ALTER TABLE ONLY public.tbl_dataset_masters
    ADD CONSTRAINT unique_tbl_dataset_masters_master_set_uuid UNIQUE (master_set_uuid);


ALTER TABLE ONLY public.tbl_datasets
    ADD CONSTRAINT unique_tbl_datasets_dataset_uuid UNIQUE (dataset_uuid);


ALTER TABLE ONLY public.tbl_ecocode_systems
    ADD CONSTRAINT unique_tbl_ecocode_systems_ecocode_system_uuid UNIQUE (ecocode_system_uuid);


ALTER TABLE ONLY public.tbl_geochronology
    ADD CONSTRAINT unique_tbl_geochronology_geochron_uuid UNIQUE (geochron_uuid);


ALTER TABLE ONLY public.tbl_methods
    ADD CONSTRAINT unique_tbl_methods_method_uuid UNIQUE (method_uuid);


ALTER TABLE ONLY public.tbl_rdb_systems
    ADD CONSTRAINT unique_tbl_rdb_systems_rdb_system_uuid UNIQUE (rdb_system_uuid);


ALTER TABLE ONLY public.tbl_relative_ages
    ADD CONSTRAINT unique_tbl_relative_ages_relative_age_uuid UNIQUE (relative_age_uuid);


ALTER TABLE ONLY public.tbl_sample_groups
    ADD CONSTRAINT unique_tbl_sample_groups_sample_group_uuid UNIQUE (sample_group_uuid);


ALTER TABLE ONLY public.tbl_site_other_records
    ADD CONSTRAINT unique_tbl_site_other_records_site_other_records_uuid UNIQUE (site_other_records_uuid);


ALTER TABLE ONLY public.tbl_sites
    ADD CONSTRAINT unique_tbl_sites_site_uuid UNIQUE (site_uuid);


ALTER TABLE ONLY public.tbl_species_associations
    ADD CONSTRAINT unique_tbl_species_associations_species_association_uuid UNIQUE (species_association_uuid);


ALTER TABLE ONLY public.tbl_taxa_synonyms
    ADD CONSTRAINT unique_tbl_taxa_synonyms_synonym_uuid UNIQUE (synonym_uuid);


ALTER TABLE ONLY public.tbl_taxonomic_order_systems
    ADD CONSTRAINT unique_tbl_taxonomic_order_systems_taxonomic_order_system_uuid UNIQUE (taxonomic_order_system_uuid);


ALTER TABLE ONLY public.tbl_taxonomy_notes
    ADD CONSTRAINT unique_tbl_taxonomy_notes_taxonomy_notes_uuid UNIQUE (taxonomy_notes_uuid);


ALTER TABLE ONLY public.tbl_tephras
    ADD CONSTRAINT unique_tbl_tephras_tephra_uuid UNIQUE (tephra_uuid);


ALTER TABLE ONLY public.tbl_text_biology
    ADD CONSTRAINT unique_tbl_text_biology_biology_uuid UNIQUE (biology_uuid);


ALTER TABLE ONLY public.tbl_text_distribution
    ADD CONSTRAINT unique_tbl_text_distribution_distribution_uuid UNIQUE (distribution_uuid);


ALTER TABLE ONLY public.tbl_text_identification_keys
    ADD CONSTRAINT unique_tbl_text_identification_keys_key_uuid UNIQUE (key_uuid);


ALTER TABLE ONLY public.tbl_site_references
    ADD CONSTRAINT uq_site_references UNIQUE (site_id, biblio_id);


ALTER TABLE ONLY public.tbl_site_site_types
    ADD CONSTRAINT uq_site_type_per_site UNIQUE (site_id, site_type_id);


ALTER TABLE ONLY public.tbl_sample_alt_refs
    ADD CONSTRAINT uq_tbl_sample_alt_refs UNIQUE (physical_sample_id, alt_ref, alt_ref_type_id);


ALTER TABLE ONLY public.tbl_abundance_elements
    ADD CONSTRAINT fk_abundance_elements_record_type_id FOREIGN KEY (record_type_id) REFERENCES public.tbl_record_types(record_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_abundance_ident_levels
    ADD CONSTRAINT fk_abundance_ident_levels_abundance_id FOREIGN KEY (abundance_id) REFERENCES public.tbl_abundances(abundance_id);


ALTER TABLE ONLY public.tbl_abundance_ident_levels
    ADD CONSTRAINT fk_abundance_ident_levels_identification_level_id FOREIGN KEY (identification_level_id) REFERENCES public.tbl_identification_levels(identification_level_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_abundance_modifications
    ADD CONSTRAINT fk_abundance_modifications_abundance_id FOREIGN KEY (abundance_id) REFERENCES public.tbl_abundances(abundance_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_abundance_modifications
    ADD CONSTRAINT fk_abundance_modifications_modification_type_id FOREIGN KEY (modification_type_id) REFERENCES public.tbl_modification_types(modification_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_abundances
    ADD CONSTRAINT fk_abundances_abundance_elements_id FOREIGN KEY (abundance_element_id) REFERENCES public.tbl_abundance_elements(abundance_element_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_abundances
    ADD CONSTRAINT fk_abundances_analysis_entity_id FOREIGN KEY (analysis_entity_id) REFERENCES public.tbl_analysis_entities(analysis_entity_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_abundances
    ADD CONSTRAINT fk_abundances_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_aggregate_samples
    ADD CONSTRAINT fk_aggragate_samples_analysis_entity_id FOREIGN KEY (analysis_entity_id) REFERENCES public.tbl_analysis_entities(analysis_entity_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_aggregate_datasets
    ADD CONSTRAINT fk_aggregate_datasets_aggregate_order_type_id FOREIGN KEY (aggregate_order_type_id) REFERENCES public.tbl_aggregate_order_types(aggregate_order_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_aggregate_datasets
    ADD CONSTRAINT fk_aggregate_datasets_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_aggregate_sample_ages
    ADD CONSTRAINT fk_aggregate_sample_ages_aggregate_dataset_id FOREIGN KEY (aggregate_dataset_id) REFERENCES public.tbl_aggregate_datasets(aggregate_dataset_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_aggregate_sample_ages
    ADD CONSTRAINT fk_aggregate_sample_ages_analysis_entity_age_id FOREIGN KEY (analysis_entity_age_id) REFERENCES public.tbl_analysis_entity_ages(analysis_entity_age_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_aggregate_samples
    ADD CONSTRAINT fk_aggregate_samples_aggregate_dataset_id FOREIGN KEY (aggregate_dataset_id) REFERENCES public.tbl_aggregate_datasets(aggregate_dataset_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_entities
    ADD CONSTRAINT fk_analysis_entities_dataset_id FOREIGN KEY (dataset_id) REFERENCES public.tbl_datasets(dataset_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_entities
    ADD CONSTRAINT fk_analysis_entities_physical_sample_id FOREIGN KEY (physical_sample_id) REFERENCES public.tbl_physical_samples(physical_sample_id);


ALTER TABLE ONLY public.tbl_analysis_entity_ages
    ADD CONSTRAINT fk_analysis_entity_ages_analysis_entity_id FOREIGN KEY (analysis_entity_id) REFERENCES public.tbl_analysis_entities(analysis_entity_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_entity_ages
    ADD CONSTRAINT fk_analysis_entity_ages_chronology_id FOREIGN KEY (chronology_id) REFERENCES public.tbl_chronologies(chronology_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_entity_dimensions
    ADD CONSTRAINT fk_analysis_entity_dimensions_analysis_entity_id FOREIGN KEY (analysis_entity_id) REFERENCES public.tbl_analysis_entities(analysis_entity_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_entity_dimensions
    ADD CONSTRAINT fk_analysis_entity_dimensions_dimension_id FOREIGN KEY (dimension_id) REFERENCES public.tbl_dimensions(dimension_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_entity_prep_methods
    ADD CONSTRAINT fk_analysis_entity_prep_methods_analysis_entity_id FOREIGN KEY (analysis_entity_id) REFERENCES public.tbl_analysis_entities(analysis_entity_id);


ALTER TABLE ONLY public.tbl_analysis_entity_prep_methods
    ADD CONSTRAINT fk_analysis_entity_prep_methods_method_id FOREIGN KEY (method_id) REFERENCES public.tbl_methods(method_id);


ALTER TABLE ONLY public.tbl_ceramics
    ADD CONSTRAINT fk_ceramics_analysis_entity_id FOREIGN KEY (analysis_entity_id) REFERENCES public.tbl_analysis_entities(analysis_entity_id);


ALTER TABLE ONLY public.tbl_ceramics
    ADD CONSTRAINT fk_ceramics_ceramics_lookup_id FOREIGN KEY (ceramics_lookup_id) REFERENCES public.tbl_ceramics_lookup(ceramics_lookup_id);


ALTER TABLE ONLY public.tbl_ceramics_lookup
    ADD CONSTRAINT fk_ceramics_lookup_method_id FOREIGN KEY (method_id) REFERENCES public.tbl_methods(method_id);


ALTER TABLE ONLY public.tbl_ceramics_measurements
    ADD CONSTRAINT fk_ceramics_measurements_method_id FOREIGN KEY (method_id) REFERENCES public.tbl_methods(method_id);


ALTER TABLE ONLY public.tbl_chronologies
    ADD CONSTRAINT fk_chronologies_contact_id FOREIGN KEY (contact_id) REFERENCES public.tbl_contacts(contact_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_colours
    ADD CONSTRAINT fk_colours_method_id FOREIGN KEY (method_id) REFERENCES public.tbl_methods(method_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_coordinate_method_dimensions
    ADD CONSTRAINT fk_coordinate_method_dimensions_dimensions_id FOREIGN KEY (dimension_id) REFERENCES public.tbl_dimensions(dimension_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_coordinate_method_dimensions
    ADD CONSTRAINT fk_coordinate_method_dimensions_method_id FOREIGN KEY (method_id) REFERENCES public.tbl_methods(method_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_data_types
    ADD CONSTRAINT fk_data_types_data_type_group_id FOREIGN KEY (data_type_group_id) REFERENCES public.tbl_data_type_groups(data_type_group_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_dataset_contacts
    ADD CONSTRAINT fk_dataset_contacts_contact_id FOREIGN KEY (contact_id) REFERENCES public.tbl_contacts(contact_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_dataset_contacts
    ADD CONSTRAINT fk_dataset_contacts_contact_type_id FOREIGN KEY (contact_type_id) REFERENCES public.tbl_contact_types(contact_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_dataset_contacts
    ADD CONSTRAINT fk_dataset_contacts_dataset_id FOREIGN KEY (dataset_id) REFERENCES public.tbl_datasets(dataset_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_dataset_masters
    ADD CONSTRAINT fk_dataset_masters_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id);


ALTER TABLE ONLY public.tbl_dataset_masters
    ADD CONSTRAINT fk_dataset_masters_contact_id FOREIGN KEY (contact_id) REFERENCES public.tbl_contacts(contact_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_dataset_submissions
    ADD CONSTRAINT fk_dataset_submission_submission_type_id FOREIGN KEY (submission_type_id) REFERENCES public.tbl_dataset_submission_types(submission_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_dataset_submissions
    ADD CONSTRAINT fk_dataset_submissions_contact_id FOREIGN KEY (contact_id) REFERENCES public.tbl_contacts(contact_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_dataset_submissions
    ADD CONSTRAINT fk_dataset_submissions_dataset_id FOREIGN KEY (dataset_id) REFERENCES public.tbl_datasets(dataset_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_datasets
    ADD CONSTRAINT fk_datasets_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_datasets
    ADD CONSTRAINT fk_datasets_data_type_id FOREIGN KEY (data_type_id) REFERENCES public.tbl_data_types(data_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_datasets
    ADD CONSTRAINT fk_datasets_master_set_id FOREIGN KEY (master_set_id) REFERENCES public.tbl_dataset_masters(master_set_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_datasets
    ADD CONSTRAINT fk_datasets_method_id FOREIGN KEY (method_id) REFERENCES public.tbl_methods(method_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_datasets
    ADD CONSTRAINT fk_datasets_project_id FOREIGN KEY (project_id) REFERENCES public.tbl_projects(project_id);


ALTER TABLE ONLY public.tbl_datasets
    ADD CONSTRAINT fk_datasets_updated_dataset_id FOREIGN KEY (updated_dataset_id) REFERENCES public.tbl_datasets(dataset_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_dating_labs
    ADD CONSTRAINT fk_dating_labs_contact_id FOREIGN KEY (contact_id) REFERENCES public.tbl_contacts(contact_id);


ALTER TABLE ONLY public.tbl_dating_material
    ADD CONSTRAINT fk_dating_material_abundance_elements_id FOREIGN KEY (abundance_element_id) REFERENCES public.tbl_abundance_elements(abundance_element_id);


ALTER TABLE ONLY public.tbl_dating_material
    ADD CONSTRAINT fk_dating_material_geochronology_geochron_id FOREIGN KEY (geochron_id) REFERENCES public.tbl_geochronology(geochron_id);


ALTER TABLE ONLY public.tbl_dating_material
    ADD CONSTRAINT fk_dating_material_taxa_tree_master_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id);


ALTER TABLE ONLY public.tbl_dendro
    ADD CONSTRAINT fk_dendro_analysis_entity_id FOREIGN KEY (analysis_entity_id) REFERENCES public.tbl_analysis_entities(analysis_entity_id);


ALTER TABLE ONLY public.tbl_dendro_date_notes
    ADD CONSTRAINT fk_dendro_date_notes_dendro_date_id FOREIGN KEY (dendro_date_id) REFERENCES public.tbl_dendro_dates(dendro_date_id);


ALTER TABLE ONLY public.tbl_dendro_dates
    ADD CONSTRAINT fk_dendro_dates_analysis_entity_id FOREIGN KEY (analysis_entity_id) REFERENCES public.tbl_analysis_entities(analysis_entity_id);


ALTER TABLE ONLY public.tbl_dendro_dates
    ADD CONSTRAINT fk_dendro_dates_dating_uncertainty_id FOREIGN KEY (dating_uncertainty_id) REFERENCES public.tbl_dating_uncertainty(dating_uncertainty_id);


ALTER TABLE ONLY public.tbl_dendro
    ADD CONSTRAINT fk_dendro_dendro_lookup_id FOREIGN KEY (dendro_lookup_id) REFERENCES public.tbl_dendro_lookup(dendro_lookup_id);


ALTER TABLE ONLY public.tbl_dendro_dates
    ADD CONSTRAINT fk_dendro_lookup_dendro_lookup_id FOREIGN KEY (dendro_lookup_id) REFERENCES public.tbl_dendro_lookup(dendro_lookup_id);


ALTER TABLE ONLY public.tbl_dendro_lookup
    ADD CONSTRAINT fk_dendro_lookup_method_id FOREIGN KEY (method_id) REFERENCES public.tbl_methods(method_id);


ALTER TABLE ONLY public.tbl_dimensions
    ADD CONSTRAINT fk_dimensions_method_group_id FOREIGN KEY (method_group_id) REFERENCES public.tbl_method_groups(method_group_id);


ALTER TABLE ONLY public.tbl_dimensions
    ADD CONSTRAINT fk_dimensions_unit_id FOREIGN KEY (unit_id) REFERENCES public.tbl_units(unit_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_ecocode_definitions
    ADD CONSTRAINT fk_ecocode_definitions_ecocode_group_id FOREIGN KEY (ecocode_group_id) REFERENCES public.tbl_ecocode_groups(ecocode_group_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_ecocode_groups
    ADD CONSTRAINT fk_ecocode_groups_ecocode_system_id FOREIGN KEY (ecocode_system_id) REFERENCES public.tbl_ecocode_systems(ecocode_system_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_ecocode_systems
    ADD CONSTRAINT fk_ecocode_systems_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_ecocodes
    ADD CONSTRAINT fk_ecocodes_ecocodedef_id FOREIGN KEY (ecocode_definition_id) REFERENCES public.tbl_ecocode_definitions(ecocode_definition_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_ecocodes
    ADD CONSTRAINT fk_ecocodes_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_features
    ADD CONSTRAINT fk_feature_type_id_feature_type_id FOREIGN KEY (feature_type_id) REFERENCES public.tbl_feature_types(feature_type_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_geochron_refs
    ADD CONSTRAINT fk_geochron_refs_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_geochron_refs
    ADD CONSTRAINT fk_geochron_refs_geochron_id FOREIGN KEY (geochron_id) REFERENCES public.tbl_geochronology(geochron_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_geochronology
    ADD CONSTRAINT fk_geochronology_analysis_entity_id FOREIGN KEY (analysis_entity_id) REFERENCES public.tbl_analysis_entities(analysis_entity_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_geochronology
    ADD CONSTRAINT fk_geochronology_dating_labs_id FOREIGN KEY (dating_lab_id) REFERENCES public.tbl_dating_labs(dating_lab_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_geochronology
    ADD CONSTRAINT fk_geochronology_dating_uncertainty_id FOREIGN KEY (dating_uncertainty_id) REFERENCES public.tbl_dating_uncertainty(dating_uncertainty_id);


ALTER TABLE ONLY public.tbl_horizons
    ADD CONSTRAINT fk_horizons_method_id FOREIGN KEY (method_id) REFERENCES public.tbl_methods(method_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_imported_taxa_replacements
    ADD CONSTRAINT fk_imported_taxa_replacements_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_isotope_measurements
    ADD CONSTRAINT fk_isotope_isotope_type_id FOREIGN KEY (isotope_type_id) REFERENCES public.tbl_isotope_types(isotope_type_id);


ALTER TABLE ONLY public.tbl_isotope_measurements
    ADD CONSTRAINT fk_isotope_measurements_isotope_standard_id FOREIGN KEY (isotope_standard_id) REFERENCES public.tbl_isotope_standards(isotope_standard_id);


ALTER TABLE ONLY public.tbl_isotope_measurements
    ADD CONSTRAINT fk_isotope_method_id FOREIGN KEY (method_id) REFERENCES public.tbl_methods(method_id);


ALTER TABLE ONLY public.tbl_isotopes
    ADD CONSTRAINT fk_isotopes_analysis_entity_id FOREIGN KEY (analysis_entity_id) REFERENCES public.tbl_analysis_entities(analysis_entity_id);


ALTER TABLE ONLY public.tbl_isotopes
    ADD CONSTRAINT fk_isotopes_isotope_measurement_id FOREIGN KEY (isotope_measurement_id) REFERENCES public.tbl_isotope_measurements(isotope_measurement_id);


ALTER TABLE ONLY public.tbl_isotopes
    ADD CONSTRAINT fk_isotopes_isotope_standard_id FOREIGN KEY (isotope_standard_id) REFERENCES public.tbl_isotope_standards(isotope_standard_id);


ALTER TABLE ONLY public.tbl_isotopes
    ADD CONSTRAINT fk_isotopes_isotope_value_specifier_id FOREIGN KEY (isotope_value_specifier_id) REFERENCES public.tbl_isotope_value_specifiers(isotope_value_specifier_id);


ALTER TABLE ONLY public.tbl_isotopes
    ADD CONSTRAINT fk_isotopes_unit_id FOREIGN KEY (unit_id) REFERENCES public.tbl_units(unit_id);


ALTER TABLE ONLY public.tbl_lithology
    ADD CONSTRAINT fk_lithology_sample_group_id FOREIGN KEY (sample_group_id) REFERENCES public.tbl_sample_groups(sample_group_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_site_locations
    ADD CONSTRAINT fk_locations_location_id FOREIGN KEY (location_id) REFERENCES public.tbl_locations(location_id);


ALTER TABLE ONLY public.tbl_locations
    ADD CONSTRAINT fk_locations_location_type_id FOREIGN KEY (location_type_id) REFERENCES public.tbl_location_types(location_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_site_locations
    ADD CONSTRAINT fk_locations_site_id FOREIGN KEY (site_id) REFERENCES public.tbl_sites(site_id);


ALTER TABLE ONLY public.tbl_mcr_names
    ADD CONSTRAINT fk_mcr_names_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_mcr_summary_data
    ADD CONSTRAINT fk_mcr_summary_data_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_mcrdata_birmbeetledat
    ADD CONSTRAINT fk_mcrdata_birmbeetledat_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_measured_value_dimensions
    ADD CONSTRAINT fk_measured_value_dimensions_dimension_id FOREIGN KEY (dimension_id) REFERENCES public.tbl_dimensions(dimension_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_measured_values
    ADD CONSTRAINT fk_measured_values_analysis_entity_id FOREIGN KEY (analysis_entity_id) REFERENCES public.tbl_analysis_entities(analysis_entity_id);


ALTER TABLE ONLY public.tbl_measured_value_dimensions
    ADD CONSTRAINT fk_measured_weights_value_id FOREIGN KEY (measured_value_id) REFERENCES public.tbl_measured_values(measured_value_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_methods
    ADD CONSTRAINT fk_methods_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_methods
    ADD CONSTRAINT fk_methods_method_group_id FOREIGN KEY (method_group_id) REFERENCES public.tbl_method_groups(method_group_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_methods
    ADD CONSTRAINT fk_methods_record_type_id FOREIGN KEY (record_type_id) REFERENCES public.tbl_record_types(record_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_methods
    ADD CONSTRAINT fk_methods_unit_id FOREIGN KEY (unit_id) REFERENCES public.tbl_units(unit_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_physical_sample_features
    ADD CONSTRAINT fk_physical_sample_features_feature_id FOREIGN KEY (feature_id) REFERENCES public.tbl_features(feature_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_physical_sample_features
    ADD CONSTRAINT fk_physical_sample_features_physical_sample_id FOREIGN KEY (physical_sample_id) REFERENCES public.tbl_physical_samples(physical_sample_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_physical_samples
    ADD CONSTRAINT fk_physical_samples_sample_name_type_id FOREIGN KEY (alt_ref_type_id) REFERENCES public.tbl_alt_ref_types(alt_ref_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_physical_samples
    ADD CONSTRAINT fk_physical_samples_sample_type_id FOREIGN KEY (sample_type_id) REFERENCES public.tbl_sample_types(sample_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_projects
    ADD CONSTRAINT fk_projects_project_stage_id FOREIGN KEY (project_stage_id) REFERENCES public.tbl_project_stages(project_stage_id);


ALTER TABLE ONLY public.tbl_projects
    ADD CONSTRAINT fk_projects_project_type_id FOREIGN KEY (project_type_id) REFERENCES public.tbl_project_types(project_type_id);


ALTER TABLE ONLY public.tbl_rdb_codes
    ADD CONSTRAINT fk_rdb_codes_rdb_system_id FOREIGN KEY (rdb_system_id) REFERENCES public.tbl_rdb_systems(rdb_system_id);


ALTER TABLE ONLY public.tbl_rdb
    ADD CONSTRAINT fk_rdb_rdb_code_id FOREIGN KEY (rdb_code_id) REFERENCES public.tbl_rdb_codes(rdb_code_id);


ALTER TABLE ONLY public.tbl_rdb_systems
    ADD CONSTRAINT fk_rdb_systems_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_rdb_systems
    ADD CONSTRAINT fk_rdb_systems_location_id FOREIGN KEY (location_id) REFERENCES public.tbl_locations(location_id);


ALTER TABLE ONLY public.tbl_rdb
    ADD CONSTRAINT fk_rdb_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_relative_age_refs
    ADD CONSTRAINT fk_relative_age_refs_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_relative_age_refs
    ADD CONSTRAINT fk_relative_age_refs_relative_age_id FOREIGN KEY (relative_age_id) REFERENCES public.tbl_relative_ages(relative_age_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_relative_ages
    ADD CONSTRAINT fk_relative_ages_location_id FOREIGN KEY (location_id) REFERENCES public.tbl_locations(location_id);


ALTER TABLE ONLY public.tbl_relative_ages
    ADD CONSTRAINT fk_relative_ages_relative_age_type_id FOREIGN KEY (relative_age_type_id) REFERENCES public.tbl_relative_age_types(relative_age_type_id);


ALTER TABLE ONLY public.tbl_relative_dates
    ADD CONSTRAINT fk_relative_dates_dating_uncertainty_id FOREIGN KEY (dating_uncertainty_id) REFERENCES public.tbl_dating_uncertainty(dating_uncertainty_id);


ALTER TABLE ONLY public.tbl_relative_dates
    ADD CONSTRAINT fk_relative_dates_method_id FOREIGN KEY (method_id) REFERENCES public.tbl_methods(method_id);


ALTER TABLE ONLY public.tbl_relative_dates
    ADD CONSTRAINT fk_relative_dates_relative_age_id FOREIGN KEY (relative_age_id) REFERENCES public.tbl_relative_ages(relative_age_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_alt_refs
    ADD CONSTRAINT fk_sample_alt_refs_alt_ref_type_id FOREIGN KEY (alt_ref_type_id) REFERENCES public.tbl_alt_ref_types(alt_ref_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_alt_refs
    ADD CONSTRAINT fk_sample_alt_refs_physical_sample_id FOREIGN KEY (physical_sample_id) REFERENCES public.tbl_physical_samples(physical_sample_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_colours
    ADD CONSTRAINT fk_sample_colours_colour_id FOREIGN KEY (colour_id) REFERENCES public.tbl_colours(colour_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_colours
    ADD CONSTRAINT fk_sample_colours_physical_sample_id FOREIGN KEY (physical_sample_id) REFERENCES public.tbl_physical_samples(physical_sample_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_coordinates
    ADD CONSTRAINT fk_sample_coordinates_coordinate_method_dimension_id FOREIGN KEY (coordinate_method_dimension_id) REFERENCES public.tbl_coordinate_method_dimensions(coordinate_method_dimension_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_coordinates
    ADD CONSTRAINT fk_sample_coordinates_physical_sample_id FOREIGN KEY (physical_sample_id) REFERENCES public.tbl_physical_samples(physical_sample_id);


ALTER TABLE ONLY public.tbl_sample_description_sample_group_contexts
    ADD CONSTRAINT fk_sample_description_sample_group_contexts_sampling_context_id FOREIGN KEY (sampling_context_id) REFERENCES public.tbl_sample_group_sampling_contexts(sampling_context_id);


ALTER TABLE ONLY public.tbl_sample_description_sample_group_contexts
    ADD CONSTRAINT fk_sample_description_types_sample_group_context_id FOREIGN KEY (sample_description_type_id) REFERENCES public.tbl_sample_description_types(sample_description_type_id);


ALTER TABLE ONLY public.tbl_sample_descriptions
    ADD CONSTRAINT fk_sample_descriptions_physical_sample_id FOREIGN KEY (physical_sample_id) REFERENCES public.tbl_physical_samples(physical_sample_id);


ALTER TABLE ONLY public.tbl_sample_descriptions
    ADD CONSTRAINT fk_sample_descriptions_sample_description_type_id FOREIGN KEY (sample_description_type_id) REFERENCES public.tbl_sample_description_types(sample_description_type_id);


ALTER TABLE ONLY public.tbl_sample_dimensions
    ADD CONSTRAINT fk_sample_dimensions_dimension_id FOREIGN KEY (dimension_id) REFERENCES public.tbl_dimensions(dimension_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_dimensions
    ADD CONSTRAINT fk_sample_dimensions_measurement_method_id FOREIGN KEY (method_id) REFERENCES public.tbl_methods(method_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_dimensions
    ADD CONSTRAINT fk_sample_dimensions_physical_sample_id FOREIGN KEY (physical_sample_id) REFERENCES public.tbl_physical_samples(physical_sample_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_group_description_type_sampling_contexts
    ADD CONSTRAINT fk_sample_group_description_type_sampling_context_id FOREIGN KEY (sample_group_description_type_id) REFERENCES public.tbl_sample_group_description_types(sample_group_description_type_id);


ALTER TABLE ONLY public.tbl_sample_group_descriptions
    ADD CONSTRAINT fk_sample_group_descriptions_sample_group_description_type_id FOREIGN KEY (sample_group_description_type_id) REFERENCES public.tbl_sample_group_description_types(sample_group_description_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_group_dimensions
    ADD CONSTRAINT fk_sample_group_dimensions_dimension_id FOREIGN KEY (dimension_id) REFERENCES public.tbl_dimensions(dimension_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_group_dimensions
    ADD CONSTRAINT fk_sample_group_dimensions_sample_group_id FOREIGN KEY (sample_group_id) REFERENCES public.tbl_sample_groups(sample_group_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_group_images
    ADD CONSTRAINT fk_sample_group_images_image_type_id FOREIGN KEY (image_type_id) REFERENCES public.tbl_image_types(image_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_group_images
    ADD CONSTRAINT fk_sample_group_images_sample_group_id FOREIGN KEY (sample_group_id) REFERENCES public.tbl_sample_groups(sample_group_id);


ALTER TABLE ONLY public.tbl_sample_group_coordinates
    ADD CONSTRAINT fk_sample_group_positions_coordinate_method_dimension_id FOREIGN KEY (coordinate_method_dimension_id) REFERENCES public.tbl_coordinate_method_dimensions(coordinate_method_dimension_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_group_coordinates
    ADD CONSTRAINT fk_sample_group_positions_sample_group_id FOREIGN KEY (sample_group_id) REFERENCES public.tbl_sample_groups(sample_group_id);


ALTER TABLE ONLY public.tbl_sample_group_references
    ADD CONSTRAINT fk_sample_group_references_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_group_references
    ADD CONSTRAINT fk_sample_group_references_sample_group_id FOREIGN KEY (sample_group_id) REFERENCES public.tbl_sample_groups(sample_group_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_groups
    ADD CONSTRAINT fk_sample_group_sampling_context_id FOREIGN KEY (sampling_context_id) REFERENCES public.tbl_sample_group_sampling_contexts(sampling_context_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_group_description_type_sampling_contexts
    ADD CONSTRAINT fk_sample_group_sampling_context_id0 FOREIGN KEY (sampling_context_id) REFERENCES public.tbl_sample_group_sampling_contexts(sampling_context_id);


ALTER TABLE ONLY public.tbl_sample_groups
    ADD CONSTRAINT fk_sample_groups_method_id FOREIGN KEY (method_id) REFERENCES public.tbl_methods(method_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_group_descriptions
    ADD CONSTRAINT fk_sample_groups_sample_group_descriptions_id FOREIGN KEY (sample_group_id) REFERENCES public.tbl_sample_groups(sample_group_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_groups
    ADD CONSTRAINT fk_sample_groups_site_id FOREIGN KEY (site_id) REFERENCES public.tbl_sites(site_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_horizons
    ADD CONSTRAINT fk_sample_horizons_horizon_id FOREIGN KEY (horizon_id) REFERENCES public.tbl_horizons(horizon_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_horizons
    ADD CONSTRAINT fk_sample_horizons_physical_sample_id FOREIGN KEY (physical_sample_id) REFERENCES public.tbl_physical_samples(physical_sample_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_images
    ADD CONSTRAINT fk_sample_images_image_type_id FOREIGN KEY (image_type_id) REFERENCES public.tbl_image_types(image_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_images
    ADD CONSTRAINT fk_sample_images_physical_sample_id FOREIGN KEY (physical_sample_id) REFERENCES public.tbl_physical_samples(physical_sample_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sample_location_type_sampling_contexts
    ADD CONSTRAINT fk_sample_location_sampling_contexts_sampling_context_id FOREIGN KEY (sample_location_type_id) REFERENCES public.tbl_sample_location_types(sample_location_type_id);


ALTER TABLE ONLY public.tbl_sample_location_type_sampling_contexts
    ADD CONSTRAINT fk_sample_location_type_sampling_context_id FOREIGN KEY (sampling_context_id) REFERENCES public.tbl_sample_group_sampling_contexts(sampling_context_id);


ALTER TABLE ONLY public.tbl_sample_locations
    ADD CONSTRAINT fk_sample_locations_physical_sample_id FOREIGN KEY (physical_sample_id) REFERENCES public.tbl_physical_samples(physical_sample_id);


ALTER TABLE ONLY public.tbl_sample_locations
    ADD CONSTRAINT fk_sample_locations_sample_location_type_id FOREIGN KEY (sample_location_type_id) REFERENCES public.tbl_sample_location_types(sample_location_type_id);


ALTER TABLE ONLY public.tbl_sample_notes
    ADD CONSTRAINT fk_sample_notes_physical_sample_id FOREIGN KEY (physical_sample_id) REFERENCES public.tbl_physical_samples(physical_sample_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_physical_samples
    ADD CONSTRAINT fk_samples_sample_group_id FOREIGN KEY (sample_group_id) REFERENCES public.tbl_sample_groups(sample_group_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_seasons
    ADD CONSTRAINT fk_seasons_season_type_id FOREIGN KEY (season_type_id) REFERENCES public.tbl_season_types(season_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_site_images
    ADD CONSTRAINT fk_site_images_contact_id FOREIGN KEY (contact_id) REFERENCES public.tbl_contacts(contact_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_site_images
    ADD CONSTRAINT fk_site_images_image_type_id FOREIGN KEY (image_type_id) REFERENCES public.tbl_image_types(image_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_site_images
    ADD CONSTRAINT fk_site_images_site_id FOREIGN KEY (site_id) REFERENCES public.tbl_sites(site_id);


ALTER TABLE ONLY public.tbl_site_natgridrefs
    ADD CONSTRAINT fk_site_natgridrefs_method_id FOREIGN KEY (method_id) REFERENCES public.tbl_methods(method_id);


ALTER TABLE ONLY public.tbl_site_natgridrefs
    ADD CONSTRAINT fk_site_natgridrefs_sites_id FOREIGN KEY (site_id) REFERENCES public.tbl_sites(site_id);


ALTER TABLE ONLY public.tbl_site_other_records
    ADD CONSTRAINT fk_site_other_records_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_site_other_records
    ADD CONSTRAINT fk_site_other_records_record_type_id FOREIGN KEY (record_type_id) REFERENCES public.tbl_record_types(record_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_site_other_records
    ADD CONSTRAINT fk_site_other_records_site_id FOREIGN KEY (site_id) REFERENCES public.tbl_sites(site_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_site_preservation_status
    ADD CONSTRAINT "fk_site_preservation_status_site_id " FOREIGN KEY (site_id) REFERENCES public.tbl_sites(site_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_sites
    ADD CONSTRAINT fk_site_preservation_status_site_preservation_status_id FOREIGN KEY (site_preservation_status_id) REFERENCES public.tbl_site_preservation_status(site_preservation_status_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_site_references
    ADD CONSTRAINT fk_site_references_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_site_references
    ADD CONSTRAINT fk_site_references_site_id FOREIGN KEY (site_id) REFERENCES public.tbl_sites(site_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_species_associations
    ADD CONSTRAINT fk_species_associations_associated_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_species_associations
    ADD CONSTRAINT fk_species_associations_association_type_id FOREIGN KEY (association_type_id) REFERENCES public.tbl_species_association_types(association_type_id);


ALTER TABLE ONLY public.tbl_species_associations
    ADD CONSTRAINT fk_species_associations_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_species_associations
    ADD CONSTRAINT fk_species_associations_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id);


ALTER TABLE ONLY public.tbl_taxa_common_names
    ADD CONSTRAINT fk_taxa_common_names_language_id FOREIGN KEY (language_id) REFERENCES public.tbl_languages(language_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_taxa_common_names
    ADD CONSTRAINT fk_taxa_common_names_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_taxa_images
    ADD CONSTRAINT fk_taxa_images_image_type_id FOREIGN KEY (image_type_id) REFERENCES public.tbl_image_types(image_type_id);


ALTER TABLE ONLY public.tbl_taxa_images
    ADD CONSTRAINT fk_taxa_images_taxa_tree_master_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id);


ALTER TABLE ONLY public.tbl_taxa_measured_attributes
    ADD CONSTRAINT fk_taxa_measured_attributes_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_taxa_reference_specimens
    ADD CONSTRAINT fk_taxa_reference_specimens_contact_id FOREIGN KEY (contact_id) REFERENCES public.tbl_contacts(contact_id);


ALTER TABLE ONLY public.tbl_taxa_reference_specimens
    ADD CONSTRAINT fk_taxa_reference_specimens_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id);


ALTER TABLE ONLY public.tbl_taxa_seasonality
    ADD CONSTRAINT fk_taxa_seasonality_activity_type_id FOREIGN KEY (activity_type_id) REFERENCES public.tbl_activity_types(activity_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_taxa_seasonality
    ADD CONSTRAINT fk_taxa_seasonality_location_id FOREIGN KEY (location_id) REFERENCES public.tbl_locations(location_id);


ALTER TABLE ONLY public.tbl_taxa_seasonality
    ADD CONSTRAINT fk_taxa_seasonality_season_id FOREIGN KEY (season_id) REFERENCES public.tbl_seasons(season_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_taxa_seasonality
    ADD CONSTRAINT fk_taxa_seasonality_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_taxa_synonyms
    ADD CONSTRAINT fk_taxa_synonyms_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_taxa_synonyms
    ADD CONSTRAINT fk_taxa_synonyms_family_id FOREIGN KEY (family_id) REFERENCES public.tbl_taxa_tree_families(family_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_taxa_synonyms
    ADD CONSTRAINT fk_taxa_synonyms_genus_id FOREIGN KEY (genus_id) REFERENCES public.tbl_taxa_tree_genera(genus_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_taxa_synonyms
    ADD CONSTRAINT fk_taxa_synonyms_taxa_tree_author_id FOREIGN KEY (author_id) REFERENCES public.tbl_taxa_tree_authors(author_id);


ALTER TABLE ONLY public.tbl_taxa_synonyms
    ADD CONSTRAINT fk_taxa_synonyms_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_taxa_tree_families
    ADD CONSTRAINT fk_taxa_tree_families_order_id FOREIGN KEY (order_id) REFERENCES public.tbl_taxa_tree_orders(order_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_taxa_tree_genera
    ADD CONSTRAINT fk_taxa_tree_genera_family_id FOREIGN KEY (family_id) REFERENCES public.tbl_taxa_tree_families(family_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_taxa_tree_master
    ADD CONSTRAINT fk_taxa_tree_master_author_id FOREIGN KEY (author_id) REFERENCES public.tbl_taxa_tree_authors(author_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_taxa_tree_master
    ADD CONSTRAINT fk_taxa_tree_master_genus_id FOREIGN KEY (genus_id) REFERENCES public.tbl_taxa_tree_genera(genus_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_taxa_tree_orders
    ADD CONSTRAINT fk_taxa_tree_orders_record_type_id FOREIGN KEY (record_type_id) REFERENCES public.tbl_record_types(record_type_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_taxonomic_order_biblio
    ADD CONSTRAINT fk_taxonomic_order_biblio_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_taxonomic_order_biblio
    ADD CONSTRAINT fk_taxonomic_order_biblio_taxonomic_order_system_id FOREIGN KEY (taxonomic_order_system_id) REFERENCES public.tbl_taxonomic_order_systems(taxonomic_order_system_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_taxonomic_order
    ADD CONSTRAINT fk_taxonomic_order_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_taxonomic_order
    ADD CONSTRAINT fk_taxonomic_order_taxonomic_order_system_id FOREIGN KEY (taxonomic_order_system_id) REFERENCES public.tbl_taxonomic_order_systems(taxonomic_order_system_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_taxonomy_notes
    ADD CONSTRAINT fk_taxonomy_notes_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_taxonomy_notes
    ADD CONSTRAINT fk_taxonomy_notes_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_dendro_dates
    ADD CONSTRAINT fk_tbl_age_types_age_type_id FOREIGN KEY (age_type_id) REFERENCES public.tbl_age_types(age_type_id);


ALTER TABLE ONLY public.tbl_dataset_methods
    ADD CONSTRAINT fk_tbl_dataset_methods_to_tbl_datasets FOREIGN KEY (dataset_id) REFERENCES public.tbl_datasets(dataset_id);


ALTER TABLE ONLY public.tbl_dataset_methods
    ADD CONSTRAINT fk_tbl_dataset_methods_to_tbl_methods FOREIGN KEY (method_id) REFERENCES public.tbl_methods(method_id);


ALTER TABLE ONLY public.tbl_rdb
    ADD CONSTRAINT fk_tbl_rdb_tbl_location_id FOREIGN KEY (location_id) REFERENCES public.tbl_locations(location_id);


ALTER TABLE ONLY public.tbl_relative_dates
    ADD CONSTRAINT fk_tbl_relative_dates_to_tbl_analysis_entities FOREIGN KEY (analysis_entity_id) REFERENCES public.tbl_analysis_entities(analysis_entity_id);


ALTER TABLE ONLY public.tbl_sample_group_notes
    ADD CONSTRAINT fk_tbl_sample_group_notes_sample_groups FOREIGN KEY (sample_group_id) REFERENCES public.tbl_sample_groups(sample_group_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_tephra_dates
    ADD CONSTRAINT fk_tephra_dates_analysis_entity_id FOREIGN KEY (analysis_entity_id) REFERENCES public.tbl_analysis_entities(analysis_entity_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_tephra_dates
    ADD CONSTRAINT fk_tephra_dates_dating_uncertainty_id FOREIGN KEY (dating_uncertainty_id) REFERENCES public.tbl_dating_uncertainty(dating_uncertainty_id);


ALTER TABLE ONLY public.tbl_tephra_dates
    ADD CONSTRAINT fk_tephra_dates_tephra_id FOREIGN KEY (tephra_id) REFERENCES public.tbl_tephras(tephra_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_tephra_refs
    ADD CONSTRAINT fk_tephra_refs_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_tephra_refs
    ADD CONSTRAINT fk_tephra_refs_tephra_id FOREIGN KEY (tephra_id) REFERENCES public.tbl_tephras(tephra_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_text_biology
    ADD CONSTRAINT fk_text_biology_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_text_biology
    ADD CONSTRAINT fk_text_biology_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_text_distribution
    ADD CONSTRAINT fk_text_distribution_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_text_distribution
    ADD CONSTRAINT fk_text_distribution_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_text_identification_keys
    ADD CONSTRAINT fk_text_identification_keys_biblio_id FOREIGN KEY (biblio_id) REFERENCES public.tbl_biblio(biblio_id) ON UPDATE CASCADE;


ALTER TABLE ONLY public.tbl_text_identification_keys
    ADD CONSTRAINT fk_text_identification_keys_taxon_id FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_abundance_properties
    ADD CONSTRAINT tbl_abundance_properties_abundance_id_fkey FOREIGN KEY (abundance_id) REFERENCES public.tbl_abundances(abundance_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_abundance_properties
    ADD CONSTRAINT tbl_abundance_properties_property_type_id_fkey FOREIGN KEY (property_type_id) REFERENCES public.tbl_property_types(property_type_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_boolean_values
    ADD CONSTRAINT tbl_analysis_boolean_values_analysis_value_id_fkey FOREIGN KEY (analysis_value_id) REFERENCES public.tbl_analysis_values(analysis_value_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_categorical_values
    ADD CONSTRAINT tbl_analysis_categorical_values_analysis_value_id_fkey FOREIGN KEY (analysis_value_id) REFERENCES public.tbl_analysis_values(analysis_value_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_categorical_values
    ADD CONSTRAINT tbl_analysis_categorical_values_value_type_item_id_fkey FOREIGN KEY (value_type_item_id) REFERENCES public.tbl_value_type_items(value_type_item_id);


ALTER TABLE ONLY public.tbl_analysis_dating_ranges
    ADD CONSTRAINT tbl_analysis_dating_ranges_age_type_id_fkey FOREIGN KEY (age_type_id) REFERENCES public.tbl_age_types(age_type_id);


ALTER TABLE ONLY public.tbl_analysis_dating_ranges
    ADD CONSTRAINT tbl_analysis_dating_ranges_analysis_value_id_fkey FOREIGN KEY (analysis_value_id) REFERENCES public.tbl_analysis_values(analysis_value_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_dating_ranges
    ADD CONSTRAINT tbl_analysis_dating_ranges_dating_uncertainty_id_fkey FOREIGN KEY (dating_uncertainty_id) REFERENCES public.tbl_dating_uncertainty(dating_uncertainty_id);


ALTER TABLE ONLY public.tbl_analysis_dating_ranges
    ADD CONSTRAINT tbl_analysis_dating_ranges_high_qualifier_fkey FOREIGN KEY (high_qualifier) REFERENCES public.tbl_value_qualifier_symbols(symbol);


ALTER TABLE ONLY public.tbl_analysis_dating_ranges
    ADD CONSTRAINT tbl_analysis_dating_ranges_low_qualifier_fkey FOREIGN KEY (low_qualifier) REFERENCES public.tbl_value_qualifier_symbols(symbol);


ALTER TABLE ONLY public.tbl_analysis_dating_ranges
    ADD CONSTRAINT tbl_analysis_dating_ranges_season_id_fkey FOREIGN KEY (season_id) REFERENCES public.tbl_seasons(season_id);


ALTER TABLE ONLY public.tbl_analysis_identifiers
    ADD CONSTRAINT tbl_analysis_identifiers_analysis_value_id_fkey FOREIGN KEY (analysis_value_id) REFERENCES public.tbl_analysis_values(analysis_value_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_integer_ranges
    ADD CONSTRAINT tbl_analysis_integer_ranges_analysis_value_id_fkey FOREIGN KEY (analysis_value_id) REFERENCES public.tbl_analysis_values(analysis_value_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_integer_ranges
    ADD CONSTRAINT tbl_analysis_integer_ranges_high_qualifier_fkey FOREIGN KEY (high_qualifier) REFERENCES public.tbl_value_qualifier_symbols(symbol);


ALTER TABLE ONLY public.tbl_analysis_integer_ranges
    ADD CONSTRAINT tbl_analysis_integer_ranges_low_qualifier_fkey FOREIGN KEY (low_qualifier) REFERENCES public.tbl_value_qualifier_symbols(symbol);


ALTER TABLE ONLY public.tbl_analysis_integer_values
    ADD CONSTRAINT tbl_analysis_integer_values_analysis_value_id_fkey FOREIGN KEY (analysis_value_id) REFERENCES public.tbl_analysis_values(analysis_value_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_integer_values
    ADD CONSTRAINT tbl_analysis_integer_values_qualifier_fkey FOREIGN KEY (qualifier) REFERENCES public.tbl_value_qualifier_symbols(symbol);


ALTER TABLE ONLY public.tbl_analysis_notes
    ADD CONSTRAINT tbl_analysis_notes_analysis_value_id_fkey FOREIGN KEY (analysis_value_id) REFERENCES public.tbl_analysis_values(analysis_value_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_numerical_ranges
    ADD CONSTRAINT tbl_analysis_numerical_ranges_analysis_value_id_fkey FOREIGN KEY (analysis_value_id) REFERENCES public.tbl_analysis_values(analysis_value_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_numerical_ranges
    ADD CONSTRAINT tbl_analysis_numerical_ranges_high_qualifier_fkey FOREIGN KEY (high_qualifier) REFERENCES public.tbl_value_qualifier_symbols(symbol);


ALTER TABLE ONLY public.tbl_analysis_numerical_ranges
    ADD CONSTRAINT tbl_analysis_numerical_ranges_low_qualifier_fkey FOREIGN KEY (low_qualifier) REFERENCES public.tbl_value_qualifier_symbols(symbol);


ALTER TABLE ONLY public.tbl_analysis_numerical_values
    ADD CONSTRAINT tbl_analysis_numerical_values_analysis_value_id_fkey FOREIGN KEY (analysis_value_id) REFERENCES public.tbl_analysis_values(analysis_value_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_numerical_values
    ADD CONSTRAINT tbl_analysis_numerical_values_qualifier_fkey FOREIGN KEY (qualifier) REFERENCES public.tbl_value_qualifier_symbols(symbol);


ALTER TABLE ONLY public.tbl_analysis_taxon_counts
    ADD CONSTRAINT tbl_analysis_taxon_counts_analysis_value_id_fkey FOREIGN KEY (analysis_value_id) REFERENCES public.tbl_analysis_values(analysis_value_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_taxon_counts
    ADD CONSTRAINT tbl_analysis_taxon_counts_taxon_id_fkey FOREIGN KEY (taxon_id) REFERENCES public.tbl_taxa_tree_master(taxon_id);


ALTER TABLE ONLY public.tbl_analysis_value_dimensions
    ADD CONSTRAINT tbl_analysis_value_dimensions_analysis_value_id_fkey FOREIGN KEY (analysis_value_id) REFERENCES public.tbl_analysis_values(analysis_value_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_value_dimensions
    ADD CONSTRAINT tbl_analysis_value_dimensions_dimension_id_fkey FOREIGN KEY (dimension_id) REFERENCES public.tbl_dimensions(dimension_id);


ALTER TABLE ONLY public.tbl_analysis_values
    ADD CONSTRAINT tbl_analysis_values_analysis_entity_id_fkey FOREIGN KEY (analysis_entity_id) REFERENCES public.tbl_analysis_entities(analysis_entity_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_analysis_values
    ADD CONSTRAINT tbl_analysis_values_value_class_id_fkey FOREIGN KEY (value_class_id) REFERENCES public.tbl_value_classes(value_class_id);


ALTER TABLE ONLY public.tbl_property_types
    ADD CONSTRAINT tbl_property_types_value_class_id_fkey FOREIGN KEY (value_class_id) REFERENCES public.tbl_value_classes(value_class_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_property_types
    ADD CONSTRAINT tbl_property_types_value_type_id_fkey FOREIGN KEY (value_type_id) REFERENCES public.tbl_value_types(value_type_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_sample_dimensions
    ADD CONSTRAINT tbl_sample_dimensions_qualifier_id_fkey FOREIGN KEY (qualifier_id) REFERENCES public.tbl_value_qualifiers(qualifier_id);


ALTER TABLE ONLY public.tbl_sample_group_dimensions
    ADD CONSTRAINT tbl_sample_group_dimensions_qualifier_id_fkey FOREIGN KEY (qualifier_id) REFERENCES public.tbl_value_qualifiers(qualifier_id);


ALTER TABLE ONLY public.tbl_site_properties
    ADD CONSTRAINT tbl_site_properties_property_type_id_fkey FOREIGN KEY (property_type_id) REFERENCES public.tbl_property_types(property_type_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_site_properties
    ADD CONSTRAINT tbl_site_properties_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.tbl_sites(site_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_site_site_types
    ADD CONSTRAINT tbl_site_site_types_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.tbl_sites(site_id) ON UPDATE CASCADE ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_site_site_types
    ADD CONSTRAINT tbl_site_site_types_site_type_id_fkey FOREIGN KEY (site_type_id) REFERENCES public.tbl_site_types(site_type_id) ON UPDATE CASCADE ON DELETE RESTRICT;


ALTER TABLE ONLY public.tbl_site_types
    ADD CONSTRAINT tbl_site_types_site_type_group_id_fkey FOREIGN KEY (site_type_group_id) REFERENCES public.tbl_site_type_groups(site_type_group_id) ON UPDATE CASCADE ON DELETE RESTRICT;


ALTER TABLE ONLY public.tbl_value_classes
    ADD CONSTRAINT tbl_value_classes_method_id_fkey FOREIGN KEY (method_id) REFERENCES public.tbl_methods(method_id);


ALTER TABLE ONLY public.tbl_value_classes
    ADD CONSTRAINT tbl_value_classes_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.tbl_value_classes(value_class_id);


ALTER TABLE ONLY public.tbl_value_classes
    ADD CONSTRAINT tbl_value_classes_value_type_id_fkey FOREIGN KEY (value_type_id) REFERENCES public.tbl_value_types(value_type_id);


ALTER TABLE ONLY public.tbl_value_qualifier_symbols
    ADD CONSTRAINT tbl_value_qualifier_symbols_cardinal_qualifier_id_fkey FOREIGN KEY (cardinal_qualifier_id) REFERENCES public.tbl_value_qualifiers(qualifier_id);


ALTER TABLE ONLY public.tbl_value_type_items
    ADD CONSTRAINT tbl_value_type_items_value_type_id_fkey FOREIGN KEY (value_type_id) REFERENCES public.tbl_value_types(value_type_id) ON DELETE CASCADE;


ALTER TABLE ONLY public.tbl_value_types
    ADD CONSTRAINT tbl_value_types_data_type_id_fkey FOREIGN KEY (data_type_id) REFERENCES public.tbl_data_types(data_type_id);


ALTER TABLE ONLY public.tbl_value_types
    ADD CONSTRAINT tbl_value_types_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.tbl_units(unit_id);


--
-- PostgreSQL database dump complete
--

\unrestrict MhDjbXsxEVNxhI2OFdMGiXBEv3SllbmXSIagzraGnJIMcgqtKItyYuF3oVChIrN

