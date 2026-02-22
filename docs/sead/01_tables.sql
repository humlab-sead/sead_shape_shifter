--
-- PostgreSQL database dump
--

CREATE TABLE public.tbl_abundances (
    abundance_id bigint NOT NULL,
    taxon_id integer NOT NULL,
    analysis_entity_id bigint NOT NULL,
    abundance_element_id integer,
    abundance integer DEFAULT 0 NOT NULL
);


CREATE TABLE public.tbl_abundance_elements (
    abundance_element_id integer NOT NUL,
    record_type_id integer,
    element_name character varying(100) NOT NULL,
    element_description text
);


CREATE TABLE public.tbl_abundance_ident_levels (
    abundance_ident_level_id integer NOT NULL,
    abundance_id bigint NOT NULL,
    identification_level_id integer NOT NULL
);


CREATE TABLE public.tbl_abundance_modifications (
    abundance_modification_id integer NOT NULL,
    abundance_id integer NOT NULL,
    modification_type_id integer NOT NULL
);


CREATE TABLE public.tbl_activity_types (
    activity_type_id integer NOT NULL,
    activity_type character varying(50) DEFAULT NULL::character varying,
    description text
);


CREATE TABLE public.tbl_age_types (
    age_type_id integer NOT NULL,
    age_type character varying(150) NOT NULL,
    description text
);


CREATE TABLE public.tbl_aggregate_datasets (
    aggregate_dataset_id integer NOT NULL,
    aggregate_order_type_id integer NOT NULL,
    biblio_id integer,
    aggregate_dataset_name character varying(255),
    description text,
    aggregate_dataset_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);

CREATE TABLE public.tbl_aggregate_order_types (
    aggregate_order_type_id integer NOT NULL,
    aggregate_order_type character varying(60) NOT NULL,
    description text
);


CREATE TABLE public.tbl_aggregate_samples (
    aggregate_sample_id integer NOT NULL,
    aggregate_dataset_id integer NOT NULL,
    analysis_entity_id bigint NOT NULL,
    aggregate_sample_name character varying(50)
);


CREATE TABLE public.tbl_aggregate_sample_ages (
    aggregate_sample_age_id integer NOT NULL,
    aggregate_dataset_id integer NOT NULL,
    analysis_entity_age_id integer NOT NULL
);

CREATE TABLE public.tbl_alt_ref_types (
    alt_ref_type_id integer NOT NULL,
    alt_ref_type character varying(50) NOT NULL,
    description text
);


CREATE TABLE public.tbl_analysis_boolean_values (
    analysis_boolean_value_id integer NOT NULL,
    analysis_value_id bigint NOT NULL,
    qualifier text,
    value boolean
);


CREATE TABLE public.tbl_analysis_categorical_values (
    analysis_categorical_value_id bigint NOT NULL,
    analysis_value_id bigint NOT NULL,
    value_type_item_id integer NOT NULL,
    value numeric(20,10) DEFAULT NULL::numeric,
    is_variant boolean
);


CREATE TABLE public.tbl_analysis_dating_ranges (
    analysis_dating_range_id bigint NOT NULL,
    analysis_value_id bigint NOT NULL,
    low_value integer,
    high_value integer,
    low_is_uncertain boolean,
    high_is_uncertain boolean,
    low_qualifier text,
    high_qualifier text,
    age_type_id integer DEFAULT 1 NOT NULL,
    season_id integer,
    dating_uncertainty_id integer,
    is_variant boolean
);


CREATE TABLE public.tbl_analysis_entities (
    analysis_entity_id bigint NOT NULL,
    physical_sample_id integer,
    dataset_id integer
);


CREATE TABLE public.tbl_analysis_entity_ages (
    analysis_entity_age_id integer NOT NULL,
    age numeric(20,5),
    age_older numeric(20,5),
    age_younger numeric(20,5),
    analysis_entity_id bigint,
    chronology_id integer,
    dating_specifier text,
    age_range int4range GENERATED ALWAYS AS (
CASE
    WHEN ((age_younger IS NULL) AND (age_older IS NULL)) THEN NULL::int4range
    ELSE int4range(COALESCE((age_younger)::integer, (age_older)::integer), (COALESCE((age_older)::integer, (age_younger)::integer) + 1))
END) STORED
);


CREATE TABLE public.tbl_analysis_entity_dimensions (
    analysis_entity_dimension_id integer NOT NULL,
    analysis_entity_id bigint NOT NULL,
    dimension_id integer NOT NULL,
    dimension_value numeric NOT NULL
);


CREATE TABLE public.tbl_analysis_entity_prep_methods (
    analysis_entity_prep_method_id integer NOT NULL,
    analysis_entity_id bigint NOT NULL,
    method_id integer NOT NULL
);


CREATE TABLE public.tbl_analysis_identifiers (
    analysis_identifier_id bigint NOT NULL,
    analysis_value_id bigint NOT NULL,
    value text NOT NULL
);


