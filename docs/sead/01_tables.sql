--
-- PostgreSQL database dump
--

create table tbl_abundances (
    abundance_id bigint not null,
    taxon_id integer not null,
    analysis_entity_id bigint not null,
    abundance_element_id integer,
    abundance integer default 0 not null
);


create table tbl_abundance_elements (
    abundance_element_id integer not null,
    record_type_id integer,
    element_name character varying(100) not null,
    element_description text
);


create table tbl_abundance_ident_levels (
    abundance_ident_level_id integer not null,
    abundance_id bigint not null,
    identification_level_id integer not null
);


create table tbl_abundance_modifications (
    abundance_modification_id integer not null,
    abundance_id integer not null,
    modification_type_id integer not null
);


create table tbl_activity_types (
    activity_type_id integer not null,
    activity_type character varying(50) default null::character varying,
    description text
);


create table tbl_age_types (
    age_type_id integer not null,
    age_type character varying(150) not null,
    description text
);


create table tbl_aggregate_datasets (
    aggregate_dataset_id integer not null,
    aggregate_order_type_id integer not null,
    biblio_id integer,
    aggregate_dataset_name character varying(255),
    description text,
    aggregate_dataset_uuid uuid default public.uuid_generate_v4() not null
);

create table tbl_aggregate_order_types (
    aggregate_order_type_id integer not null,
    aggregate_order_type character varying(60) not null,
    description text
);


create table tbl_aggregate_samples (
    aggregate_sample_id integer not null,
    aggregate_dataset_id integer not null,
    analysis_entity_id bigint not null,
    aggregate_sample_name character varying(50)
);


create table tbl_aggregate_sample_ages (
    aggregate_sample_age_id integer not null,
    aggregate_dataset_id integer not null,
    analysis_entity_age_id integer not null
);

create table tbl_alt_ref_types (
    alt_ref_type_id integer not null,
    alt_ref_type character varying(50) not null,
    description text
);


create table tbl_analysis_boolean_values (
    analysis_boolean_value_id integer not null,
    analysis_value_id bigint not null,
    qualifier text,
    value boolean
);


create table tbl_analysis_categorical_values (
    analysis_categorical_value_id bigint not null,
    analysis_value_id bigint not null,
    value_type_item_id integer not null,
    value numeric(20, 10) default null::numeric,
    is_variant boolean
);


create table tbl_analysis_dating_ranges (
    analysis_dating_range_id bigint not null,
    analysis_value_id bigint not null,
    low_value integer,
    high_value integer,
    low_is_uncertain boolean,
    high_is_uncertain boolean,
    low_qualifier text,
    high_qualifier text,
    age_type_id integer default 1 not null,
    season_id integer,
    dating_uncertainty_id integer,
    is_variant boolean
);


create table tbl_analysis_entities (
    analysis_entity_id bigint not null,
    physical_sample_id integer,
    dataset_id integer
);


create table tbl_analysis_entity_ages (
    analysis_entity_age_id integer not null,
    age numeric(20, 5),
    age_older numeric(20, 5),
    age_younger numeric(20, 5),
    analysis_entity_id bigint,
    chronology_id integer,
    dating_specifier text,
    age_range int4range generated always as (
        case
            when ((age_younger is null) and (age_older is null)) then null::int4range
            else int4range(coalesce(
                (age_younger)::integer, (age_older)::integer
            ),
            (coalesce((age_older)::integer, (age_younger)::integer) + 1))
        end
    ) stored
);


create table tbl_analysis_entity_dimensions (
    analysis_entity_dimension_id integer not null,
    analysis_entity_id bigint not null,
    dimension_id integer not null,
    dimension_value numeric not null
);


create table tbl_analysis_entity_prep_methods (
    analysis_entity_prep_method_id integer not null,
    analysis_entity_id bigint not null,
    method_id integer not null
);


create table tbl_analysis_identifiers (
    analysis_identifier_id bigint not null,
    analysis_value_id bigint not null,
    value text not null
);


