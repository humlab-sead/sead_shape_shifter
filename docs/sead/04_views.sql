create view public.master_set_reference as
select distinct
    tbl_abundances.abundance_id,
    string_agg(
        case
            when
                ((tbl_biblio.full_reference is not null) and (tbl_biblio.full_reference <> ''::text))
                then tbl_biblio.full_reference
            else (
                ((coalesce(tbl_biblio.authors, ''::character varying))::text || ' '::text)
                || (coalesce(tbl_biblio.title, ''::character varying))::text
            )
        end, ' | '::text
    ) as "associatedReferences"
from ((((
    public.tbl_abundances
    join
        public.tbl_analysis_entities
        on ((tbl_abundances.analysis_entity_id = tbl_analysis_entities.analysis_entity_id))
)
join public.tbl_datasets on ((tbl_datasets.dataset_id = tbl_analysis_entities.dataset_id))
)
join public.tbl_dataset_masters on ((tbl_dataset_masters.master_set_id = tbl_datasets.master_set_id))
)
join public.tbl_biblio on ((tbl_dataset_masters.biblio_id = tbl_biblio.biblio_id))
)
group by tbl_abundances.abundance_id;


alter view public.master_set_reference owner to rebecka;

--
-- Name: taxon_view; Type: VIEW; Schema: public; Owner: rebecka
--

create view public.taxon_view as
select distinct
    tbl_taxa_tree_master.taxon_id,
    tbl_taxa_tree_master.species,
    tbl_taxa_tree_genera.genus_name,
    tbl_taxa_tree_families.family_name,
    case
        when
            (
                (
                    (tbl_taxa_tree_master.species)::text
                    <> all((array['sp.'::character varying, 'spp.'::character varying])::text [])
                )
                and ((tbl_taxa_tree_master.species)::text !~~ '% sp.%'::text)
                and ((tbl_taxa_tree_master.species)::text !~~ '% spp.%'::text)
            )
            then (tbl_taxonomic_order.taxonomic_code)::integer
        else null::integer
    end as dyntaxa_taxon_id,
    case
        when
            (
                (tbl_taxonomic_order.taxonomic_code is not null)
                and (
                    (tbl_taxa_tree_master.species)::text
                    <> all((array['sp.'::character varying, 'spp.'::character varying])::text [])
                )
                and ((tbl_taxa_tree_master.species)::text !~~ '% sp.%'::text)
                and ((tbl_taxa_tree_master.species)::text !~~ '% spp.%'::text)
            )
            then 'Dyntaxa taxon id'::text
        else ''::text
    end as "taxonRemarks",
    concat(
        tbl_taxa_tree_genera.genus_name, ' ', tbl_taxa_tree_master.species, ' ',
        case
            when
                (
                    (tbl_taxa_tree_authors.author_name is not null)
                    and ((tbl_taxa_tree_authors.author_name)::text !~~ '%(%'::text)
                )
                then (concat(' (', tbl_taxa_tree_authors.author_name, ')'))::character varying
            else coalesce(tbl_taxa_tree_authors.author_name, ''::character varying)
        end
    ) as "scientificName"
from (((((
    public.tbl_taxa_tree_master
    left join public.tbl_taxa_tree_authors on ((tbl_taxa_tree_master.author_id = tbl_taxa_tree_authors.author_id))
)
join public.tbl_taxa_tree_genera on ((tbl_taxa_tree_master.genus_id = tbl_taxa_tree_genera.genus_id))
)
join public.tbl_taxa_tree_families on ((tbl_taxa_tree_genera.family_id = tbl_taxa_tree_families.family_id))
)
join public.tbl_taxa_tree_orders on ((tbl_taxa_tree_families.order_id = tbl_taxa_tree_orders.order_id))
)
left join
    public.tbl_taxonomic_order
    on (
        (
            (tbl_taxonomic_order.taxon_id = tbl_taxa_tree_master.taxon_id)
            and (tbl_taxonomic_order.taxonomic_order_system_id = 2)
        )
    )
)
where (tbl_taxa_tree_orders.record_type_id = 1);


alter view public.taxon_view owner to rebecka;

--
-- Name: view_typed_analysis_tables; Type: VIEW; Schema: public; Owner: sead_master
--

create view public.view_typed_analysis_tables as
select
    table_id,
    table_name,
    base_type
