--
-- PostgreSQL database dump
--

\restrict M3RKcBauwMs1QCLqPW9hQdM0MLfF73NxiHumgRQePNPOIZuvkzCzqKkUFNbqhjW

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

set default_tablespace = '';


create index idx_abundance_modifications_abundance_id on public.tbl_abundance_modifications using btree (
    abundance_id
);


create index idx_abundance_modifications_modification_type_id on public.tbl_abundance_modifications using btree (
    modification_type_id
);


create index idx_abundances_abundance_element_id on public.tbl_abundances using btree (
    abundance_element_id
);


create index idx_abundances_analysis_entity_id on public.tbl_abundances using btree (
    analysis_entity_id
);


create index idx_abundances_taxon_id on public.tbl_abundances using btree (
    taxon_id
);


create index idx_analysis_entities_dataset_id on public.tbl_analysis_entities using btree (
    dataset_id
);


create index idx_analysis_entities_physical_sample_id on public.tbl_analysis_entities using btree (
    physical_sample_id
);


create index idx_analysis_entity_prep_methods_analysis_entity_id on public.tbl_analysis_entity_prep_methods using btree (
    analysis_entity_id
);


create index idx_analysis_entity_prep_methods_method_id on public.tbl_analysis_entity_prep_methods using btree (
    method_id
);


create index idx_biblio_id on public.tbl_sample_group_references using btree (
    biblio_id
);


create index idx_datasets_biblio_id on public.tbl_datasets using btree (
    biblio_id
);


create index idx_datasets_data_type_id on public.tbl_datasets using btree (
    data_type_id
);


create index idx_datasets_master_set_id on public.tbl_datasets using btree (
    master_set_id
);


create index idx_datasets_method_id on public.tbl_datasets using btree (
    method_id
);


create index idx_datasets_project_id on public.tbl_datasets using btree (
    project_id
);


create index idx_datasets_updated_dataset_id on public.tbl_datasets using btree (
    updated_dataset_id
);


create index idx_ecocode_groups_ecocode_system_id on public.tbl_ecocode_groups using btree (
    ecocode_system_id
);


create index idx_ecocode_groups_name on public.tbl_ecocode_groups using btree (
    name
);


create index idx_ecocode_systems_biblio_id on public.tbl_ecocode_systems using btree (
    biblio_id
);


create index idx_ecocode_systems_ecocode_group_id on public.tbl_ecocode_systems using btree (
    name
);


create index idx_ecocodes_ecocode_definition_id on public.tbl_ecocodes using btree (
    ecocode_definition_id
);


create index idx_ecocodes_taxon_id on public.tbl_ecocodes using btree (
    taxon_id
);


create index idx_features_feature_type_id on public.tbl_features using btree (
    feature_type_id
);


create index idx_languages_language_id on public.tbl_languages using btree (
    language_id
);


create index idx_locations_location_type_id on public.tbl_locations using btree (
    location_type_id
);


create index idx_measured_values_analysis_entity_id on public.tbl_measured_values using btree (
    analysis_entity_id
);


create index idx_physical_sample_features_feature_id on public.tbl_physical_sample_features using btree (
    feature_id
);


create index idx_physical_sample_features_physical_sample_id on public.tbl_physical_sample_features using btree (
    physical_sample_id
);


create index idx_physical_samples_alt_ref_type_id on public.tbl_physical_samples using btree (
    alt_ref_type_id
);


create index idx_physical_samples_sample_group_id on public.tbl_physical_samples using btree (
    sample_group_id
);


create index idx_physical_samples_sample_type_id on public.tbl_physical_samples using btree (
    sample_type_id
);


create index idx_sample_alt_refs_alt_ref_type_id on public.tbl_sample_alt_refs using btree (
    alt_ref_type_id
);


create index idx_sample_alt_refs_physical_sample_id on public.tbl_sample_alt_refs using btree (
    physical_sample_id
);


create index idx_sample_coordinates_coordinate_method_dimension_id on public.tbl_sample_coordinates using btree (
    coordinate_method_dimension_id
);


create index idx_sample_coordinates_physical_sample_id on public.tbl_sample_coordinates using btree (
    physical_sample_id
);


create index idx_sample_group_id on public.tbl_sample_group_references using btree (
    sample_group_id
);


