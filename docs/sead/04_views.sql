CREATE VIEW public.master_set_reference AS
 SELECT DISTINCT tbl_abundances.abundance_id,
    string_agg(
        CASE
            WHEN ((tbl_biblio.full_reference IS NOT NULL) AND (tbl_biblio.full_reference <> ''::text)) THEN tbl_biblio.full_reference
            ELSE (((COALESCE(tbl_biblio.authors, ''::character varying))::text || ' '::text) || (COALESCE(tbl_biblio.title, ''::character varying))::text)
        END, ' | '::text) AS "associatedReferences"
   FROM ((((public.tbl_abundances
     JOIN public.tbl_analysis_entities ON ((tbl_abundances.analysis_entity_id = tbl_analysis_entities.analysis_entity_id)))
     JOIN public.tbl_datasets ON ((tbl_datasets.dataset_id = tbl_analysis_entities.dataset_id)))
     JOIN public.tbl_dataset_masters ON ((tbl_dataset_masters.master_set_id = tbl_datasets.master_set_id)))
     JOIN public.tbl_biblio ON ((tbl_dataset_masters.biblio_id = tbl_biblio.biblio_id)))
  GROUP BY tbl_abundances.abundance_id;


ALTER VIEW public.master_set_reference OWNER TO rebecka;

--
-- Name: taxon_view; Type: VIEW; Schema: public; Owner: rebecka
--

CREATE VIEW public.taxon_view AS
 SELECT DISTINCT tbl_taxa_tree_master.taxon_id,
    tbl_taxa_tree_master.species,
    tbl_taxa_tree_genera.genus_name,
    tbl_taxa_tree_families.family_name,
        CASE
            WHEN (((tbl_taxa_tree_master.species)::text <> ALL ((ARRAY['sp.'::character varying, 'spp.'::character varying])::text[])) AND ((tbl_taxa_tree_master.species)::text !~~ '% sp.%'::text) AND ((tbl_taxa_tree_master.species)::text !~~ '% spp.%'::text)) THEN (tbl_taxonomic_order.taxonomic_code)::integer
            ELSE NULL::integer
        END AS dyntaxa_taxon_id,
        CASE
            WHEN ((tbl_taxonomic_order.taxonomic_code IS NOT NULL) AND ((tbl_taxa_tree_master.species)::text <> ALL ((ARRAY['sp.'::character varying, 'spp.'::character varying])::text[])) AND ((tbl_taxa_tree_master.species)::text !~~ '% sp.%'::text) AND ((tbl_taxa_tree_master.species)::text !~~ '% spp.%'::text)) THEN 'Dyntaxa taxon id'::text
            ELSE ''::text
        END AS "taxonRemarks",
    concat(tbl_taxa_tree_genera.genus_name, ' ', tbl_taxa_tree_master.species, ' ',
        CASE
            WHEN ((tbl_taxa_tree_authors.author_name IS NOT NULL) AND ((tbl_taxa_tree_authors.author_name)::text !~~ '%(%'::text)) THEN (concat(' (', tbl_taxa_tree_authors.author_name, ')'))::character varying
            ELSE COALESCE(tbl_taxa_tree_authors.author_name, ''::character varying)
        END) AS "scientificName"
   FROM (((((public.tbl_taxa_tree_master
     LEFT JOIN public.tbl_taxa_tree_authors ON ((tbl_taxa_tree_master.author_id = tbl_taxa_tree_authors.author_id)))
     JOIN public.tbl_taxa_tree_genera ON ((tbl_taxa_tree_master.genus_id = tbl_taxa_tree_genera.genus_id)))
     JOIN public.tbl_taxa_tree_families ON ((tbl_taxa_tree_genera.family_id = tbl_taxa_tree_families.family_id)))
     JOIN public.tbl_taxa_tree_orders ON ((tbl_taxa_tree_families.order_id = tbl_taxa_tree_orders.order_id)))
     LEFT JOIN public.tbl_taxonomic_order ON (((tbl_taxonomic_order.taxon_id = tbl_taxa_tree_master.taxon_id) AND (tbl_taxonomic_order.taxonomic_order_system_id = 2))))
  WHERE (tbl_taxa_tree_orders.record_type_id = 1);


ALTER VIEW public.taxon_view OWNER TO rebecka;

--
-- Name: view_typed_analysis_tables; Type: VIEW; Schema: public; Owner: sead_master
--