from
    (values (1, 'tbl_analysis_boolean_values'::text, 'boolean'::text), (2, 'tbl_analysis_categorical_values'::text, 'category'::text), (3, 'tbl_analysis_dating_ranges'::text, 'dating_range'::text), (4, 'tbl_analysis_identifiers'::text, 'identifier'::text), (5, 'tbl_analysis_integer_ranges'::text, 'integer_range'::text), (6, 'tbl_analysis_integer_values'::text, 'integer'::text), (7, 'tbl_analysis_notes'::text, 'note'::text), (8, 'tbl_analysis_numerical_ranges'::text, 'decimal_range'::text), (9, 'tbl_analysis_numerical_values'::text, 'decimal'::text), (10, 'tbl_analysis_taxon_counts'::text, 'taxon_count'::text), (11, 'tbl_analysis_value_dimensions'::text, 'dimension'::text)) t (table_id, table_name, base_type);


alter view public.view_typed_analysis_tables owner to sead_master;

--
-- Name: view_typed_analysis_values; Type: VIEW; Schema: public; Owner: sead_master
--

create view public.view_typed_analysis_values as
select
    1 as table_id,
    tbl_analysis_boolean_values.analysis_value_id
from public.tbl_analysis_boolean_values
union
select
    2 as table_id,
    tbl_analysis_categorical_values.analysis_value_id
from public.tbl_analysis_categorical_values
union
select
    3 as table_id,
    tbl_analysis_dating_ranges.analysis_value_id
from public.tbl_analysis_dating_ranges
union
select
    4 as table_id,
    tbl_analysis_identifiers.analysis_value_id
from public.tbl_analysis_identifiers
union
select
    5 as table_id,
    tbl_analysis_integer_ranges.analysis_value_id
from public.tbl_analysis_integer_ranges
union
select
    6 as table_id,
    tbl_analysis_integer_values.analysis_value_id
from public.tbl_analysis_integer_values
union
select
    7 as table_id,
    tbl_analysis_notes.analysis_value_id
from public.tbl_analysis_notes
union
select
    8 as table_id,
    tbl_analysis_numerical_ranges.analysis_value_id
from public.tbl_analysis_numerical_ranges
union
select
    9 as table_id,
    tbl_analysis_numerical_values.analysis_value_id
from public.tbl_analysis_numerical_values
union
select
    10 as table_id,
    tbl_analysis_taxon_counts.analysis_value_id
from public.tbl_analysis_taxon_counts
union
select
    11 as table_id,
    tbl_analysis_value_dimensions.analysis_value_id
from public.tbl_analysis_value_dimensions;


alter view public.view_typed_analysis_values owner to sead_master;

--
-- Name: typed_analysis_values; Type: VIEW; Schema: public; Owner: sead_master
--

create view public.typed_analysis_values as
select
    view_typed_analysis_values.analysis_value_id,
    view_typed_analysis_tables.table_name,
    view_typed_analysis_tables.base_type
from (
    public.view_typed_analysis_values
    join public.view_typed_analysis_tables using (table_id)
);


alter view public.typed_analysis_values owner to sead_master;

--
-- Name: view_bibliography_references; Type: VIEW; Schema: public; Owner: sead_master
--

create view public.view_bibliography_references as
select
    e.dataset_uuid as uuid,
    b.biblio_uuid
from (
    public.tbl_datasets e
    join public.tbl_biblio b using (biblio_id)
)
union
select
    e.rdb_system_uuid as uuid,
    b.biblio_uuid
from (
    public.tbl_rdb_systems e
    join public.tbl_biblio b using (biblio_id)
)
union
select
    e.sample_group_uuid as uuid,
    b.biblio_uuid
from ((
    public.tbl_sample_group_references r
    join public.tbl_sample_groups e using (sample_group_id)
)
join public.tbl_biblio b using (biblio_id)
)
union
select
    e.relative_age_uuid as uuid,
    b.biblio_uuid
from ((
    public.tbl_relative_age_refs r
    join public.tbl_relative_ages e using (relative_age_id)
)
join public.tbl_biblio b using (biblio_id)
)
union
select
    e.taxonomy_notes_uuid as uuid,
    b.biblio_uuid
from (
    public.tbl_taxonomy_notes e
    join public.tbl_biblio b using (biblio_id)
)
union
select
    e.species_association_uuid as uuid,
    b.biblio_uuid