create table tbl_analysis_integer_ranges (
    analysis_integer_range_id bigint not null,
    analysis_value_id bigint not null,
    low_value integer,
    high_value integer,
    low_is_uncertain boolean,
    high_is_uncertain boolean,
    low_qualifier text,
    high_qualifier text,
    is_variant boolean
);


create table tbl_analysis_integer_values (
    analysis_integer_value_id bigint not null,
    analysis_value_id bigint not null,
    qualifier text,
    value integer,
    is_variant boolean
);


create table tbl_analysis_notes (
    analysis_note_id bigint not null,
    analysis_value_id bigint not null,
    value text not null
);


create table tbl_analysis_numerical_ranges (
    analysis_numerical_range_id bigint not null,
    analysis_value_id bigint not null,
    value numrange not null,
    low_is_uncertain boolean,
    high_is_uncertain boolean,
    low_qualifier text,
    high_qualifier text,
    is_variant boolean
);


create table tbl_analysis_numerical_values (
    analysis_numerical_value_id bigint not null,
    analysis_value_id bigint not null,
    qualifier text,
    value numeric(20, 10),
    is_variant boolean
);


create table tbl_analysis_taxon_counts (
    analysis_taxon_count_id integer not null,
    analysis_value_id bigint not null,
    taxon_id integer not null,
    value numeric(20, 10) not null
);


create table tbl_analysis_values (
    analysis_value_id bigint not null,
    value_class_id integer not null,
    analysis_entity_id bigint not null,
    analysis_value text,
    boolean_value boolean,
    is_boolean boolean,
    is_uncertain boolean,
    is_undefined boolean,
    is_not_analyzed boolean,
    is_indeterminable boolean,
    is_anomaly boolean
);


create table tbl_analysis_value_dimensions (
    analysis_value_dimension_id integer not null,
    analysis_value_id bigint not null,
    dimension_id integer not null,
    value numeric(20, 10) not null
);


