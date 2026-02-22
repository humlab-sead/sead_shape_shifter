--
-- PostgreSQL database dump
--

\restrict M3RKcBauwMs1QCLqPW9hQdM0MLfF73NxiHumgRQePNPOIZuvkzCzqKkUFNbqhjW

-- Dumped from database version 16.4 (Debian 16.4-1.pgdg110+2)
-- Dumped by pg_dump version 18.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';


CREATE INDEX idx_abundance_modifications_abundance_id ON public.tbl_abundance_modifications USING btree (
    abundance_id
);


CREATE INDEX idx_abundance_modifications_modification_type_id ON public.tbl_abundance_modifications USING btree (
    modification_type_id
);


CREATE INDEX idx_abundances_abundance_element_id ON public.tbl_abundances USING btree (
    abundance_element_id
);


CREATE INDEX idx_abundances_analysis_entity_id ON public.tbl_abundances USING btree (
    analysis_entity_id
);


CREATE INDEX idx_abundances_taxon_id ON public.tbl_abundances USING btree (
    taxon_id
);


CREATE INDEX idx_analysis_entities_dataset_id ON public.tbl_analysis_entities USING btree (
    dataset_id
);


CREATE INDEX idx_analysis_entities_physical_sample_id ON public.tbl_analysis_entities USING btree (
    physical_sample_id
);


CREATE INDEX idx_analysis_entity_prep_methods_analysis_entity_id ON public.tbl_analysis_entity_prep_methods USING btree (
    analysis_entity_id
);


CREATE INDEX idx_analysis_entity_prep_methods_method_id ON public.tbl_analysis_entity_prep_methods USING btree (
    method_id
);


CREATE INDEX idx_biblio_id ON public.tbl_sample_group_references USING btree (
    biblio_id
);


CREATE INDEX idx_datasets_biblio_id ON public.tbl_datasets USING btree (
    biblio_id
);


CREATE INDEX idx_datasets_data_type_id ON public.tbl_datasets USING btree (
    data_type_id
);


CREATE INDEX idx_datasets_master_set_id ON public.tbl_datasets USING btree (
    master_set_id
);


CREATE INDEX idx_datasets_method_id ON public.tbl_datasets USING btree (
    method_id
);


CREATE INDEX idx_datasets_project_id ON public.tbl_datasets USING btree (
    project_id
);


CREATE INDEX idx_datasets_updated_dataset_id ON public.tbl_datasets USING btree (
    updated_dataset_id
);


CREATE INDEX idx_ecocode_groups_ecocode_system_id ON public.tbl_ecocode_groups USING btree (
    ecocode_system_id
);


CREATE INDEX idx_ecocode_groups_name ON public.tbl_ecocode_groups USING btree (
    name
);


CREATE INDEX idx_ecocode_systems_biblio_id ON public.tbl_ecocode_systems USING btree (
    biblio_id
);


CREATE INDEX idx_ecocode_systems_ecocode_group_id ON public.tbl_ecocode_systems USING btree (
    name
);


CREATE INDEX idx_ecocodes_ecocode_definition_id ON public.tbl_ecocodes USING btree (
    ecocode_definition_id
);


CREATE INDEX idx_ecocodes_taxon_id ON public.tbl_ecocodes USING btree (
    taxon_id
);


CREATE INDEX idx_features_feature_type_id ON public.tbl_features USING btree (
    feature_type_id
);


CREATE INDEX idx_languages_language_id ON public.tbl_languages USING btree (
    language_id
);


CREATE INDEX idx_locations_location_type_id ON public.tbl_locations USING btree (
    location_type_id
);


CREATE INDEX idx_measured_values_analysis_entity_id ON public.tbl_measured_values USING btree (
    analysis_entity_id
);


CREATE INDEX idx_physical_sample_features_feature_id ON public.tbl_physical_sample_features USING btree (
    feature_id
);


CREATE INDEX idx_physical_sample_features_physical_sample_id ON public.tbl_physical_sample_features USING btree (
    physical_sample_id
);


CREATE INDEX idx_physical_samples_alt_ref_type_id ON public.tbl_physical_samples USING btree (
    alt_ref_type_id
);


CREATE INDEX idx_physical_samples_sample_group_id ON public.tbl_physical_samples USING btree (
    sample_group_id
);


CREATE INDEX idx_physical_samples_sample_type_id ON public.tbl_physical_samples USING btree (
    sample_type_id
);


CREATE INDEX idx_sample_alt_refs_alt_ref_type_id ON public.tbl_sample_alt_refs USING btree (
    alt_ref_type_id
);


CREATE INDEX idx_sample_alt_refs_physical_sample_id ON public.tbl_sample_alt_refs USING btree (
    physical_sample_id
);


CREATE INDEX idx_sample_coordinates_coordinate_method_dimension_id ON public.tbl_sample_coordinates USING btree (
    coordinate_method_dimension_id
);