from (
    public.tbl_species_associations e
    join public.tbl_biblio b using (biblio_id)
)
union
select
    e.distribution_uuid as uuid,
    b.biblio_uuid
from (
    public.tbl_text_distribution e
    join public.tbl_biblio b using (biblio_id)
)
union
select
    e.tephra_uuid as uuid,
    b.biblio_uuid
from ((
    public.tbl_tephra_refs r
    join public.tbl_tephras e using (tephra_id)
)
join public.tbl_biblio b using (biblio_id)
)
union
select
    e.ecocode_system_uuid as uuid,
    b.biblio_uuid
from (
    public.tbl_ecocode_systems e
    join public.tbl_biblio b using (biblio_id)
)
union
select
    e.master_set_uuid as uuid,
    b.biblio_uuid
from (
    public.tbl_dataset_masters e
    join public.tbl_biblio b using (biblio_id)
)
union
select
    e.site_other_records_uuid as uuid,
    b.biblio_uuid
from (
    public.tbl_site_other_records e
    join public.tbl_biblio b using (biblio_id)
)
union
select
    e.key_uuid as uuid,
    b.biblio_uuid
from (
    public.tbl_text_identification_keys e
    join public.tbl_biblio b using (biblio_id)
)
union
select
    e.geochron_uuid as uuid,
    b.biblio_uuid
from ((
    public.tbl_geochron_refs r
    join public.tbl_geochronology e using (geochron_id)
)
join public.tbl_biblio b using (biblio_id)
)
union
select
    e.site_uuid as uuid,
    b.biblio_uuid
from ((
    public.tbl_site_references r
    join public.tbl_sites e using (site_id)
)
join public.tbl_biblio b using (biblio_id)
)
union
select
    e.synonym_uuid as uuid,
    b.biblio_uuid
from (
    public.tbl_taxa_synonyms e
    join public.tbl_biblio b using (biblio_id)
)
union
select
    e.biology_uuid as uuid,
    b.biblio_uuid
from (
    public.tbl_text_biology e
    join public.tbl_biblio b using (biblio_id)
)
union
select
    e.aggregate_dataset_uuid as uuid,
    b.biblio_uuid
from (
    public.tbl_aggregate_datasets e
    join public.tbl_biblio b using (biblio_id)
)
union
select
    e.taxonomic_order_system_uuid as uuid,
    b.biblio_uuid
from ((
    public.tbl_taxonomic_order_biblio r
    join public.tbl_taxonomic_order_systems e using (taxonomic_order_system_id)
)
join public.tbl_biblio b using (biblio_id)
)
union
select
    e.method_uuid as uuid,
    b.biblio_uuid
from (
    public.tbl_methods e
    join public.tbl_biblio b using (biblio_id)
);


alter view public.view_bibliography_references owner to sead_master;

--
-- Name: view_occurrence_ids; Type: VIEW; Schema: public; Owner: rebecka
--

create view public.view_occurrence_ids as
select
    concat('SEAD:', 'BUGS:', tbl_sites.site_id, ':', tbl_abundances.abundance_id) as "occurrenceID",
    tbl_abundances.abundance_id,
    case
        when
            (
                (tbl_sample_group_sampling_contexts.sampling_context)::text
                = any((array['Other modern'::character varying, 'Pitfall traps'::character varying])::text [])
            )
            then 'HumanObservation'::character varying
        when
            (
                (tbl_sample_group_sampling_contexts.sampling_context)::text
                = any(
                    (
                        array[
                            'Stratigraphic sequence'::character varying,
                            'Archaeological site'::character varying,
                            'Other palaeo'::character varying
                        ]
                    )::text []
                )
            )
            then 'FossilSpecimen'::character varying
        else tbl_sample_group_sampling_contexts.sampling_context
    end as "basisOfRecord"
from (((((((
    public.tbl_abundances
    join public.tbl_taxa_tree_master on ((tbl_abundances.taxon_id = tbl_taxa_tree_master.taxon_id))
)
join public.tbl_analysis_entities on ((tbl_analysis_entities.analysis_entity_id = tbl_abundances.analysis_entity_id))
)
join public.tbl_datasets on ((tbl_analysis_entities.dataset_id = tbl_datasets.dataset_id))
)
join
    public.tbl_physical_samples
    on ((tbl_physical_samples.physical_sample_id = tbl_analysis_entities.physical_sample_id))
)
join public.tbl_sample_groups on ((tbl_physical_samples.sample_group_id = tbl_sample_groups.sample_group_id))
)
join
    public.tbl_sample_group_sampling_contexts
    on ((tbl_sample_groups.sampling_context_id = tbl_sample_group_sampling_contexts.sampling_context_id))
)
join public.tbl_sites on ((tbl_sample_groups.site_id = tbl_sites.site_id))
)
where (tbl_datasets.master_set_id = 1);