CREATE TABLE public.tbl_analysis_integer_ranges (
    analysis_integer_range_id bigint NOT NULL,
    analysis_value_id bigint NOT NULL,
    low_value integer,
    high_value integer,
    low_is_uncertain boolean,
    high_is_uncertain boolean,
    low_qualifier text,
    high_qualifier text,
    is_variant boolean
);


CREATE TABLE public.tbl_analysis_integer_values (
    analysis_integer_value_id bigint NOT NULL,
    analysis_value_id bigint NOT NULL,
    qualifier text,
    value integer,
    is_variant boolean
);


CREATE TABLE public.tbl_analysis_notes (
    analysis_note_id bigint NOT NULL,
    analysis_value_id bigint NOT NULL,
    value text NOT NULL
);


CREATE TABLE public.tbl_analysis_numerical_ranges (
    analysis_numerical_range_id bigint NOT NULL,
    analysis_value_id bigint NOT NULL,
    value numrange NOT NULL,
    low_is_uncertain boolean,
    high_is_uncertain boolean,
    low_qualifier text,
    high_qualifier text,
    is_variant boolean
);


CREATE TABLE public.tbl_analysis_numerical_values (
    analysis_numerical_value_id bigint NOT NULL,
    analysis_value_id bigint NOT NULL,
    qualifier text,
    value numeric(20,10),
    is_variant boolean
);


CREATE TABLE public.tbl_analysis_taxon_counts (
    analysis_taxon_count_id integer NOT NULL,
    analysis_value_id bigint NOT NULL,
    taxon_id integer NOT NULL,
    value numeric(20,10) NOT NULL
);


CREATE TABLE public.tbl_analysis_values (
    analysis_value_id bigint NOT NULL,
    value_class_id integer NOT NULL,
    analysis_entity_id bigint NOT NULL,
    analysis_value text,
    boolean_value boolean,
    is_boolean boolean,
    is_uncertain boolean,
    is_undefined boolean,
    is_not_analyzed boolean,
    is_indeterminable boolean,
    is_anomaly boolean
);


CREATE TABLE public.tbl_analysis_value_dimensions (
    analysis_value_dimension_id integer NOT NULL,
    analysis_value_id bigint NOT NULL,
    dimension_id integer NOT NULL,
    value numeric(20,10) NOT NULL
);