CREATE INDEX idx_sample_coordinates_physical_sample_id ON public.tbl_sample_coordinates USING btree (
    physical_sample_id
);


CREATE INDEX idx_sample_group_id ON public.tbl_sample_group_references USING btree (
    sample_group_id
);


CREATE INDEX idx_sample_horizons_horizon_id ON public.tbl_sample_horizons USING btree (
    horizon_id
);


CREATE INDEX idx_sample_horizons_physical_sample_id ON public.tbl_sample_horizons USING btree (
    physical_sample_id
);


CREATE INDEX idx_sample_notes_physical_sample_id ON public.tbl_sample_notes USING btree (
    physical_sample_id
);


CREATE INDEX idx_site_locations_location_id ON public.tbl_site_locations USING btree (
    location_id
);


CREATE INDEX idx_site_locations_site_id ON public.tbl_site_locations USING btree (
    site_id
);


CREATE INDEX idx_taxa_common_names_language_id ON public.tbl_taxa_common_names USING btree (
    language_id
);


CREATE INDEX idx_taxa_common_names_taxon_id ON public.tbl_taxa_common_names USING btree (
    taxon_id
);


CREATE INDEX idx_taxa_tree_authors_name ON public.tbl_taxa_tree_authors USING btree (
    author_name
);


CREATE INDEX idx_taxa_tree_families_name ON public.tbl_taxa_tree_families USING btree (
    family_name
);


CREATE INDEX idx_taxa_tree_families_order_id ON public.tbl_taxa_tree_families USING btree (
    order_id
);


CREATE INDEX idx_taxa_tree_genera_family_id ON public.tbl_taxa_tree_genera USING btree (
    family_id
);


CREATE INDEX idx_taxa_tree_genera_name ON public.tbl_taxa_tree_genera USING btree (
    genus_name
);


CREATE INDEX idx_taxa_tree_master_author_id ON public.tbl_taxa_tree_master USING btree (
    author_id
);


CREATE INDEX idx_taxa_tree_master_genus_id ON public.tbl_taxa_tree_master USING btree (
    genus_id
);


CREATE INDEX idx_taxa_tree_orders_order_id ON public.tbl_taxa_tree_orders USING btree (
    order_id
);


CREATE INDEX idx_taxonomic_order_biblio_biblio_id ON public.tbl_taxonomic_order_biblio USING btree (
    biblio_id
);


CREATE INDEX idx_taxonomic_order_biblio_taxonomic_order_biblio_id ON public.tbl_taxonomic_order_biblio USING btree (
    taxonomic_order_biblio_id
);


CREATE INDEX idx_taxonomic_order_biblio_taxonomic_order_system_id ON public.tbl_taxonomic_order_biblio USING btree (
    taxonomic_order_system_id
);


CREATE INDEX idx_taxonomic_order_systems_taxonomic_system_id ON public.tbl_taxonomic_order_systems USING btree (
    taxonomic_order_system_id
);


CREATE INDEX idx_taxonomic_order_taxon_id ON public.tbl_taxonomic_order USING btree (
    taxon_id
);


CREATE INDEX idx_taxonomic_order_taxonomic_code ON public.tbl_taxonomic_order USING btree (
    taxonomic_code
);


CREATE INDEX idx_taxonomic_order_taxonomic_order_id ON public.tbl_taxonomic_order USING btree (
    taxonomic_order_id
);


CREATE INDEX idx_taxonomic_order_taxonomic_system_id ON public.tbl_taxonomic_order USING btree (
    taxonomic_order_system_id
);


CREATE INDEX idx_tbl_physical_sample_features_feature_id ON public.tbl_physical_sample_features USING btree (
    feature_id
);


CREATE INDEX tbl_biblio_norm_trgm ON public.tbl_biblio USING gin (
    authority.immutable_unaccent(lower(full_reference)) public.gin_trgm_ops
);


CREATE INDEX tbl_data_type_groups_norm_trgm ON public.tbl_data_type_groups USING gin (
    authority.immutable_unaccent(
        lower((data_type_group_name)::text)
    ) public.gin_trgm_ops
);


CREATE INDEX tbl_data_types_norm_trgm ON public.tbl_data_types USING gin (
    authority.immutable_unaccent(
        lower((data_type_name)::text)
    ) public.gin_trgm_ops
);


CREATE INDEX tbl_dating_uncertainty_norm_trgm ON public.tbl_dating_uncertainty USING gin (
    authority.immutable_unaccent(lower((uncertainty)::text)) public.gin_trgm_ops
);


CREATE INDEX tbl_ecocode_groups_idx_name ON public.tbl_ecocode_groups USING btree (
    name
);


CREATE INDEX tbl_feature_types_norm_trgm ON public.tbl_feature_types USING gin (
    authority.immutable_unaccent(
        lower((feature_type_name)::text)
    ) public.gin_trgm_ops
);