alter view public.view_occurrence_ids owner to rebecka;

--
-- Name: view_physical_abundances; Type: VIEW; Schema: public; Owner: rebecka
--

create view public.view_physical_abundances as
select
    tps.physical_sample_id,
    ta.abundance_id
from (((
    public.tbl_abundances ta
    join public.tbl_analysis_entities tae on ((ta.analysis_entity_id = tae.analysis_entity_id))
)
join public.tbl_datasets on ((tae.dataset_id = tbl_datasets.dataset_id))
)
join public.tbl_physical_samples tps on ((tae.physical_sample_id = tps.physical_sample_id))
)
where (tbl_datasets.master_set_id = 1);


alter view public.view_physical_abundances owner to rebecka;

--
-- Name: view_with_times; Type: VIEW; Schema: public; Owner: rebecka
--

create view public.view_with_times as
select
    tbl_analysis_entity_ages.age_older,
    tbl_analysis_entity_ages.age_younger,
    tbl_physical_samples.physical_sample_id,
    tbl_analysis_entity_ages.date_updated
from (((
    public.tbl_datasets
    join public.tbl_analysis_entities using (dataset_id)
)
join public.tbl_physical_samples using (physical_sample_id))
join public.tbl_analysis_entity_ages using (analysis_entity_id))
where (tbl_datasets.master_set_id = 1);


alter view public.view_with_times owner to rebecka;

--
-- Name: view_chronometric_ages; Type: VIEW; Schema: public; Owner: rebecka
--

create view public.view_chronometric_ages as
select
    (vt.age_younger)::integer as "latestChronometricAge",
    (vt.age_older)::integer as "earliestChronometricAge",
    voi."occurrenceID",
    voi."basisOfRecord",
    'BP'::text as "earliestChronometricAgeReferenceSystem",
    'BP'::text as "latestChronometricAgeReferenceSystem"
from ((
    public.view_physical_abundances pa
    left join public.view_with_times vt on ((pa.physical_sample_id = vt.physical_sample_id))
)
join public.view_occurrence_ids voi on ((pa.abundance_id = voi.abundance_id))
)
group by
    ((vt.age_younger)::integer), ((vt.age_older)::integer), voi."occurrenceID", 'BP'::text, 'BP'::text, voi."basisOfRecord";


alter view public.view_chronometric_ages owner to rebecka;

--
-- Name: view_identified_by; Type: VIEW; Schema: public; Owner: rebecka
--

create view public.view_identified_by as
select
    tbl_abundances.abundance_id,
    coalesce(string_agg((
        case
            when (tbl_dataset_contacts.contact_type_id = 1) then tbl_contacts.last_name
            else null::character varying
        end
    )::text, ' | '::text), 'unknown'::text) as "identifiedBy"
from ((((
    public.tbl_abundances
    join
        public.tbl_analysis_entities
        on ((tbl_abundances.analysis_entity_id = tbl_analysis_entities.analysis_entity_id))
)
join public.tbl_datasets on ((tbl_analysis_entities.dataset_id = tbl_datasets.dataset_id))
)
left join public.tbl_dataset_contacts on ((tbl_dataset_contacts.dataset_id = tbl_datasets.dataset_id))
)
left join public.tbl_contacts on ((tbl_dataset_contacts.contact_id = tbl_contacts.contact_id))
)
where (tbl_datasets.master_set_id = 1)
group by tbl_abundances.abundance_id;


alter view public.view_identified_by owner to rebecka;

--
-- Name: view_physical_ages; Type: VIEW; Schema: public; Owner: rebecka
--

create view public.view_physical_ages as
select
    tbl_analysis_entity_ages.age_older,
    tbl_analysis_entity_ages.age_younger,
    tbl_physical_samples.physical_sample_id,
    tbl_analysis_entity_ages.date_updated