CREATE TABLE public.tbl_biblio (
    biblio_id integer NOT NULL,
    bugs_reference character varying(60) DEFAULT NULL::character varying,
    doi character varying(255) DEFAULT NULL::character varying,
    isbn character varying(128) DEFAULT NULL::character varying,
    notes text,
    title character varying,
    year character varying(255) DEFAULT NULL::character varying,
    authors character varying,
    full_reference text DEFAULT ''::text NOT NULL,
    url character varying,
    biblio_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_ceramics (
    ceramics_id integer NOT NULL,
    analysis_entity_id integer NOT NULL,
    measurement_value character varying NOT NULL,
    ceramics_lookup_id integer NOT NULL
);


CREATE TABLE public.tbl_ceramics_lookup (
    ceramics_lookup_id integer NOT NULL,
    method_id integer NOT NULL,
    description text,
    name character varying NOT NULL
);


CREATE TABLE public.tbl_ceramics_measurements (
    ceramics_measurement_id integer NOT NULL,
    method_id integer
);


CREATE TABLE public.tbl_chronologies (
    chronology_id integer NOT NULL,
    age_model text,
    relative_age_type_id integer,
    chronology_name text,
    contact_id integer,
    date_prepared timestamp(0) without time zone,
    notes text
);


CREATE TABLE public.tbl_colours (
    colour_id integer NOT NULL,
    colour_name character varying(30) NOT NULL,
    method_id integer NOT NULL,
    rgb integer
);


CREATE TABLE public.tbl_contacts (
    contact_id integer NOT NULL,
    address_1 character varying(255),
    address_2 character varying(255),
    location_id integer,
    email character varying,
    first_name character varying(50),
    last_name character varying(100),
    phone_number character varying(50),
    url text
);


CREATE TABLE public.tbl_contact_types (
    contact_type_id integer NOT NULL,
    contact_type_name character varying(150) NOT NULL,
    description text
);


CREATE TABLE public.tbl_coordinate_method_dimensions (
    coordinate_method_dimension_id integer NOT NULL,
    dimension_id integer NOT NULL,
    method_id integer NOT NULL,
    limit_upper numeric(18,10),
    limit_lower numeric(18,10)
);


CREATE TABLE public.tbl_data_types (
    data_type_id integer NOT NULL,
    data_type_group_id integer NOT NULL,
    data_type_name character varying(25) DEFAULT NULL::character varying,
    definition text
);


CREATE TABLE public.tbl_data_type_groups (
    data_type_group_id integer NOT NULL,
    data_type_group_name character varying(25),
    description text
);


CREATE TABLE public.tbl_datasets (
    dataset_id integer NOT NULL,
    master_set_id integer,
    data_type_id integer NOT NULL,
    method_id integer,
    biblio_id integer,
    updated_dataset_id integer,
    project_id integer,
    dataset_name character varying(50) NOT NULL,
    dataset_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_dataset_contacts (
    dataset_contact_id integer NOT NULL,
    contact_id integer NOT NULL,
    contact_type_id integer NOT NULL,
    dataset_id integer NOT NULL
);


CREATE TABLE public.tbl_dataset_masters (
    master_set_id integer NOT NULL,
    contact_id integer,
    biblio_id integer,
    master_name character varying(100),
    master_notes text,
    url text,
    master_set_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_dataset_methods (
    dataset_method_id integer NOT NULL,
    dataset_id integer NOT NULL,
    method_id integer NOT NULL
);

CREATE TABLE public.tbl_dataset_submissions (
    dataset_submission_id integer NOT NULL,
    dataset_id integer NOT NULL,
    submission_type_id integer NOT NULL,
    contact_id integer NOT NULL,
    date_submitted text,
    notes text
);


CREATE TABLE public.tbl_dataset_submission_types (
    submission_type_id integer NOT NULL,
    submission_type character varying(60) NOT NULL,
    description text
);


CREATE TABLE public.tbl_dating_labs (
    dating_lab_id integer NOT NULL,
    contact_id integer,
    international_lab_id character varying(10) NOT NULL,
    lab_name character varying(100) DEFAULT NULL::character varying,
    country_id integer
);


CREATE TABLE public.tbl_dating_material (
    dating_material_id integer NOT NULL,
    geochron_id integer NOT NULL,
    taxon_id integer,
    material_dated character varying,
    description text,
    abundance_element_id integer
);


CREATE TABLE public.tbl_dating_uncertainty (
    dating_uncertainty_id integer NOT NULL,
    description text,
    uncertainty character varying
);


CREATE TABLE public.tbl_dendro (
    dendro_id integer NOT NULL,
    analysis_entity_id integer NOT NULL,
    measurement_value character varying NOT NULL,
    dendro_lookup_id integer NOT NULL
);

CREATE TABLE public.tbl_dendro_dates (
    dendro_date_id integer NOT NULL,
    season_id integer,
    dating_uncertainty_id integer,
    dendro_lookup_id integer NOT NULL,
    age_type_id integer NOT NULL,
    analysis_entity_id integer NOT NULL,
    age_older integer,
    age_younger integer,
    age_range int4range GENERATED ALWAYS AS (
CASE
    WHEN ((age_younger IS NULL) AND (age_older IS NULL)) THEN NULL::int4range
    ELSE int4range(COALESCE(age_older, age_younger), (COALESCE(age_younger, age_older) + 1))
END) STORED
);


CREATE TABLE public.tbl_dendro_date_notes (
    dendro_date_note_id integer NOT NULL,
    dendro_date_id integer NOT NULL,
    note text
);

CREATE TABLE public.tbl_dendro_lookup (
    dendro_lookup_id integer NOT NULL,
    method_id integer,
    name character varying NOT NULL,
    description text
);


CREATE TABLE public.tbl_dimensions (
    dimension_id integer NOT NULL,
    dimension_abbrev character varying(40),
    dimension_description text,
    dimension_name character varying(50) NOT NULL,
    unit_id integer,
    method_group_id integer
);


CREATE TABLE public.tbl_ecocodes (
    ecocode_id integer NOT NULL,
    ecocode_definition_id integer DEFAULT 0,
    taxon_id integer DEFAULT 0
);


CREATE TABLE public.tbl_ecocode_definitions (
    ecocode_definition_id integer NOT NULL,
    abbreviation character varying(10) DEFAULT NULL::character varying,
    definition text,
    ecocode_group_id integer DEFAULT 0,
    name character varying(150) DEFAULT NULL::character varying,
    notes text,
    sort_order smallint DEFAULT 0
);


CREATE TABLE public.tbl_ecocode_groups (
    ecocode_group_id integer NOT NULL,
    definition text DEFAULT NULL::character varying,
    ecocode_system_id integer DEFAULT 0,
    name character varying(200) DEFAULT NULL::character varying,
    abbreviation character varying(255)
);


CREATE TABLE public.tbl_ecocode_systems (
    ecocode_system_id integer NOT NULL,
    biblio_id integer,
    definition text DEFAULT NULL::character varying,
    name character varying(50) DEFAULT NULL::character varying,
    notes text,
    ecocode_system_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_features (
    feature_id integer NOT NULL,
    feature_type_id integer NOT NULL,
    feature_name character varying,
    feature_description text
);


CREATE TABLE public.tbl_feature_types (
    feature_type_id integer NOT NULL,
    feature_type_name character varying(128),
    feature_type_description text
);


CREATE TABLE public.tbl_geochron_refs (
    geochron_ref_id integer NOT NULL,
    geochron_id integer NOT NULL,
    biblio_id integer NOT NULL
);


CREATE TABLE public.tbl_geochronology (
    geochron_id integer NOT NULL,
    analysis_entity_id bigint NOT NULL,
    dating_lab_id integer,
    lab_number character varying(40),
    age numeric(20,5),
    error_older numeric(20,5),
    error_younger numeric(20,5),
    delta_13c numeric(10,5),
    notes text,
    dating_uncertainty_id integer,
    geochron_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_horizons (
    horizon_id integer NOT NULL,
    description text,
    horizon_name character varying(15) NOT NULL,
    method_id integer NOT NULL
);


CREATE TABLE public.tbl_identification_levels (
    identification_level_id integer NOT NULL,
    identification_level_abbrev character varying(50) DEFAULT NULL::character varying,
    identification_level_name character varying(50) DEFAULT NULL::character varying,
    notes text
);


CREATE TABLE public.tbl_image_types (
    image_type_id integer NOT NULL,
    description text,
    image_type character varying(40) NOT NULL
);


CREATE TABLE public.tbl_imported_taxa_replacements (
    imported_taxa_replacement_id integer NOT NULL,
    imported_name_replaced character varying(100) NOT NULL,
    taxon_id integer NOT NULL
);

CREATE TABLE public.tbl_isotopes (
    isotope_id integer NOT NULL,
    analysis_entity_id integer NOT NULL,
    isotope_measurement_id integer NOT NULL,
    isotope_standard_id integer,
    measurement_value text,
    unit_id integer NOT NULL,
    isotope_value_specifier_id integer NOT NULL
);

CREATE TABLE public.tbl_isotope_measurements (
    isotope_measurement_id integer NOT NULL,
    isotope_standard_id integer,
    method_id integer,
    isotope_type_id integer
);

CREATE TABLE public.tbl_isotope_standards (
    isotope_standard_id integer NOT NULL,
    isotope_ration character varying,
    international_scale character varying,
    accepted_ratio_xe6 character varying,
    error_of_ratio character varying,
    reference character varying
);


CREATE TABLE public.tbl_isotope_types (
    isotope_type_id integer NOT NULL,
    designation character varying,
    abbreviation character varying,
    atomic_number numeric,
    description text,
    alternative_designation character varying
);


CREATE TABLE public.tbl_isotope_value_specifiers (
    isotope_value_specifier_id integer NOT NULL,
    name character varying NOT NULL,
    description text NOT NULL
);

CREATE TABLE public.tbl_languages (
    language_id integer NOT NULL,
    language_name_english character varying(100) DEFAULT NULL::character varying,
    language_name_native character varying(100) DEFAULT NULL::character varying
);


CREATE TABLE public.tbl_lithology (
    lithology_id integer NOT NULL,
    depth_bottom numeric(20,5),
    depth_top numeric(20,5) NOT NULL,
    description text NOT NULL,
    lower_boundary character varying(255),
    sample_group_id integer NOT NULL
);


CREATE TABLE public.tbl_locations (
    location_id integer NOT NULL,
    location_name character varying(255) NOT NULL,
    location_type_id integer NOT NULL,
    default_lat_dd numeric(18,10),
    default_long_dd numeric(18,10)
);


CREATE TABLE public.tbl_location_types (
    location_type_id integer NOT NULL,
    description text,
    location_type character varying(40)
);


CREATE TABLE public.tbl_mcr_names (
    taxon_id integer NOT NULL,
    comparison_notes character varying(255) DEFAULT NULL::character varying,
    mcr_name_trim character varying(80) DEFAULT NULL::character varying,
    mcr_number smallint DEFAULT 0,
    mcr_species_name character varying(200) DEFAULT NULL::character varying
);


CREATE TABLE public.tbl_mcr_summary_data (
    mcr_summary_data_id integer NOT NULL,
    cog_mid_tmax smallint DEFAULT 0,
    cog_mid_trange smallint DEFAULT 0,
    taxon_id integer NOT NULL,
    tmax_hi smallint DEFAULT 0,
    tmax_lo smallint DEFAULT 0,
    tmin_hi smallint DEFAULT 0,
    tmin_lo smallint DEFAULT 0,
    trange_hi smallint DEFAULT 0,
    trange_lo smallint DEFAULT 0
);


CREATE TABLE public.tbl_mcrdata_birmbeetledat (
    mcrdata_birmbeetledat_id integer NOT NULL,
    mcr_data text,
    mcr_row smallint NOT NULL,
    taxon_id integer NOT NULL
);


CREATE TABLE public.tbl_measured_values (
    measured_value_id bigint NOT NULL,
    analysis_entity_id bigint NOT NULL,
    measured_value numeric(20,10) NOT NULL
);


CREATE TABLE public.tbl_measured_value_dimensions (
    measured_value_dimension_id integer NOT NULL,
    dimension_id integer NOT NULL,
    dimension_value numeric(18,10) NOT NULL,
    measured_value_id bigint NOT NULL
);


CREATE TABLE public.tbl_methods (
    method_id integer NOT NULL,
    biblio_id integer,
    description text NOT NULL,
    method_abbrev_or_alt_name character varying(50),
    method_group_id integer NOT NULL,
    method_name character varying(50) NOT NULL,
    record_type_id integer,
    unit_id integer,
    method_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_method_groups (
    method_group_id integer NOT NULL,
    description text NOT NULL,
    group_name character varying(100) NOT NULL
);


CREATE TABLE public.tbl_modification_types (
    modification_type_id integer NOT NULL,
    modification_type_name character varying(128),
    modification_type_description text
);


CREATE TABLE public.tbl_physical_samples (
    physical_sample_id integer NOT NULL,
    sample_group_id integer DEFAULT 0 NOT NULL,
    alt_ref_type_id integer,
    sample_type_id integer NOT NULL,
    sample_name character varying(50) NOT NULL,
    date_sampled character varying
);


CREATE TABLE public.tbl_physical_sample_features (
    physical_sample_feature_id integer NOT NULL,
    feature_id integer NOT NULL,
    physical_sample_id integer NOT NULL
);


CREATE TABLE public.tbl_projects (
    project_id integer NOT NULL,
    project_type_id integer,
    project_stage_id integer,
    project_name character varying(150),
    project_abbrev_name character varying(25),
    description text
);


CREATE TABLE public.tbl_project_stages (
    project_stage_id integer NOT NULL,
    stage_name character varying,
    description text
);


CREATE TABLE public.tbl_project_types (
    project_type_id integer NOT NULL,
    project_type_name character varying,
    description text
);


CREATE TABLE public.tbl_rdb (
    rdb_id integer NOT NULL,
    location_id integer NOT NULL,
    rdb_code_id integer,
    taxon_id integer NOT NULL
);


CREATE TABLE public.tbl_rdb_codes (
    rdb_code_id integer NOT NULL,
    rdb_category character varying(4) DEFAULT NULL::character varying,
    rdb_definition character varying(200) DEFAULT NULL::character varying,
    rdb_system_id integer DEFAULT 0
);


CREATE TABLE public.tbl_rdb_systems (
    rdb_system_id integer NOT NULL,
    biblio_id integer NOT NULL,
    location_id integer NOT NULL,
    rdb_first_published smallint,
    rdb_system character varying(10) DEFAULT NULL::character varying,
    rdb_system_date integer,
    rdb_version character varying(10) DEFAULT NULL::character varying,
    rdb_system_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_record_types (
    record_type_id integer NOT NULL,
    record_type_name character varying(50) DEFAULT NULL::character varying,
    record_type_description text
);


CREATE TABLE public.tbl_relative_ages (
    relative_age_id integer NOT NULL,
    relative_age_type_id integer,
    relative_age_name character varying(50),
    description text,
    c14_age_older numeric(20,5),
    c14_age_younger numeric(20,5),
    cal_age_older numeric(20,5),
    cal_age_younger numeric(20,5),
    notes text,
    location_id integer,
    abbreviation character varying,
    relative_age_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_relative_age_refs (
    relative_age_ref_id integer NOT NULL,
    biblio_id integer NOT NULL,
    relative_age_id integer NOT NULL
);


CREATE TABLE public.tbl_relative_age_types (
    relative_age_type_id integer NOT NULL,
    age_type character varying,
    description text
);


CREATE TABLE public.tbl_relative_dates (
    relative_date_id integer NOT NULL,
    relative_age_id integer,
    method_id integer,
    notes text,
    dating_uncertainty_id integer,
    analysis_entity_id integer NOT NULL
);


CREATE TABLE public.tbl_sample_alt_refs (
    sample_alt_ref_id integer NOT NULL,
    alt_ref character varying(80) NOT NULL,
    alt_ref_type_id integer NOT NULL,
    physical_sample_id integer NOT NULL
);


CREATE TABLE public.tbl_sample_colours (
    sample_colour_id integer NOT NULL,
    colour_id integer NOT NULL,
    physical_sample_id integer NOT NULL
);


CREATE TABLE public.tbl_sample_coordinates (
    sample_coordinate_id integer NOT NULL,
    physical_sample_id integer NOT NULL,
    coordinate_method_dimension_id integer NOT NULL,
    measurement numeric(20,10) NOT NULL,
    accuracy numeric(20,10)
);


CREATE TABLE public.tbl_sample_descriptions (
    sample_description_id integer NOT NULL,
    sample_description_type_id integer NOT NULL,
    physical_sample_id integer NOT NULL,
    description character varying
);


CREATE TABLE public.tbl_sample_description_sample_group_contexts (
    sample_description_sample_group_context_id integer NOT NULL,
    sampling_context_id integer,
    sample_description_type_id integer
);


CREATE TABLE public.tbl_sample_description_types (
    sample_description_type_id integer NOT NULL,
    type_name character varying(255),
    type_description text
);


CREATE TABLE public.tbl_sample_dimensions (
    sample_dimension_id integer NOT NULL,
    physical_sample_id integer NOT NULL,
    dimension_id integer NOT NULL,
    method_id integer NOT NULL,
    dimension_value numeric(20,10) NOT NULL,
    qualifier_id integer
);


CREATE TABLE public.tbl_sample_groups (
    sample_group_id integer NOT NULL,
    site_id integer DEFAULT 0,
    sampling_context_id integer,
    method_id integer NOT NULL,
    sample_group_name character varying(100) DEFAULT NULL::character varying,
    sample_group_description text,
    sample_group_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_sample_group_coordinates (
    sample_group_position_id integer NOT NULL,
    coordinate_method_dimension_id integer NOT NULL,
    sample_group_position numeric(20,10),
    position_accuracy character varying(128),
    sample_group_id integer NOT NULL
);


CREATE TABLE public.tbl_sample_group_descriptions (
    sample_group_description_id integer NOT NULL,
    group_description character varying,
    sample_group_description_type_id integer NOT NULL,
    sample_group_id integer
);


CREATE TABLE public.tbl_sample_group_description_types (
    sample_group_description_type_id integer NOT NULL,
    type_name character varying(255),
    type_description character varying
);


CREATE TABLE public.tbl_sample_group_description_type_sampling_contexts (
    sample_group_description_type_sampling_context_id integer NOT NULL,
    sampling_context_id integer NOT NULL,
    sample_group_description_type_id integer NOT NULL
);


CREATE TABLE public.tbl_sample_group_dimensions (
    sample_group_dimension_id integer NOT NULL,
    dimension_id integer NOT NULL,
    dimension_value numeric(20,5) NOT NULL,
    sample_group_id integer NOT NULL,
    qualifier_id integer
);


CREATE TABLE public.tbl_sample_group_images (
    sample_group_image_id integer NOT NULL,
    description text,
    image_location text NOT NULL,
    image_name character varying(80),
    image_type_id integer NOT NULL,
    sample_group_id integer NOT NULL
);


CREATE TABLE public.tbl_sample_group_notes (
    sample_group_note_id integer NOT NULL,
    sample_group_id integer NOT NULL,
    note character varying
);


CREATE TABLE public.tbl_sample_group_references (
    sample_group_reference_id integer NOT NULL,
    biblio_id integer NOT NULL,
    sample_group_id integer DEFAULT 0
);


CREATE TABLE public.tbl_sample_group_sampling_contexts (
    sampling_context_id integer NOT NULL,
    sampling_context character varying(80) NOT NULL,
    description text,
    sort_order smallint DEFAULT 0 NOT NULL
);


CREATE TABLE public.tbl_sample_horizons (
    sample_horizon_id integer NOT NULL,
    horizon_id integer NOT NULL,
    physical_sample_id integer NOT NULL
);


CREATE TABLE public.tbl_sample_images (
    sample_image_id integer NOT NULL,
    description text,
    image_location text NOT NULL,
    image_name character varying(80),
    image_type_id integer NOT NULL,
    physical_sample_id integer NOT NULL
);


CREATE TABLE public.tbl_sample_locations (
    sample_location_id integer NOT NULL,
    sample_location_type_id integer NOT NULL,
    physical_sample_id integer NOT NULL,
    location character varying(255)
);


CREATE TABLE public.tbl_sample_location_types (
    sample_location_type_id integer NOT NULL,
    location_type character varying(255),
    location_type_description text
);


CREATE TABLE public.tbl_sample_location_type_sampling_contexts (
    sample_location_type_sampling_context_id integer NOT NULL,
    sampling_context_id integer NOT NULL,
    sample_location_type_id integer NOT NULL
);


CREATE TABLE public.tbl_sample_notes (
    sample_note_id integer NOT NULL,
    physical_sample_id integer NOT NULL,
    note_type character varying,
    note text NOT NULL
);


CREATE TABLE public.tbl_sample_types (
    sample_type_id integer NOT NULL,
    type_name character varying(40) NOT NULL,
    description text
);


CREATE TABLE public.tbl_seasons (
    season_id integer NOT NULL,
    season_name character varying(20) DEFAULT NULL::character varying,
    season_type character varying(30) DEFAULT NULL::character varying,
    season_type_id integer,
    sort_order smallint DEFAULT 0
);


CREATE TABLE public.tbl_season_types (
    season_type_id integer NOT NULL,
    description text,
    season_type character varying(30)
);


CREATE TABLE public.tbl_sites (
    site_id integer NOT NULL,
    altitude numeric(18,10),
    latitude_dd numeric(18,10),
    longitude_dd numeric(18,10),
    national_site_identifier character varying(255),
    site_description text DEFAULT NULL::character varying,
    site_name character varying(60) DEFAULT NULL::character varying,
    site_preservation_status_id integer,
    site_location_accuracy character varying,
    site_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_site_images (
    site_image_id integer NOT NULL,
    contact_id integer,
    credit character varying(100),
    date_taken date,
    description text,
    image_location text NOT NULL,
    image_name character varying(80),
    image_type_id integer NOT NULL,
    site_id integer NOT NULL
);


CREATE TABLE public.tbl_site_locations (
    site_location_id integer NOT NULL,
    location_id integer NOT NULL,
    site_id integer NOT NULL
);


CREATE TABLE public.tbl_site_natgridrefs (
    site_natgridref_id integer NOT NULL,
    site_id integer NOT NULL,
    method_id integer NOT NULL,
    natgridref character varying NOT NULL
);


CREATE TABLE public.tbl_site_other_records (
    site_other_records_id integer NOT NULL,
    site_id integer,
    biblio_id integer,
    record_type_id integer,
    description text,
    site_other_records_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_site_preservation_status (
    site_preservation_status_id integer NOT NULL,
    site_id integer,
    preservation_status_or_threat character varying,
    description text,
    assessment_type character varying,
    assessment_author_contact_id integer,
    "Evaluation_date" date
);


CREATE TABLE public.tbl_site_references (
    site_reference_id integer NOT NULL,
    site_id integer DEFAULT 0,
    biblio_id integer NOT NULL
);


CREATE TABLE public.tbl_species_associations (
    species_association_id integer NOT NULL,
    associated_taxon_id integer NOT NULL,
    biblio_id integer,
    taxon_id integer NOT NULL,
    association_type_id integer,
    referencing_type text,
    species_association_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_species_association_types (
    association_type_id integer NOT NULL,
    association_type_name character varying(255),
    association_description text
);


CREATE TABLE public.tbl_taxa_common_names (
    taxon_common_name_id integer NOT NULL,
    common_name character varying(255) DEFAULT NULL::character varying,
    language_id integer DEFAULT 0,
    taxon_id integer DEFAULT 0
);


CREATE TABLE public.tbl_taxa_images (
    taxa_images_id integer NOT NULL,
    image_name character varying,
    description text,
    image_location text,
    image_type_id integer,
    taxon_id integer NOT NULL
);


CREATE TABLE public.tbl_taxa_measured_attributes (
    measured_attribute_id integer NOT NULL,
    attribute_measure character varying(255) DEFAULT NULL::character varying,
    attribute_type character varying(255) DEFAULT NULL::character varying,
    attribute_units character varying(10) DEFAULT NULL::character varying,
    data numeric(18,10) DEFAULT 0,
    taxon_id integer NOT NULL
);


CREATE TABLE public.tbl_taxa_reference_specimens (
    taxa_reference_specimen_id integer NOT NULL,
    taxon_id integer NOT NULL,
    contact_id integer NOT NULL,
    notes text
);


CREATE TABLE public.tbl_taxa_seasonality (
    seasonality_id integer NOT NULL,
    activity_type_id integer NOT NULL,
    season_id integer DEFAULT 0,
    taxon_id integer NOT NULL,
    location_id integer NOT NULL
);


CREATE TABLE public.tbl_taxa_synonyms (
    synonym_id integer NOT NULL,
    biblio_id integer NOT NULL,
    family_id integer,
    genus_id integer,
    notes text DEFAULT NULL::character varying,
    taxon_id integer,
    author_id integer,
    synonym character varying(255),
    reference_type character varying,
    synonym_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_taxa_tree_authors (
    author_id integer NOT NULL,
    author_name character varying(100) DEFAULT NULL::character varying
);


CREATE TABLE public.tbl_taxa_tree_families (
    family_id integer NOT NULL,
    family_name character varying(100) DEFAULT NULL::character varying,
    order_id integer NOT NULL
);


CREATE TABLE public.tbl_taxa_tree_genera (
    genus_id integer NOT NULL,
    family_id integer,
    genus_name character varying(100) DEFAULT NULL::character varying
);


CREATE TABLE public.tbl_taxa_tree_master (
    taxon_id integer NOT NULL,
    author_id integer,
    genus_id integer,
    species character varying(255) DEFAULT NULL::character varying
);


CREATE TABLE public.tbl_taxa_tree_orders (
    order_id integer NOT NULL,
    order_name character varying(50) DEFAULT NULL::character varying,
    record_type_id integer,
    sort_order integer
);


CREATE TABLE public.tbl_taxonomic_order (
    taxonomic_order_id integer NOT NULL,
    taxon_id integer DEFAULT 0,
    taxonomic_code numeric(18,10) DEFAULT 0,
    taxonomic_order_system_id integer DEFAULT 0
);


CREATE TABLE public.tbl_taxonomic_order_biblio (
    taxonomic_order_biblio_id integer NOT NULL,
    biblio_id integer DEFAULT 0,
    taxonomic_order_system_id integer DEFAULT 0
);


CREATE TABLE public.tbl_taxonomic_order_systems (
    taxonomic_order_system_id integer NOT NULL,
    system_description text,
    system_name character varying(50) DEFAULT NULL::character varying,
    taxonomic_order_system_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_taxonomy_notes (
    taxonomy_notes_id integer NOT NULL,
    biblio_id integer NOT NULL,
    taxon_id integer NOT NULL,
    taxonomy_notes text,
    taxonomy_notes_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_temperatures (
    record_id integer NOT NULL,
    years_bp integer NOT NULL,
    d180_gisp2 numeric
);


CREATE TABLE public.tbl_tephras (
    tephra_id integer NOT NULL,
    c14_age numeric(20,5),
    c14_age_older numeric(20,5),
    c14_age_younger numeric(20,5),
    cal_age numeric(20,5),
    cal_age_older numeric(20,5),
    cal_age_younger numeric(20,5),
    notes text,
    tephra_name character varying(80),
    tephra_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_tephra_dates (
    tephra_date_id integer NOT NULL,
    analysis_entity_id bigint NOT NULL,
    notes text,
    tephra_id integer NOT NULL,
    dating_uncertainty_id integer
);


CREATE TABLE public.tbl_tephra_refs (
    tephra_ref_id integer NOT NULL,
    biblio_id integer NOT NULL,
    tephra_id integer NOT NULL
);


CREATE TABLE public.tbl_text_biology (
    biology_id integer NOT NULL,
    biblio_id integer NOT NULL,
    biology_text text,
    taxon_id integer NOT NULL,
    biology_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_text_distribution (
    distribution_id integer NOT NULL,
    biblio_id integer NOT NULL,
    distribution_text text,
    taxon_id integer NOT NULL,
    distribution_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_text_identification_keys (
    key_id integer NOT NULL,
    biblio_id integer NOT NULL,
    key_text text,
    taxon_id integer NOT NULL,
    key_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_units (
    unit_id integer NOT NULL,
    description text,
    unit_abbrev character varying(15),
    unit_name character varying(50) NOT NULL
);


CREATE TABLE public.tbl_updates_log (
    updates_log_id integer NOT NULL,
    table_name character varying(150) NOT NULL,
    last_updated date NOT NULL
);

CREATE TABLE public.tbl_value_classes (
    value_class_id integer NOT NULL,
    value_type_id integer NOT NULL,
    method_id integer NOT NULL,
    parent_id integer,
    name character varying(80) NOT NULL,
    description text NOT NULL,
    value_class_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_value_qualifiers (
    qualifier_id integer NOT NULL,
    symbol text NOT NULL,
    description text NOT NULL,
    qualifier_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_value_qualifier_symbols (
    qualifier_symbol_id integer NOT NULL,
    symbol text NOT NULL,
    cardinal_qualifier_id integer NOT NULL,
    qualifier_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_value_types (
    value_type_id integer NOT NULL,
    unit_id integer,
    data_type_id integer,
    name text NOT NULL,
    base_type text NOT NULL,
    "precision" integer,
    description text NOT NULL,
    value_type_uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL
);


CREATE TABLE public.tbl_value_type_items (
    value_type_item_id integer NOT NULL,
    value_type_id integer NOT NULL,
    name character varying(80) DEFAULT NULL::character varying,
    description text
);


CREATE TABLE public.tbl_years_types (
    years_type_id integer NOT NULL,
    name character varying NOT NULL,
    description text
);


CREATE TABLE public.tbl_abundance_properties (
    abundance_property_id integer NOT NULL,
    abundance_id integer NOT NULL,
    property_type_id integer NOT NULL,
    property_value text NOT NULL
);

CREATE TABLE public.tbl_property_types (
    uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    property_type_id integer NOT NULL,
    property_type_name text NOT NULL,
    description text NOT NULL,
    value_type_id integer,
    value_class_id integer
);

CREATE TABLE public.tbl_site_properties (
    site_property_id integer NOT NULL,
    site_id integer NOT NULL,
    property_type_id integer NOT NULL,
    property_value text NOT NULL
);

CREATE TABLE public.tbl_site_site_types (
    site_site_type_id integer NOT NULL,
    site_id integer NOT NULL,
    site_type_id integer NOT NULL,
    is_primary_type boolean DEFAULT false NOT NULL,
    confidence_code smallint,
    notes text
);

CREATE TABLE public.tbl_site_type_groups (
    site_type_group_id integer NOT NULL,
    site_type_group_abbrev character varying(40) NOT NULL,
    site_type_group character varying(255) NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    origin_code character varying(40),
    origin_description text DEFAULT ''::text NOT NULL
);

CREATE TABLE public.tbl_site_types (
    site_type_id integer NOT NULL,
    site_type_group_id integer NOT NULL,
    site_type_abbrev character varying(40) NOT NULL,
    site_type character varying(256) NOT NULL,
    description text DEFAULT ''::text NOT NULL
);

CREATE TABLE public.v_sql (
    "?column?" text COLLATE pg_catalog."C"
);