CREATE VIEW public.view_typed_analysis_tables AS
 SELECT table_id,
    table_name,
    base_type
   FROM ( VALUES (1,'tbl_analysis_boolean_values'::text,'boolean'::text), (2,'tbl_analysis_categorical_values'::text,'category'::text), (3,'tbl_analysis_dating_ranges'::text,'dating_range'::text), (4,'tbl_analysis_identifiers'::text,'identifier'::text), (5,'tbl_analysis_integer_ranges'::text,'integer_range'::text), (6,'tbl_analysis_integer_values'::text,'integer'::text), (7,'tbl_analysis_notes'::text,'note'::text), (8,'tbl_analysis_numerical_ranges'::text,'decimal_range'::text), (9,'tbl_analysis_numerical_values'::text,'decimal'::text), (10,'tbl_analysis_taxon_counts'::text,'taxon_count'::text), (11,'tbl_analysis_value_dimensions'::text,'dimension'::text)) t(table_id, table_name, base_type);


ALTER VIEW public.view_typed_analysis_tables OWNER TO sead_master;

--
-- Name: view_typed_analysis_values; Type: VIEW; Schema: public; Owner: sead_master
--

CREATE VIEW public.view_typed_analysis_values AS
 SELECT 1 AS table_id,
    tbl_analysis_boolean_values.analysis_value_id
   FROM public.tbl_analysis_boolean_values
UNION
 SELECT 2 AS table_id,
    tbl_analysis_categorical_values.analysis_value_id
   FROM public.tbl_analysis_categorical_values
UNION
 SELECT 3 AS table_id,
    tbl_analysis_dating_ranges.analysis_value_id
   FROM public.tbl_analysis_dating_ranges
UNION
 SELECT 4 AS table_id,
    tbl_analysis_identifiers.analysis_value_id
   FROM public.tbl_analysis_identifiers
UNION
 SELECT 5 AS table_id,
    tbl_analysis_integer_ranges.analysis_value_id
   FROM public.tbl_analysis_integer_ranges
UNION
 SELECT 6 AS table_id,
    tbl_analysis_integer_values.analysis_value_id
   FROM public.tbl_analysis_integer_values
UNION
 SELECT 7 AS table_id,
    tbl_analysis_notes.analysis_value_id
   FROM public.tbl_analysis_notes
UNION
 SELECT 8 AS table_id,
    tbl_analysis_numerical_ranges.analysis_value_id
   FROM public.tbl_analysis_numerical_ranges
UNION
 SELECT 9 AS table_id,
    tbl_analysis_numerical_values.analysis_value_id
   FROM public.tbl_analysis_numerical_values
UNION
 SELECT 10 AS table_id,
    tbl_analysis_taxon_counts.analysis_value_id
   FROM public.tbl_analysis_taxon_counts
UNION
 SELECT 11 AS table_id,
    tbl_analysis_value_dimensions.analysis_value_id
   FROM public.tbl_analysis_value_dimensions;


ALTER VIEW public.view_typed_analysis_values OWNER TO sead_master;

--
-- Name: typed_analysis_values; Type: VIEW; Schema: public; Owner: sead_master
--

CREATE VIEW public.typed_analysis_values AS
 SELECT view_typed_analysis_values.analysis_value_id,
    view_typed_analysis_tables.table_name,
    view_typed_analysis_tables.base_type
   FROM (public.view_typed_analysis_values
     JOIN public.view_typed_analysis_tables USING (table_id));


ALTER VIEW public.typed_analysis_values OWNER TO sead_master;

--
-- Name: view_bibliography_references; Type: VIEW; Schema: public; Owner: sead_master
--