CREATE INDEX tbl_features_norm_trgm ON public.tbl_features USING gin (
    authority.immutable_unaccent(
        lower((feature_name)::text)
    ) public.gin_trgm_ops
);


CREATE INDEX tbl_location_types_norm_trgm ON public.tbl_location_types USING gin (
    authority.immutable_unaccent(
        lower((location_type)::text)
    ) public.gin_trgm_ops
);


CREATE INDEX tbl_locations_norm_trgm ON public.tbl_locations USING gin (
    authority.immutable_unaccent(
        lower((location_name)::text)
    ) public.gin_trgm_ops
);


CREATE INDEX tbl_method_groups_norm_trgm ON public.tbl_method_groups USING gin (
    authority.immutable_unaccent(lower((group_name)::text)) public.gin_trgm_ops
);


CREATE INDEX tbl_methods_norm_trgm ON public.tbl_methods USING gin (
    authority.immutable_unaccent(lower((method_name)::text)) public.gin_trgm_ops
);


CREATE INDEX tbl_modification_types_norm_trgm ON public.tbl_modification_types USING gin (
    authority.immutable_unaccent(
        lower((modification_type_name)::text)
    ) public.gin_trgm_ops
);


CREATE INDEX tbl_record_types_norm_trgm ON public.tbl_record_types USING gin (
    authority.immutable_unaccent(
        lower((record_type_name)::text)
    ) public.gin_trgm_ops
);


CREATE INDEX tbl_relative_age_types_norm_trgm ON public.tbl_relative_age_types USING gin (
    authority.immutable_unaccent(lower((age_type)::text)) public.gin_trgm_ops
);


CREATE INDEX tbl_relative_ages_norm_trgm ON public.tbl_relative_ages USING gin (
    authority.immutable_unaccent(
        lower((relative_age_name)::text)
    ) public.gin_trgm_ops
);


CREATE INDEX tbl_sample_description_types_norm_trgm ON public.tbl_sample_description_types USING gin (
    authority.immutable_unaccent(lower((type_name)::text)) public.gin_trgm_ops
);


CREATE INDEX tbl_sample_group_description_types_norm_trgm ON public.tbl_sample_group_description_types USING gin (
    authority.immutable_unaccent(lower((type_name)::text)) public.gin_trgm_ops
);


CREATE INDEX tbl_sample_group_sampling_contexts_norm_trgm ON public.tbl_sample_group_sampling_contexts USING gin (
    authority.immutable_unaccent(
        lower((sampling_context)::text)
    ) public.gin_trgm_ops
);


CREATE INDEX tbl_sample_location_types_norm_trgm ON public.tbl_sample_location_types USING gin (
    authority.immutable_unaccent(
        lower((location_type)::text)
    ) public.gin_trgm_ops
);


CREATE INDEX tbl_sample_types_norm_trgm ON public.tbl_sample_types USING gin (
    authority.immutable_unaccent(lower((type_name)::text)) public.gin_trgm_ops
);


CREATE INDEX tbl_taxa_synonyms_norm_trgm ON public.tbl_taxa_synonyms USING gin (
    authority.immutable_unaccent(lower((synonym)::text)) public.gin_trgm_ops
);


CREATE INDEX tbl_taxa_tree_authors_norm_trgm ON public.tbl_taxa_tree_authors USING gin (
    authority.immutable_unaccent(lower((author_name)::text)) public.gin_trgm_ops
);


CREATE INDEX tbl_taxa_tree_families_norm_trgm ON public.tbl_taxa_tree_families USING gin (
    authority.immutable_unaccent(lower((family_name)::text)) public.gin_trgm_ops
);


CREATE INDEX tbl_taxa_tree_genera_norm_trgm ON public.tbl_taxa_tree_genera USING gin (
    authority.immutable_unaccent(lower((genus_name)::text)) public.gin_trgm_ops
);


CREATE INDEX tbl_taxa_tree_master_norm_trgm ON public.tbl_taxa_tree_master USING gin (
    authority.immutable_unaccent(lower((species)::text)) public.gin_trgm_ops
);


CREATE INDEX tbl_taxa_tree_orders_norm_trgm ON public.tbl_taxa_tree_orders USING gin (
    authority.immutable_unaccent(lower((order_name)::text)) public.gin_trgm_ops
);


CREATE INDEX tbl_taxonomic_order_code_trgm ON public.tbl_taxonomic_order USING gin (
    ((taxonomic_code)::text) public.gin_trgm_ops
);


CREATE INDEX tbl_taxonomic_order_systems_norm_trgm ON public.tbl_taxonomic_order_systems USING gin (
    authority.immutable_unaccent(lower((system_name)::text)) public.gin_trgm_ops
);


CREATE INDEX tbl_taxonomy_notes_norm_trgm ON public.tbl_taxonomy_notes USING gin (
    authority.immutable_unaccent(lower(taxonomy_notes)) public.gin_trgm_ops
);