create index idx_sample_horizons_horizon_id on public.tbl_sample_horizons using btree (
    horizon_id
);


create index idx_sample_horizons_physical_sample_id on public.tbl_sample_horizons using btree (
    physical_sample_id
);


create index idx_sample_notes_physical_sample_id on public.tbl_sample_notes using btree (
    physical_sample_id
);


create index idx_site_locations_location_id on public.tbl_site_locations using btree (
    location_id
);


create index idx_site_locations_site_id on public.tbl_site_locations using btree (
    site_id
);


create index idx_taxa_common_names_language_id on public.tbl_taxa_common_names using btree (
    language_id
);


create index idx_taxa_common_names_taxon_id on public.tbl_taxa_common_names using btree (
    taxon_id
);


create index idx_taxa_tree_authors_name on public.tbl_taxa_tree_authors using btree (
    author_name
);


create index idx_taxa_tree_families_name on public.tbl_taxa_tree_families using btree (
    family_name
);


create index idx_taxa_tree_families_order_id on public.tbl_taxa_tree_families using btree (
    order_id
);


create index idx_taxa_tree_genera_family_id on public.tbl_taxa_tree_genera using btree (
    family_id
);


create index idx_taxa_tree_genera_name on public.tbl_taxa_tree_genera using btree (
    genus_name
);


create index idx_taxa_tree_master_author_id on public.tbl_taxa_tree_master using btree (
    author_id
);


create index idx_taxa_tree_master_genus_id on public.tbl_taxa_tree_master using btree (
    genus_id
);


create index idx_taxa_tree_orders_order_id on public.tbl_taxa_tree_orders using btree (
    order_id
);


create index idx_taxonomic_order_biblio_biblio_id on public.tbl_taxonomic_order_biblio using btree (
    biblio_id
);


create index idx_taxonomic_order_biblio_taxonomic_order_biblio_id on public.tbl_taxonomic_order_biblio using btree (
    taxonomic_order_biblio_id
);


create index idx_taxonomic_order_biblio_taxonomic_order_system_id on public.tbl_taxonomic_order_biblio using btree (
    taxonomic_order_system_id
);


create index idx_taxonomic_order_systems_taxonomic_system_id on public.tbl_taxonomic_order_systems using btree (
    taxonomic_order_system_id
);


create index idx_taxonomic_order_taxon_id on public.tbl_taxonomic_order using btree (
    taxon_id
);


create index idx_taxonomic_order_taxonomic_code on public.tbl_taxonomic_order using btree (
    taxonomic_code
);


create index idx_taxonomic_order_taxonomic_order_id on public.tbl_taxonomic_order using btree (
    taxonomic_order_id
);


create index idx_taxonomic_order_taxonomic_system_id on public.tbl_taxonomic_order using btree (
    taxonomic_order_system_id
);


create index idx_tbl_physical_sample_features_feature_id on public.tbl_physical_sample_features using btree (
    feature_id
);


create index tbl_biblio_norm_trgm on public.tbl_biblio using gin (
    authority.immutable_unaccent(lower(full_reference)) public.gin_trgm_ops
);


create index tbl_data_type_groups_norm_trgm on public.tbl_data_type_groups using gin (
    authority.immutable_unaccent(
        lower((data_type_group_name)::text)
    ) public.gin_trgm_ops
);


create index tbl_data_types_norm_trgm on public.tbl_data_types using gin (
    authority.immutable_unaccent(
        lower((data_type_name)::text)
    ) public.gin_trgm_ops
);


create index tbl_dating_uncertainty_norm_trgm on public.tbl_dating_uncertainty using gin (
    authority.immutable_unaccent(lower((uncertainty)::text)) public.gin_trgm_ops
);


create index tbl_ecocode_groups_idx_name on public.tbl_ecocode_groups using btree (
    name
);


create index tbl_feature_types_norm_trgm on public.tbl_feature_types using gin (
    authority.immutable_unaccent(
        lower((feature_type_name)::text)
    ) public.gin_trgm_ops
);


create index tbl_features_norm_trgm on public.tbl_features using gin (
    authority.immutable_unaccent(
        lower((feature_name)::text)
    ) public.gin_trgm_ops
);