from (((
    public.tbl_datasets
    join public.tbl_analysis_entities using (dataset_id)
)
join public.tbl_physical_samples using (physical_sample_id))
join public.tbl_analysis_entity_ages using (analysis_entity_id))
where (tbl_datasets.master_set_id = 1);


alter view public.view_physical_ages owner to rebecka;

--
-- Name: view_taxa_alphabetically; Type: VIEW; Schema: public; Owner: sead_master
--

create view public.view_taxa_alphabetically as
select
    o.order_id,
    o.order_name as "order",
    f.family_id,
    f.family_name as family,
    g.genus_id,
    g.genus_name as genus,
    s.taxon_id,
    s.species,
    a.author_id,
    a.author_name as author
from ((((
    public.tbl_taxa_tree_master s
    join public.tbl_taxa_tree_genera g on ((s.genus_id = g.genus_id))
)
join public.tbl_taxa_tree_families f on ((g.family_id = f.family_id))
)
join public.tbl_taxa_tree_orders o on ((f.order_id = o.order_id))
)
left join public.tbl_taxa_tree_authors a on ((s.author_id = a.author_id))
)
order by o.order_name, f.family_name, g.genus_name, s.species;


alter view public.view_taxa_alphabetically owner to sead_master;

--
-- Name: view_with_references; Type: VIEW; Schema: public; Owner: rebecka
--

create view public.view_with_references as
select distinct
    tbl_abundances.abundance_id,
    string_agg(
        case
            when
                ((tbl_biblio.full_reference is not null) and (tbl_biblio.full_reference <> ''::text))
                then tbl_biblio.full_reference
            else (
                ((coalesce(tbl_biblio.authors, ''::character varying))::text || ' '::text)
                || (coalesce(tbl_biblio.title, ''::character varying))::text
            )
        end, ' | '::text
    ) as "associatedReferences"
from ((((((
    public.tbl_abundances
    join
        public.tbl_analysis_entities
        on ((tbl_abundances.analysis_entity_id = tbl_analysis_entities.analysis_entity_id))
)
join
    public.tbl_physical_samples
    on ((tbl_analysis_entities.physical_sample_id = tbl_physical_samples.physical_sample_id))
)
join public.tbl_sample_groups on ((tbl_sample_groups.sample_group_id = tbl_physical_samples.sample_group_id))
)
join public.tbl_sites on ((tbl_sites.site_id = tbl_sample_groups.site_id))
)
join public.tbl_site_references on ((tbl_site_references.site_id = tbl_sites.site_id))
)
join public.tbl_biblio on ((tbl_site_references.biblio_id = tbl_biblio.biblio_id))
)
where (tbl_abundances.abundance_id in (
    select view_occurrence_ids.abundance_id
    from public.view_occurrence_ids
))
group by tbl_abundances.abundance_id;


alter view public.view_with_references owner to rebecka;

--
-- Name: view_with_abundances; Type: VIEW; Schema: public; Owner: rebecka
--