CREATE VIEW public.view_bibliography_references AS
 SELECT e.dataset_uuid AS uuid,
    b.biblio_uuid
   FROM (public.tbl_datasets e
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.rdb_system_uuid AS uuid,
    b.biblio_uuid
   FROM (public.tbl_rdb_systems e
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.sample_group_uuid AS uuid,
    b.biblio_uuid
   FROM ((public.tbl_sample_group_references r
     JOIN public.tbl_sample_groups e USING (sample_group_id))
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.relative_age_uuid AS uuid,
    b.biblio_uuid
   FROM ((public.tbl_relative_age_refs r
     JOIN public.tbl_relative_ages e USING (relative_age_id))
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.taxonomy_notes_uuid AS uuid,
    b.biblio_uuid
   FROM (public.tbl_taxonomy_notes e
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.species_association_uuid AS uuid,
    b.biblio_uuid
   FROM (public.tbl_species_associations e
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.distribution_uuid AS uuid,
    b.biblio_uuid
   FROM (public.tbl_text_distribution e
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.tephra_uuid AS uuid,
    b.biblio_uuid
   FROM ((public.tbl_tephra_refs r
     JOIN public.tbl_tephras e USING (tephra_id))
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.ecocode_system_uuid AS uuid,
    b.biblio_uuid
   FROM (public.tbl_ecocode_systems e
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.master_set_uuid AS uuid,
    b.biblio_uuid
   FROM (public.tbl_dataset_masters e
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.site_other_records_uuid AS uuid,
    b.biblio_uuid
   FROM (public.tbl_site_other_records e
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.key_uuid AS uuid,
    b.biblio_uuid
   FROM (public.tbl_text_identification_keys e
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.geochron_uuid AS uuid,
    b.biblio_uuid
   FROM ((public.tbl_geochron_refs r
     JOIN public.tbl_geochronology e USING (geochron_id))
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.site_uuid AS uuid,
    b.biblio_uuid
   FROM ((public.tbl_site_references r
     JOIN public.tbl_sites e USING (site_id))
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.synonym_uuid AS uuid,
    b.biblio_uuid
   FROM (public.tbl_taxa_synonyms e
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.biology_uuid AS uuid,
    b.biblio_uuid
   FROM (public.tbl_text_biology e
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.aggregate_dataset_uuid AS uuid,
    b.biblio_uuid
   FROM (public.tbl_aggregate_datasets e
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.taxonomic_order_system_uuid AS uuid,
    b.biblio_uuid
   FROM ((public.tbl_taxonomic_order_biblio r
     JOIN public.tbl_taxonomic_order_systems e USING (taxonomic_order_system_id))
     JOIN public.tbl_biblio b USING (biblio_id))
UNION
 SELECT e.method_uuid AS uuid,
    b.biblio_uuid
   FROM (public.tbl_methods e
     JOIN public.tbl_biblio b USING (biblio_id));


ALTER VIEW public.view_bibliography_references OWNER TO sead_master;

--
-- Name: view_occurrence_ids; Type: VIEW; Schema: public; Owner: rebecka
--

CREATE VIEW public.view_occurrence_ids AS
 SELECT concat('SEAD:', 'BUGS:', tbl_sites.site_id, ':', tbl_abundances.abundance_id) AS "occurrenceID",
    tbl_abundances.abundance_id,
        CASE
            WHEN ((tbl_sample_group_sampling_contexts.sampling_context)::text = ANY ((ARRAY['Other modern'::character varying, 'Pitfall traps'::character varying])::text[])) THEN 'HumanObservation'::character varying
            WHEN ((tbl_sample_group_sampling_contexts.sampling_context)::text = ANY ((ARRAY['Stratigraphic sequence'::character varying, 'Archaeological site'::character varying, 'Other palaeo'::character varying])::text[])) THEN 'FossilSpecimen'::character varying
            ELSE tbl_sample_group_sampling_contexts.sampling_context
        END AS "basisOfRecord"
   FROM (((((((public.tbl_abundances
     JOIN public.tbl_taxa_tree_master ON ((tbl_abundances.taxon_id = tbl_taxa_tree_master.taxon_id)))
     JOIN public.tbl_analysis_entities ON ((tbl_analysis_entities.analysis_entity_id = tbl_abundances.analysis_entity_id)))
     JOIN public.tbl_datasets ON ((tbl_analysis_entities.dataset_id = tbl_datasets.dataset_id)))
     JOIN public.tbl_physical_samples ON ((tbl_physical_samples.physical_sample_id = tbl_analysis_entities.physical_sample_id)))
     JOIN public.tbl_sample_groups ON ((tbl_physical_samples.sample_group_id = tbl_sample_groups.sample_group_id)))
     JOIN public.tbl_sample_group_sampling_contexts ON ((tbl_sample_groups.sampling_context_id = tbl_sample_group_sampling_contexts.sampling_context_id)))
     JOIN public.tbl_sites ON ((tbl_sample_groups.site_id = tbl_sites.site_id)))
  WHERE (tbl_datasets.master_set_id = 1);


ALTER VIEW public.view_occurrence_ids OWNER TO rebecka;

--
-- Name: view_physical_abundances; Type: VIEW; Schema: public; Owner: rebecka
--

CREATE VIEW public.view_physical_abundances AS
 SELECT tps.physical_sample_id,
    ta.abundance_id
   FROM (((public.tbl_abundances ta
     JOIN public.tbl_analysis_entities tae ON ((ta.analysis_entity_id = tae.analysis_entity_id)))
     JOIN public.tbl_datasets ON ((tae.dataset_id = tbl_datasets.dataset_id)))
     JOIN public.tbl_physical_samples tps ON ((tae.physical_sample_id = tps.physical_sample_id)))
  WHERE (tbl_datasets.master_set_id = 1);


ALTER VIEW public.view_physical_abundances OWNER TO rebecka;

--
-- Name: view_with_times; Type: VIEW; Schema: public; Owner: rebecka
--

CREATE VIEW public.view_with_times AS
 SELECT tbl_analysis_entity_ages.age_older,
    tbl_analysis_entity_ages.age_younger,
    tbl_physical_samples.physical_sample_id,
    tbl_analysis_entity_ages.date_updated
   FROM (((public.tbl_datasets
     JOIN public.tbl_analysis_entities USING (dataset_id))
     JOIN public.tbl_physical_samples USING (physical_sample_id))
     JOIN public.tbl_analysis_entity_ages USING (analysis_entity_id))
  WHERE (tbl_datasets.master_set_id = 1);


ALTER VIEW public.view_with_times OWNER TO rebecka;

--
-- Name: view_chronometric_ages; Type: VIEW; Schema: public; Owner: rebecka
--

CREATE VIEW public.view_chronometric_ages AS
 SELECT (vt.age_younger)::integer AS "latestChronometricAge",
    (vt.age_older)::integer AS "earliestChronometricAge",
    voi."occurrenceID",
    voi."basisOfRecord",
    'BP'::text AS "earliestChronometricAgeReferenceSystem",
    'BP'::text AS "latestChronometricAgeReferenceSystem"
   FROM ((public.view_physical_abundances pa
     LEFT JOIN public.view_with_times vt ON ((pa.physical_sample_id = vt.physical_sample_id)))
     JOIN public.view_occurrence_ids voi ON ((pa.abundance_id = voi.abundance_id)))
  GROUP BY ((vt.age_younger)::integer), ((vt.age_older)::integer), voi."occurrenceID", 'BP'::text, 'BP'::text, voi."basisOfRecord";


ALTER VIEW public.view_chronometric_ages OWNER TO rebecka;

--
-- Name: view_identified_by; Type: VIEW; Schema: public; Owner: rebecka
--

CREATE VIEW public.view_identified_by AS
 SELECT tbl_abundances.abundance_id,
    COALESCE(string_agg((
        CASE
            WHEN (tbl_dataset_contacts.contact_type_id = 1) THEN tbl_contacts.last_name
            ELSE NULL::character varying
        END)::text, ' | '::text), 'unknown'::text) AS "identifiedBy"
   FROM ((((public.tbl_abundances
     JOIN public.tbl_analysis_entities ON ((tbl_abundances.analysis_entity_id = tbl_analysis_entities.analysis_entity_id)))
     JOIN public.tbl_datasets ON ((tbl_analysis_entities.dataset_id = tbl_datasets.dataset_id)))
     LEFT JOIN public.tbl_dataset_contacts ON ((tbl_dataset_contacts.dataset_id = tbl_datasets.dataset_id)))
     LEFT JOIN public.tbl_contacts ON ((tbl_dataset_contacts.contact_id = tbl_contacts.contact_id)))
  WHERE (tbl_datasets.master_set_id = 1)
  GROUP BY tbl_abundances.abundance_id;


ALTER VIEW public.view_identified_by OWNER TO rebecka;

--
-- Name: view_physical_ages; Type: VIEW; Schema: public; Owner: rebecka
--

CREATE VIEW public.view_physical_ages AS
 SELECT tbl_analysis_entity_ages.age_older,
    tbl_analysis_entity_ages.age_younger,
    tbl_physical_samples.physical_sample_id,
    tbl_analysis_entity_ages.date_updated
   FROM (((public.tbl_datasets
     JOIN public.tbl_analysis_entities USING (dataset_id))
     JOIN public.tbl_physical_samples USING (physical_sample_id))
     JOIN public.tbl_analysis_entity_ages USING (analysis_entity_id))
  WHERE (tbl_datasets.master_set_id = 1);


ALTER VIEW public.view_physical_ages OWNER TO rebecka;

--
-- Name: view_taxa_alphabetically; Type: VIEW; Schema: public; Owner: sead_master
--

CREATE VIEW public.view_taxa_alphabetically AS
 SELECT o.order_id,
    o.order_name AS "order",
    f.family_id,
    f.family_name AS family,
    g.genus_id,
    g.genus_name AS genus,
    s.taxon_id,
    s.species,
    a.author_id,
    a.author_name AS author
   FROM ((((public.tbl_taxa_tree_master s
     JOIN public.tbl_taxa_tree_genera g ON ((s.genus_id = g.genus_id)))
     JOIN public.tbl_taxa_tree_families f ON ((g.family_id = f.family_id)))
     JOIN public.tbl_taxa_tree_orders o ON ((f.order_id = o.order_id)))
     LEFT JOIN public.tbl_taxa_tree_authors a ON ((s.author_id = a.author_id)))
  ORDER BY o.order_name, f.family_name, g.genus_name, s.species;


ALTER VIEW public.view_taxa_alphabetically OWNER TO sead_master;

--
-- Name: view_with_references; Type: VIEW; Schema: public; Owner: rebecka
--

CREATE VIEW public.view_with_references AS
 SELECT DISTINCT tbl_abundances.abundance_id,
    string_agg(
        CASE
            WHEN ((tbl_biblio.full_reference IS NOT NULL) AND (tbl_biblio.full_reference <> ''::text)) THEN tbl_biblio.full_reference
            ELSE (((COALESCE(tbl_biblio.authors, ''::character varying))::text || ' '::text) || (COALESCE(tbl_biblio.title, ''::character varying))::text)
        END, ' | '::text) AS "associatedReferences"
   FROM ((((((public.tbl_abundances
     JOIN public.tbl_analysis_entities ON ((tbl_abundances.analysis_entity_id = tbl_analysis_entities.analysis_entity_id)))
     JOIN public.tbl_physical_samples ON ((tbl_analysis_entities.physical_sample_id = tbl_physical_samples.physical_sample_id)))
     JOIN public.tbl_sample_groups ON ((tbl_sample_groups.sample_group_id = tbl_physical_samples.sample_group_id)))
     JOIN public.tbl_sites ON ((tbl_sites.site_id = tbl_sample_groups.site_id)))
     JOIN public.tbl_site_references ON ((tbl_site_references.site_id = tbl_sites.site_id)))
     JOIN public.tbl_biblio ON ((tbl_site_references.biblio_id = tbl_biblio.biblio_id)))
  WHERE (tbl_abundances.abundance_id IN ( SELECT view_occurrence_ids.abundance_id
           FROM public.view_occurrence_ids))
  GROUP BY tbl_abundances.abundance_id;


ALTER VIEW public.view_with_references OWNER TO rebecka;

--
-- Name: view_with_abundances; Type: VIEW; Schema: public; Owner: rebecka
--

CREATE VIEW public.view_with_abundances AS
 SELECT
        CASE
            WHEN ((tbl_data_types.data_type_name)::text = 'Presence'::text) THEN ''::text
            ELSE (tbl_abundances.abundance)::text
        END AS "organismQuantity",
    COALESCE((tbl_sites.latitude_dd)::text, 'unknown'::text) AS "decimalLatitude",
    COALESCE((tbl_sites.longitude_dd)::text, 'unknown'::text) AS "decimalLongitude",
    regexp_replace((tbl_sites.site_name)::text, '[\r\n]+'::text, ' '::text, 'g'::text) AS locality,
    regexp_replace(tbl_sites.site_description, '[\r\n]+'::text, ' '::text, 'g'::text) AS "occurrenceRemarks",
    COALESCE((tv.dyntaxa_taxon_id)::text, ''::text) AS "taxonID",
    COALESCE(tv."taxonRemarks", ''::text) AS "taxonRemarks",
    tv.genus_name AS genus,
    tv.family_name AS family,
    regexp_replace(tv."scientificName", '[\r\n]+'::text, ' '::text, 'g'::text) AS "scientificName",
    COALESCE(regexp_replace(idby."identifiedBy", '[\r\n]+'::text, ' '::text, 'g'::text), 'unknown'::text) AS "identifiedBy",
    COALESCE(regexp_replace(vr."associatedReferences", '[\r\n]+'::text, ' '::text, 'g'::text), 'unknown'::text) AS "associatedReferences",
    'WGS84'::text AS "geodeticDatum",
    'PhysicalObject'::text AS type,
    'en'::text AS language,
    'CC-BY 4.0'::text AS license,
    CURRENT_DATE AS modified,
    voi."occurrenceID",
    'Present'::text AS "occurrenceStatus",
        CASE
            WHEN ((tbl_dataset_masters.master_name)::text = 'Bugs database'::text) THEN 'Animalia'::text
            ELSE 'Not bugs data, check query for kingdom'::text
        END AS kingdom,
        CASE
            WHEN ((tbl_sample_group_sampling_contexts.sampling_context)::text = ANY ((ARRAY['Other modern'::character varying, 'Pitfall traps'::character varying])::text[])) THEN 'HumanObservation'::character varying
            WHEN ((tbl_sample_group_sampling_contexts.sampling_context)::text = ANY ((ARRAY['Stratigraphic sequence'::character varying, 'Archaeological site'::character varying, 'Other palaeo'::character varying])::text[])) THEN 'FossilSpecimen'::character varying
            ELSE tbl_sample_group_sampling_contexts.sampling_context
        END AS "basisOfRecord",
        CASE
            WHEN ((tv.species)::text = ANY ((ARRAY['sp'::character varying, 'sp.'::character varying, 'spp'::character varying, 'spp.'::character varying])::text[])) THEN 'genus'::text
            WHEN ((tv.species)::text = ANY ((ARRAY['indet'::character varying, 'indet.'::character varying])::text[])) THEN 'family'::text
            ELSE 'species'::text
        END AS "taxonRank",
        CASE
            WHEN ((tbl_data_types.data_type_name)::text = 'Presence'::text) THEN ''::character varying
            WHEN ((tbl_data_types.data_type_name)::text = 'Abundance'::text) THEN 'Individuals'::character varying
            WHEN ((tbl_data_types.data_type_name)::text = 'MNI'::text) THEN 'Individuals: MNI'::character varying
            WHEN ((tbl_data_types.data_type_name)::text = 'Partial abundance'::text) THEN 'Individuals: partial abundance'::character varying
            WHEN ((tbl_data_types.data_type_name)::text = 'Undefined other'::text) THEN 'Undefined'::character varying
            ELSE tbl_data_types.data_type_name
        END AS "organismQuantityType",
    tbl_locations.location_name AS country
   FROM (((((((((((((((public.tbl_abundances
     JOIN public.tbl_analysis_entities tae ON ((tbl_abundances.analysis_entity_id = tae.analysis_entity_id)))
     JOIN public.view_occurrence_ids voi ON ((tbl_abundances.abundance_id = voi.abundance_id)))
     JOIN public.tbl_datasets ON ((tae.dataset_id = tbl_datasets.dataset_id)))
     JOIN public.tbl_dataset_masters ON ((tbl_datasets.master_set_id = tbl_dataset_masters.master_set_id)))
     JOIN public.tbl_physical_samples ON ((tae.physical_sample_id = tbl_physical_samples.physical_sample_id)))
     JOIN public.tbl_sample_groups ON ((tbl_sample_groups.sample_group_id = tbl_physical_samples.sample_group_id)))
     JOIN public.tbl_sample_group_sampling_contexts ON ((tbl_sample_group_sampling_contexts.sampling_context_id = tbl_sample_groups.sampling_context_id)))
     JOIN public.tbl_sites ON ((tbl_sites.site_id = tbl_sample_groups.site_id)))
     JOIN public.taxon_view tv ON ((tbl_abundances.taxon_id = tv.taxon_id)))
     JOIN public.tbl_site_locations sl ON ((sl.site_id = tbl_sites.site_id)))
     JOIN public.tbl_locations ON ((sl.location_id = tbl_locations.location_id)))
     JOIN public.tbl_location_types ON ((tbl_location_types.location_type_id = tbl_locations.location_type_id)))
     JOIN public.tbl_data_types ON ((tbl_data_types.data_type_id = tbl_datasets.data_type_id)))
     JOIN public.view_identified_by idby ON ((idby.abundance_id = tbl_abundances.abundance_id)))
     LEFT JOIN public.view_with_references vr ON ((vr.abundance_id = tbl_abundances.abundance_id)))
  WHERE ((tbl_dataset_masters.master_set_id = 1) AND ((tbl_location_types.location_type)::text = 'Country'::text));


ALTER VIEW public.view_with_abundances OWNER TO rebecka;

--
-- PostgreSQL database dump complete
--

\unrestrict zcZmvcCVUGfK0HwZJeouYHwYICk2X9WxL6f7iZdTToRxlIbqNXbrChBmeLdUhBK