create index tbl_location_types_norm_trgm on public.tbl_location_types using gin (
    authority.immutable_unaccent(
        lower((location_type)::text)
    ) public.gin_trgm_ops
);


create index tbl_locations_norm_trgm on public.tbl_locations using gin (
    authority.immutable_unaccent(
        lower((location_name)::text)
    ) public.gin_trgm_ops
);


create index tbl_method_groups_norm_trgm on public.tbl_method_groups using gin (
    authority.immutable_unaccent(lower((group_name)::text)) public.gin_trgm_ops
);


create index tbl_methods_norm_trgm on public.tbl_methods using gin (
    authority.immutable_unaccent(lower((method_name)::text)) public.gin_trgm_ops
);


create index tbl_modification_types_norm_trgm on public.tbl_modification_types using gin (
    authority.immutable_unaccent(
        lower((modification_type_name)::text)
    ) public.gin_trgm_ops
);


create index tbl_record_types_norm_trgm on public.tbl_record_types using gin (
    authority.immutable_unaccent(
        lower((record_type_name)::text)
    ) public.gin_trgm_ops
);


create index tbl_relative_age_types_norm_trgm on public.tbl_relative_age_types using gin (
    authority.immutable_unaccent(lower((age_type)::text)) public.gin_trgm_ops
);


create index tbl_relative_ages_norm_trgm on public.tbl_relative_ages using gin (
    authority.immutable_unaccent(
        lower((relative_age_name)::text)
    ) public.gin_trgm_ops
);


create index tbl_sample_description_types_norm_trgm on public.tbl_sample_description_types using gin (
    authority.immutable_unaccent(lower((type_name)::text)) public.gin_trgm_ops
);


create index tbl_sample_group_description_types_norm_trgm on public.tbl_sample_group_description_types using gin (
    authority.immutable_unaccent(lower((type_name)::text)) public.gin_trgm_ops
);


create index tbl_sample_group_sampling_contexts_norm_trgm on public.tbl_sample_group_sampling_contexts using gin (
    authority.immutable_unaccent(
        lower((sampling_context)::text)
    ) public.gin_trgm_ops
);


create index tbl_sample_location_types_norm_trgm on public.tbl_sample_location_types using gin (
    authority.immutable_unaccent(
        lower((location_type)::text)
    ) public.gin_trgm_ops
);


create index tbl_sample_types_norm_trgm on public.tbl_sample_types using gin (
    authority.immutable_unaccent(lower((type_name)::text)) public.gin_trgm_ops
);


create index tbl_taxa_synonyms_norm_trgm on public.tbl_taxa_synonyms using gin (
    authority.immutable_unaccent(lower((synonym)::text)) public.gin_trgm_ops
);


create index tbl_taxa_tree_authors_norm_trgm on public.tbl_taxa_tree_authors using gin (
    authority.immutable_unaccent(lower((author_name)::text)) public.gin_trgm_ops
);


create index tbl_taxa_tree_families_norm_trgm on public.tbl_taxa_tree_families using gin (
    authority.immutable_unaccent(lower((family_name)::text)) public.gin_trgm_ops
);


create index tbl_taxa_tree_genera_norm_trgm on public.tbl_taxa_tree_genera using gin (
    authority.immutable_unaccent(lower((genus_name)::text)) public.gin_trgm_ops
);


create index tbl_taxa_tree_master_norm_trgm on public.tbl_taxa_tree_master using gin (
    authority.immutable_unaccent(lower((species)::text)) public.gin_trgm_ops
);


create index tbl_taxa_tree_orders_norm_trgm on public.tbl_taxa_tree_orders using gin (
    authority.immutable_unaccent(lower((order_name)::text)) public.gin_trgm_ops
);


create index tbl_taxonomic_order_code_trgm on public.tbl_taxonomic_order using gin (
    ((taxonomic_code)::text) public.gin_trgm_ops
);


create index tbl_taxonomic_order_systems_norm_trgm on public.tbl_taxonomic_order_systems using gin (
    authority.immutable_unaccent(lower((system_name)::text)) public.gin_trgm_ops
);


create index tbl_taxonomy_notes_norm_trgm on public.tbl_taxonomy_notes using gin (
    authority.immutable_unaccent(lower(taxonomy_notes)) public.gin_trgm_ops
);