create view public.view_with_abundances as
select
    case
        when ((tbl_data_types.data_type_name)::text = 'Presence'::text) then ''::text
        else (tbl_abundances.abundance)::text
    end as "organismQuantity",
    coalesce((tbl_sites.latitude_dd)::text, 'unknown'::text) as "decimalLatitude",
    coalesce((tbl_sites.longitude_dd)::text, 'unknown'::text) as "decimalLongitude",
    regexp_replace((tbl_sites.site_name)::text, '[\r\n]+'::text, ' '::text, 'g'::text) as locality,
    regexp_replace(tbl_sites.site_description, '[\r\n]+'::text, ' '::text, 'g'::text) as "occurrenceRemarks",
    coalesce((tv.dyntaxa_taxon_id)::text, ''::text) as "taxonID",
    coalesce(tv."taxonRemarks", ''::text) as "taxonRemarks",
    tv.genus_name as genus,
    tv.family_name as family,
    regexp_replace(tv."scientificName", '[\r\n]+'::text, ' '::text, 'g'::text) as "scientificName",
    coalesce(regexp_replace(idby."identifiedBy", '[\r\n]+'::text, ' '::text, 'g'::text), 'unknown'::text)
        as "identifiedBy",
    coalesce(regexp_replace(vr."associatedReferences", '[\r\n]+'::text, ' '::text, 'g'::text), 'unknown'::text)
        as "associatedReferences",
    'WGS84'::text as "geodeticDatum",
    'PhysicalObject'::text as type,
    'en'::text as language,
    'CC-BY 4.0'::text as license,
    current_date as modified,
    voi."occurrenceID",
    'Present'::text as "occurrenceStatus",
    case
        when ((tbl_dataset_masters.master_name)::text = 'Bugs database'::text) then 'Animalia'::text
        else 'Not bugs data, check query for kingdom'::text
    end as kingdom,
    case
        when
            (
                (tbl_sample_group_sampling_contexts.sampling_context)::text
                = any((array['Other modern'::character varying, 'Pitfall traps'::character varying])::text [])
            )
            then 'HumanObservation'::character varying
        when
            (
                (tbl_sample_group_sampling_contexts.sampling_context)::text
                = any(
                    (
                        array[
                            'Stratigraphic sequence'::character varying,
                            'Archaeological site'::character varying,
                            'Other palaeo'::character varying
                        ]
                    )::text []
                )
            )
            then 'FossilSpecimen'::character varying
        else tbl_sample_group_sampling_contexts.sampling_context
    end as "basisOfRecord",
    case
        when
            (
                (tv.species)::text
                = any(
                    (
                        array[
                            'sp'::character varying,
                            'sp.'::character varying,
                            'spp'::character varying,
                            'spp.'::character varying
                        ]
                    )::text []
                )
            )
            then 'genus'::text
        when
            ((tv.species)::text = any((array['indet'::character varying, 'indet.'::character varying])::text []))
            then 'family'::text
        else 'species'::text
    end as "taxonRank",
    case
        when ((tbl_data_types.data_type_name)::text = 'Presence'::text) then ''::character varying
        when ((tbl_data_types.data_type_name)::text = 'Abundance'::text) then 'Individuals'::character varying
        when ((tbl_data_types.data_type_name)::text = 'MNI'::text) then 'Individuals: MNI'::character varying
        when
            ((tbl_data_types.data_type_name)::text = 'Partial abundance'::text)
            then 'Individuals: partial abundance'::character varying
        when ((tbl_data_types.data_type_name)::text = 'Undefined other'::text) then 'Undefined'::character varying
        else tbl_data_types.data_type_name
    end as "organismQuantityType",
    tbl_locations.location_name as country
from (((((((((((((((
    public.tbl_abundances
    join public.tbl_analysis_entities tae on ((tbl_abundances.analysis_entity_id = tae.analysis_entity_id))
)
join public.view_occurrence_ids voi on ((tbl_abundances.abundance_id = voi.abundance_id))
)
join public.tbl_datasets on ((tae.dataset_id = tbl_datasets.dataset_id))
)
join public.tbl_dataset_masters on ((tbl_datasets.master_set_id = tbl_dataset_masters.master_set_id))
)
join public.tbl_physical_samples on ((tae.physical_sample_id = tbl_physical_samples.physical_sample_id))
)
join public.tbl_sample_groups on ((tbl_sample_groups.sample_group_id = tbl_physical_samples.sample_group_id))
)
join
    public.tbl_sample_group_sampling_contexts
    on ((tbl_sample_group_sampling_contexts.sampling_context_id = tbl_sample_groups.sampling_context_id))
)
join public.tbl_sites on ((tbl_sites.site_id = tbl_sample_groups.site_id))
)
join public.taxon_view tv on ((tbl_abundances.taxon_id = tv.taxon_id))
)
join public.tbl_site_locations sl on ((sl.site_id = tbl_sites.site_id))
)
join public.tbl_locations on ((sl.location_id = tbl_locations.location_id))
)
join public.tbl_location_types on ((tbl_location_types.location_type_id = tbl_locations.location_type_id))
)
join public.tbl_data_types on ((tbl_data_types.data_type_id = tbl_datasets.data_type_id))
)
join public.view_identified_by idby on ((idby.abundance_id = tbl_abundances.abundance_id))
)
left join public.view_with_references vr on ((vr.abundance_id = tbl_abundances.abundance_id))
)
where ((tbl_dataset_masters.master_set_id = 1) and ((tbl_location_types.location_type)::text = 'Country'::text));


alter view public.view_with_abundances owner to rebecka;

--
-- PostgreSQL database dump complete
--

\unrestrict zcZmvcCVUGfK0HwZJeouYHwYICk2X9WxL6f7iZdTToRxlIbqNXbrChBmeLdUhBK