create table tbl_biblio (
    biblio_id integer not null,
    bugs_reference character varying(60) default null::character varying,
    doi character varying(255) default null::character varying,
    isbn character varying(128) default null::character varying,
    notes text,
    title character varying,
    year character varying(255) default null::character varying,
    authors character varying,
    full_reference text default ''::text not null,
    url character varying,
    biblio_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_ceramics (
    ceramics_id integer not null,
    analysis_entity_id integer not null,
    measurement_value character varying not null,
    ceramics_lookup_id integer not null
);


create table tbl_ceramics_lookup (
    ceramics_lookup_id integer not null,
    method_id integer not null,
    description text,
    name character varying not null
);


create table tbl_ceramics_measurements (
    ceramics_measurement_id integer not null,
    method_id integer
);


create table tbl_chronologies (
    chronology_id integer not null,
    age_model text,
    relative_age_type_id integer,
    chronology_name text,
    contact_id integer,
    date_prepared timestamp(0) without time zone,
    notes text
);


create table tbl_colours (
    colour_id integer not null,
    colour_name character varying(30) not null,
    method_id integer not null,
    rgb integer
);


create table tbl_contacts (
    contact_id integer not null,
    address_1 character varying(255),
    address_2 character varying(255),
    location_id integer,
    email character varying,
    first_name character varying(50),
    last_name character varying(100),
    phone_number character varying(50),
    url text
);


create table tbl_contact_types (
    contact_type_id integer not null,
    contact_type_name character varying(150) not null,
    description text
);


create table tbl_coordinate_method_dimensions (
    coordinate_method_dimension_id integer not null,
    dimension_id integer not null,
    method_id integer not null,
    limit_upper numeric(18, 10),
    limit_lower numeric(18, 10)
);


create table tbl_data_types (
    data_type_id integer not null,
    data_type_group_id integer not null,
    data_type_name character varying(25) default null::character varying,
    definition text
);


create table tbl_data_type_groups (
    data_type_group_id integer not null,
    data_type_group_name character varying(25),
    description text
);


create table tbl_datasets (
    dataset_id integer not null,
    master_set_id integer,
    data_type_id integer not null,
    method_id integer,
    biblio_id integer,
    updated_dataset_id integer,
    project_id integer,
    dataset_name character varying(50) not null,
    dataset_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_dataset_contacts (
    dataset_contact_id integer not null,
    contact_id integer not null,
    contact_type_id integer not null,
    dataset_id integer not null
);


create table tbl_dataset_masters (
    master_set_id integer not null,
    contact_id integer,
    biblio_id integer,
    master_name character varying(100),
    master_notes text,
    url text,
    master_set_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_dataset_methods (
    dataset_method_id integer not null,
    dataset_id integer not null,
    method_id integer not null
);

create table tbl_dataset_submissions (
    dataset_submission_id integer not null,
    dataset_id integer not null,
    submission_type_id integer not null,
    contact_id integer not null,
    date_submitted text,
    notes text
);


create table tbl_dataset_submission_types (
    submission_type_id integer not null,
    submission_type character varying(60) not null,
    description text
);


create table tbl_dating_labs (
    dating_lab_id integer not null,
    contact_id integer,
    international_lab_id character varying(10) not null,
    lab_name character varying(100) default null::character varying,
    country_id integer
);


create table tbl_dating_material (
    dating_material_id integer not null,
    geochron_id integer not null,
    taxon_id integer,
    material_dated character varying,
    description text,
    abundance_element_id integer
);


create table tbl_dating_uncertainty (
    dating_uncertainty_id integer not null,
    description text,
    uncertainty character varying
);


create table tbl_dendro (
    dendro_id integer not null,
    analysis_entity_id integer not null,
    measurement_value character varying not null,
    dendro_lookup_id integer not null
);

create table tbl_dendro_dates (
    dendro_date_id integer not null,
    season_id integer,
    dating_uncertainty_id integer,
    dendro_lookup_id integer not null,
    age_type_id integer not null,
    analysis_entity_id integer not null,
    age_older integer,
    age_younger integer,
    age_range int4range generated always as (
        case
            when ((age_younger is null) and (age_older is null)) then null::int4range
            else int4range(coalesce(age_older, age_younger), (coalesce(age_younger, age_older) + 1))
        end
    ) stored
);


create table tbl_dendro_date_notes (
    dendro_date_note_id integer not null,
    dendro_date_id integer not null,
    note text
);

create table tbl_dendro_lookup (
    dendro_lookup_id integer not null,
    method_id integer,
    name character varying not null,
    description text
);


create table tbl_dimensions (
    dimension_id integer not null,
    dimension_abbrev character varying(40),
    dimension_description text,
    dimension_name character varying(50) not null,
    unit_id integer,
    method_group_id integer
);


create table tbl_ecocodes (
    ecocode_id integer not null,
    ecocode_definition_id integer default 0,
    taxon_id integer default 0
);


create table tbl_ecocode_definitions (
    ecocode_definition_id integer not null,
    abbreviation character varying(10) default null::character varying,
    definition text,
    ecocode_group_id integer default 0,
    name character varying(150) default null::character varying,
    notes text,
    sort_order smallint default 0
);


create table tbl_ecocode_groups (
    ecocode_group_id integer not null,
    definition text default null::character varying,
    ecocode_system_id integer default 0,
    name character varying(200) default null::character varying,
    abbreviation character varying(255)
);


create table tbl_ecocode_systems (
    ecocode_system_id integer not null,
    biblio_id integer,
    definition text default null::character varying,
    name character varying(50) default null::character varying,
    notes text,
    ecocode_system_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_features (
    feature_id integer not null,
    feature_type_id integer not null,
    feature_name character varying,
    feature_description text
);


create table tbl_feature_types (
    feature_type_id integer not null,
    feature_type_name character varying(128),
    feature_type_description text
);


create table tbl_geochron_refs (
    geochron_ref_id integer not null,
    geochron_id integer not null,
    biblio_id integer not null
);


create table tbl_geochronology (
    geochron_id integer not null,
    analysis_entity_id bigint not null,
    dating_lab_id integer,
    lab_number character varying(40),
    age numeric(20, 5),
    error_older numeric(20, 5),
    error_younger numeric(20, 5),
    delta_13c numeric(10, 5),
    notes text,
    dating_uncertainty_id integer,
    geochron_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_horizons (
    horizon_id integer not null,
    description text,
    horizon_name character varying(15) not null,
    method_id integer not null
);


create table tbl_identification_levels (
    identification_level_id integer not null,
    identification_level_abbrev character varying(50) default null::character varying,
    identification_level_name character varying(50) default null::character varying,
    notes text
);


create table tbl_image_types (
    image_type_id integer not null,
    description text,
    image_type character varying(40) not null
);


create table tbl_imported_taxa_replacements (
    imported_taxa_replacement_id integer not null,
    imported_name_replaced character varying(100) not null,
    taxon_id integer not null
);

create table tbl_isotopes (
    isotope_id integer not null,
    analysis_entity_id integer not null,
    isotope_measurement_id integer not null,
    isotope_standard_id integer,
    measurement_value text,
    unit_id integer not null,
    isotope_value_specifier_id integer not null
);

create table tbl_isotope_measurements (
    isotope_measurement_id integer not null,
    isotope_standard_id integer,
    method_id integer,
    isotope_type_id integer
);

create table tbl_isotope_standards (
    isotope_standard_id integer not null,
    isotope_ration character varying,
    international_scale character varying,
    accepted_ratio_xe6 character varying,
    error_of_ratio character varying,
    reference character varying
);


create table tbl_isotope_types (
    isotope_type_id integer not null,
    designation character varying,
    abbreviation character varying,
    atomic_number numeric,
    description text,
    alternative_designation character varying
);


create table tbl_isotope_value_specifiers (
    isotope_value_specifier_id integer not null,
    name character varying not null,
    description text not null
);

create table tbl_languages (
    language_id integer not null,
    language_name_english character varying(100) default null::character varying,
    language_name_native character varying(100) default null::character varying
);


create table tbl_lithology (
    lithology_id integer not null,
    depth_bottom numeric(20, 5),
    depth_top numeric(20, 5) not null,
    description text not null,
    lower_boundary character varying(255),
    sample_group_id integer not null
);


create table tbl_locations (
    location_id integer not null,
    location_name character varying(255) not null,
    location_type_id integer not null,
    default_lat_dd numeric(18, 10),
    default_long_dd numeric(18, 10)
);


create table tbl_location_types (
    location_type_id integer not null,
    description text,
    location_type character varying(40)
);


create table tbl_mcr_names (
    taxon_id integer not null,
    comparison_notes character varying(255) default null::character varying,
    mcr_name_trim character varying(80) default null::character varying,
    mcr_number smallint default 0,
    mcr_species_name character varying(200) default null::character varying
);


create table tbl_mcr_summary_data (
    mcr_summary_data_id integer not null,
    cog_mid_tmax smallint default 0,
    cog_mid_trange smallint default 0,
    taxon_id integer not null,
    tmax_hi smallint default 0,
    tmax_lo smallint default 0,
    tmin_hi smallint default 0,
    tmin_lo smallint default 0,
    trange_hi smallint default 0,
    trange_lo smallint default 0
);


create table tbl_mcrdata_birmbeetledat (
    mcrdata_birmbeetledat_id integer not null,
    mcr_data text,
    mcr_row smallint not null,
    taxon_id integer not null
);


create table tbl_measured_values (
    measured_value_id bigint not null,
    analysis_entity_id bigint not null,
    measured_value numeric(20, 10) not null
);


create table tbl_measured_value_dimensions (
    measured_value_dimension_id integer not null,
    dimension_id integer not null,
    dimension_value numeric(18, 10) not null,
    measured_value_id bigint not null
);


create table tbl_methods (
    method_id integer not null,
    biblio_id integer,
    description text not null,
    method_abbrev_or_alt_name character varying(50),
    method_group_id integer not null,
    method_name character varying(50) not null,
    record_type_id integer,
    unit_id integer,
    method_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_method_groups (
    method_group_id integer not null,
    description text not null,
    group_name character varying(100) not null
);


create table tbl_modification_types (
    modification_type_id integer not null,
    modification_type_name character varying(128),
    modification_type_description text
);


create table tbl_physical_samples (
    physical_sample_id integer not null,
    sample_group_id integer default 0 not null,
    alt_ref_type_id integer,
    sample_type_id integer not null,
    sample_name character varying(50) not null,
    date_sampled character varying
);


create table tbl_physical_sample_features (
    physical_sample_feature_id integer not null,
    feature_id integer not null,
    physical_sample_id integer not null
);


create table tbl_projects (
    project_id integer not null,
    project_type_id integer,
    project_stage_id integer,
    project_name character varying(150),
    project_abbrev_name character varying(25),
    description text
);


create table tbl_project_stages (
    project_stage_id integer not null,
    stage_name character varying,
    description text
);


create table tbl_project_types (
    project_type_id integer not null,
    project_type_name character varying,
    description text
);


create table tbl_rdb (
    rdb_id integer not null,
    location_id integer not null,
    rdb_code_id integer,
    taxon_id integer not null
);


create table tbl_rdb_codes (
    rdb_code_id integer not null,
    rdb_category character varying(4) default null::character varying,
    rdb_definition character varying(200) default null::character varying,
    rdb_system_id integer default 0
);


create table tbl_rdb_systems (
    rdb_system_id integer not null,
    biblio_id integer not null,
    location_id integer not null,
    rdb_first_published smallint,
    rdb_system character varying(10) default null::character varying,
    rdb_system_date integer,
    rdb_version character varying(10) default null::character varying,
    rdb_system_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_record_types (
    record_type_id integer not null,
    record_type_name character varying(50) default null::character varying,
    record_type_description text
);


create table tbl_relative_ages (
    relative_age_id integer not null,
    relative_age_type_id integer,
    relative_age_name character varying(50),
    description text,
    c14_age_older numeric(20, 5),
    c14_age_younger numeric(20, 5),
    cal_age_older numeric(20, 5),
    cal_age_younger numeric(20, 5),
    notes text,
    location_id integer,
    abbreviation character varying,
    relative_age_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_relative_age_refs (
    relative_age_ref_id integer not null,
    biblio_id integer not null,
    relative_age_id integer not null
);


create table tbl_relative_age_types (
    relative_age_type_id integer not null,
    age_type character varying,
    description text
);


create table tbl_relative_dates (
    relative_date_id integer not null,
    relative_age_id integer,
    method_id integer,
    notes text,
    dating_uncertainty_id integer,
    analysis_entity_id integer not null
);


create table tbl_sample_alt_refs (
    sample_alt_ref_id integer not null,
    alt_ref character varying(80) not null,
    alt_ref_type_id integer not null,
    physical_sample_id integer not null
);


create table tbl_sample_colours (
    sample_colour_id integer not null,
    colour_id integer not null,
    physical_sample_id integer not null
);


create table tbl_sample_coordinates (
    sample_coordinate_id integer not null,
    physical_sample_id integer not null,
    coordinate_method_dimension_id integer not null,
    measurement numeric(20, 10) not null,
    accuracy numeric(20, 10)
);


create table tbl_sample_descriptions (
    sample_description_id integer not null,
    sample_description_type_id integer not null,
    physical_sample_id integer not null,
    description character varying
);


create table tbl_sample_description_sample_group_contexts (
    sample_description_sample_group_context_id integer not null,
    sampling_context_id integer,
    sample_description_type_id integer
);


create table tbl_sample_description_types (
    sample_description_type_id integer not null,
    type_name character varying(255),
    type_description text
);


create table tbl_sample_dimensions (
    sample_dimension_id integer not null,
    physical_sample_id integer not null,
    dimension_id integer not null,
    method_id integer not null,
    dimension_value numeric(20, 10) not null,
    qualifier_id integer
);


create table tbl_sample_groups (
    sample_group_id integer not null,
    site_id integer default 0,
    sampling_context_id integer,
    method_id integer not null,
    sample_group_name character varying(100) default null::character varying,
    sample_group_description text,
    sample_group_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_sample_group_coordinates (
    sample_group_position_id integer not null,
    coordinate_method_dimension_id integer not null,
    sample_group_position numeric(20, 10),
    position_accuracy character varying(128),
    sample_group_id integer not null
);


create table tbl_sample_group_descriptions (
    sample_group_description_id integer not null,
    group_description character varying,
    sample_group_description_type_id integer not null,
    sample_group_id integer
);


create table tbl_sample_group_description_types (
    sample_group_description_type_id integer not null,
    type_name character varying(255),
    type_description character varying
);


create table tbl_sample_group_description_type_sampling_contexts (
    sample_group_description_type_sampling_context_id integer not null,
    sampling_context_id integer not null,
    sample_group_description_type_id integer not null
);


create table tbl_sample_group_dimensions (
    sample_group_dimension_id integer not null,
    dimension_id integer not null,
    dimension_value numeric(20, 5) not null,
    sample_group_id integer not null,
    qualifier_id integer
);


create table tbl_sample_group_images (
    sample_group_image_id integer not null,
    description text,
    image_location text not null,
    image_name character varying(80),
    image_type_id integer not null,
    sample_group_id integer not null
);


create table tbl_sample_group_notes (
    sample_group_note_id integer not null,
    sample_group_id integer not null,
    note character varying
);


create table tbl_sample_group_references (
    sample_group_reference_id integer not null,
    biblio_id integer not null,
    sample_group_id integer default 0
);


create table tbl_sample_group_sampling_contexts (
    sampling_context_id integer not null,
    sampling_context character varying(80) not null,
    description text,
    sort_order smallint default 0 not null
);


create table tbl_sample_horizons (
    sample_horizon_id integer not null,
    horizon_id integer not null,
    physical_sample_id integer not null
);


create table tbl_sample_images (
    sample_image_id integer not null,
    description text,
    image_location text not null,
    image_name character varying(80),
    image_type_id integer not null,
    physical_sample_id integer not null
);


create table tbl_sample_locations (
    sample_location_id integer not null,
    sample_location_type_id integer not null,
    physical_sample_id integer not null,
    location character varying(255)
);


create table tbl_sample_location_types (
    sample_location_type_id integer not null,
    location_type character varying(255),
    location_type_description text
);


create table tbl_sample_location_type_sampling_contexts (
    sample_location_type_sampling_context_id integer not null,
    sampling_context_id integer not null,
    sample_location_type_id integer not null
);


create table tbl_sample_notes (
    sample_note_id integer not null,
    physical_sample_id integer not null,
    note_type character varying,
    note text not null
);


create table tbl_sample_types (
    sample_type_id integer not null,
    type_name character varying(40) not null,
    description text
);


create table tbl_seasons (
    season_id integer not null,
    season_name character varying(20) default null::character varying,
    season_type character varying(30) default null::character varying,
    season_type_id integer,
    sort_order smallint default 0
);


create table tbl_season_types (
    season_type_id integer not null,
    description text,
    season_type character varying(30)
);


create table tbl_sites (
    site_id integer not null,
    altitude numeric(18, 10),
    latitude_dd numeric(18, 10),
    longitude_dd numeric(18, 10),
    national_site_identifier character varying(255),
    site_description text default null::character varying,
    site_name character varying(60) default null::character varying,
    site_preservation_status_id integer,
    site_location_accuracy character varying,
    site_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_site_images (
    site_image_id integer not null,
    contact_id integer,
    credit character varying(100),
    date_taken date,
    description text,
    image_location text not null,
    image_name character varying(80),
    image_type_id integer not null,
    site_id integer not null
);


create table tbl_site_locations (
    site_location_id integer not null,
    location_id integer not null,
    site_id integer not null
);


create table tbl_site_natgridrefs (
    site_natgridref_id integer not null,
    site_id integer not null,
    method_id integer not null,
    natgridref character varying not null
);


create table tbl_site_other_records (
    site_other_records_id integer not null,
    site_id integer,
    biblio_id integer,
    record_type_id integer,
    description text,
    site_other_records_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_site_preservation_status (
    site_preservation_status_id integer not null,
    site_id integer,
    preservation_status_or_threat character varying,
    description text,
    assessment_type character varying,
    assessment_author_contact_id integer,
    "Evaluation_date" date
);


create table tbl_site_references (
    site_reference_id integer not null,
    site_id integer default 0,
    biblio_id integer not null
);


create table tbl_species_associations (
    species_association_id integer not null,
    associated_taxon_id integer not null,
    biblio_id integer,
    taxon_id integer not null,
    association_type_id integer,
    referencing_type text,
    species_association_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_species_association_types (
    association_type_id integer not null,
    association_type_name character varying(255),
    association_description text
);


create table tbl_taxa_common_names (
    taxon_common_name_id integer not null,
    common_name character varying(255) default null::character varying,
    language_id integer default 0,
    taxon_id integer default 0
);


create table tbl_taxa_images (
    taxa_images_id integer not null,
    image_name character varying,
    description text,
    image_location text,
    image_type_id integer,
    taxon_id integer not null
);


create table tbl_taxa_measured_attributes (
    measured_attribute_id integer not null,
    attribute_measure character varying(255) default null::character varying,
    attribute_type character varying(255) default null::character varying,
    attribute_units character varying(10) default null::character varying,
    data numeric(18, 10) default 0,
    taxon_id integer not null
);


create table tbl_taxa_reference_specimens (
    taxa_reference_specimen_id integer not null,
    taxon_id integer not null,
    contact_id integer not null,
    notes text
);


create table tbl_taxa_seasonality (
    seasonality_id integer not null,
    activity_type_id integer not null,
    season_id integer default 0,
    taxon_id integer not null,
    location_id integer not null
);


create table tbl_taxa_synonyms (
    synonym_id integer not null,
    biblio_id integer not null,
    family_id integer,
    genus_id integer,
    notes text default null::character varying,
    taxon_id integer,
    author_id integer,
    synonym character varying(255),
    reference_type character varying,
    synonym_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_taxa_tree_authors (
    author_id integer not null,
    author_name character varying(100) default null::character varying
);


create table tbl_taxa_tree_families (
    family_id integer not null,
    family_name character varying(100) default null::character varying,
    order_id integer not null
);


create table tbl_taxa_tree_genera (
    genus_id integer not null,
    family_id integer,
    genus_name character varying(100) default null::character varying
);


create table tbl_taxa_tree_master (
    taxon_id integer not null,
    author_id integer,
    genus_id integer,
    species character varying(255) default null::character varying
);


create table tbl_taxa_tree_orders (
    order_id integer not null,
    order_name character varying(50) default null::character varying,
    record_type_id integer,
    sort_order integer
);


create table tbl_taxonomic_order (
    taxonomic_order_id integer not null,
    taxon_id integer default 0,
    taxonomic_code numeric(18, 10) default 0,
    taxonomic_order_system_id integer default 0
);


create table tbl_taxonomic_order_biblio (
    taxonomic_order_biblio_id integer not null,
    biblio_id integer default 0,
    taxonomic_order_system_id integer default 0
);


create table tbl_taxonomic_order_systems (
    taxonomic_order_system_id integer not null,
    system_description text,
    system_name character varying(50) default null::character varying,
    taxonomic_order_system_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_taxonomy_notes (
    taxonomy_notes_id integer not null,
    biblio_id integer not null,
    taxon_id integer not null,
    taxonomy_notes text,
    taxonomy_notes_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_temperatures (
    record_id integer not null,
    years_bp integer not null,
    d180_gisp2 numeric
);


create table tbl_tephras (
    tephra_id integer not null,
    c14_age numeric(20, 5),
    c14_age_older numeric(20, 5),
    c14_age_younger numeric(20, 5),
    cal_age numeric(20, 5),
    cal_age_older numeric(20, 5),
    cal_age_younger numeric(20, 5),
    notes text,
    tephra_name character varying(80),
    tephra_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_tephra_dates (
    tephra_date_id integer not null,
    analysis_entity_id bigint not null,
    notes text,
    tephra_id integer not null,
    dating_uncertainty_id integer
);


create table tbl_tephra_refs (
    tephra_ref_id integer not null,
    biblio_id integer not null,
    tephra_id integer not null
);


create table tbl_text_biology (
    biology_id integer not null,
    biblio_id integer not null,
    biology_text text,
    taxon_id integer not null,
    biology_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_text_distribution (
    distribution_id integer not null,
    biblio_id integer not null,
    distribution_text text,
    taxon_id integer not null,
    distribution_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_text_identification_keys (
    key_id integer not null,
    biblio_id integer not null,
    key_text text,
    taxon_id integer not null,
    key_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_units (
    unit_id integer not null,
    description text,
    unit_abbrev character varying(15),
    unit_name character varying(50) not null
);


create table tbl_updates_log (
    updates_log_id integer not null,
    table_name character varying(150) not null,
    last_updated date not null
);

create table tbl_value_classes (
    value_class_id integer not null,
    value_type_id integer not null,
    method_id integer not null,
    parent_id integer,
    name character varying(80) not null,
    description text not null,
    value_class_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_value_qualifiers (
    qualifier_id integer not null,
    symbol text not null,
    description text not null,
    qualifier_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_value_qualifier_symbols (
    qualifier_symbol_id integer not null,
    symbol text not null,
    cardinal_qualifier_id integer not null,
    qualifier_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_value_types (
    value_type_id integer not null,
    unit_id integer,
    data_type_id integer,
    name text not null,
    base_type text not null,
    precision integer,
    description text not null,
    value_type_uuid uuid default public.uuid_generate_v4() not null
);


create table tbl_value_type_items (
    value_type_item_id integer not null,
    value_type_id integer not null,
    name character varying(80) default null::character varying,
    description text
);


create table tbl_years_types (
    years_type_id integer not null,
    name character varying not null,
    description text
);


create table tbl_abundance_properties (
    abundance_property_id integer not null,
    abundance_id integer not null,
    property_type_id integer not null,
    property_value text not null
);

create table tbl_property_types (
    uuid uuid default gen_random_uuid() not null,
    property_type_id integer not null,
    property_type_name text not null,
    description text not null,
    value_type_id integer,
    value_class_id integer
);

create table tbl_site_properties (
    site_property_id integer not null,
    site_id integer not null,
    property_type_id integer not null,
    property_value text not null
);

create table tbl_site_site_types (
    site_site_type_id integer not null,
    site_id integer not null,
    site_type_id integer not null,
    is_primary_type boolean default false not null,
    confidence_code smallint,
    notes text
);

create table tbl_site_type_groups (
    site_type_group_id integer not null,
    site_type_group_abbrev character varying(40) not null,
    site_type_group character varying(255) not null,
    description text default ''::text not null,
    origin_code character varying(40),
    origin_description text default ''::text not null
);

create table tbl_site_types (
    site_type_id integer not null,
    site_type_group_id integer not null,
    site_type_abbrev character varying(40) not null,
    site_type character varying(256) not null,
    description text default ''::text not null
);
