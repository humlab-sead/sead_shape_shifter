<!-- converted from building_dendro_reduced.xlsx -->

## Sheet: data_table_index
| table_name | only_new_data | new_data |
| --- | --- | --- |
| tbl_sites | true | true |
| tbl_site_locations | true | true |
| tbl_site_references | true | true |
| tbl_sample_groups | true | true |
| tbl_sample_group_descriptions | true | true |
| tbl_sample_group_coordinates | true | true |
| tbl_sample_group_notes | true | true |
| tbl_physical_samples | true | true |
| tbl_sample_descriptions | true | true |
| tbl_sample_locations | true | true |
| tbl_sample_notes | true | true |
| tbl_sample_alt_refs | true | true |
| tbl_analysis_entities | true | true |
| tbl_dendro | true | true |
| tbl_dendro_dates | true | true |
| tbl_dendro_date_notes | true | true |
| tbl_datasets | true | true |
| tbl_dataset_contacts | true | true |
| tbl_dataset_submissions | true | true |
| tbl_projects | true | true |
| tbl_abundances | true | true |
## Sheet: tbl_sites
| system_id | site_preservation_status_id | site_name | site_description | national_site_identifier | latitude_dd | longitude_dd | altitude | date_updated | site_location_accuracy | site_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1635 |  | Fröjden |  |  | 58.0836551307243 | 16.4887472928153 |  |  |  |  |
## Sheet: tbl_site_locations
| system_id | site_location_id | site_id | location_id | date_updated |
| --- | --- | --- | --- | --- |
| 391 |  | 1635 | 781 |  |
| 392 |  | 1635 | 3737 |  |
| 393 |  | 1635 | 3760 |  |
| 394 |  | 1635 | 4820 |  |
| 395 |  | 1635 | 5064 |  |
| 396 |  | 1635 | 205 |  |
## Sheet: tbl_site_references
| system_id | site_id | biblio_id | date_updated | site_reference_id | Projektnr |
| --- | --- | --- | --- | --- | --- |
| 1 | 1635 | 352 |  |  |  |
## Sheet: tbl_sample_groups
| system_id | sample_group_id | sample_group_name | sample_group_description | site_id | method_id | sampling_context_id | date_updated | sample_group_id.1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 11952 |  | 75699A Fröjden |  | 1635 | 10 | 17 |  |  |
## Sheet: tbl_sample_group_descriptions
| system_id | group_description | sample_group_description_type_id | sample_group_id | date_updated | sample_group_description_id |
| --- | --- | --- | --- | --- | --- |
| 508 | Bostadshus | 62 | 11952 |  |  |
| 509 | Mangårdsbyggnad | 61 | 11952 |  |  |
| 510 | 1,5 Plan | 59 | 11952 |  |  |
| 511 | Trä, Liggtimmer | 58 | 11952 |  |  |
| 512 | Panel | 56 | 11952 |  |  |
| 513 | Sadeltak | 55 | 11952 |  |  |
| 514 | Takpannor | 54 | 11952 |  |  |
| 515 | Nybyggnad (1775) "Virket till den första byggperioden avverkades vinterhalvåret 1774/75." (Rapport 2005:31)  | 53 | 11952 |  |  |
## Sheet: tbl_sample_group_coordinates
| system_id | coordinate_method_dimension_id | position_accuracy | sample_group_id | sample_group_position | date_updated | sample_group_position_id | sample_group_name |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 143 | 2 | Precise | 143 | 57.5276850784344 |  |  | 12637A Abbotens hus |
## Sheet: tbl_sample_group_notes
| system_id | sample_group_id | note | date_updated | sample_group_note_id |
| --- | --- | --- | --- | --- |
| 1 | 11952 | Ladugården är riven men några stockar är bevarade |  |  |
## Sheet: tbl_physical_samples
| system_id | physical_sample_id | sample_group_id | alt_ref_type_id | sample_type_id | sample_name | date_sampled | date_updated |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 53971 |  | 11952 | 3 | 12 | 75699 | 2005-01-26 |  |
| 53972 |  | 11952 | 3 | 12 | 75800 | 2005-01-26 |  |
## Sheet: tbl_sample_descriptions
| system_id | sample_description_id | sample_description_type_id | physical_sample_id | description | date_updated |
| --- | --- | --- | --- | --- | --- |
| 3843 |  | 30 | 53971 | Liggande timmer |  |
| 3844 |  | 30 | 53972 | Liggande timmer |  |
## Sheet: tbl_sample_locations
| system_id | sample_location_type_id | physical_sample_id | location | date_updated | sample_location_id |
| --- | --- | --- | --- | --- | --- |
| 21427 | 72 | 53971 | Bottenvåning |  |  |
| 21428 | 73 | 53971 | Garderob |  |  |
| 21429 | 74 | 53971 | Vägg |  |  |
| 21430 | 75 | 53971 | Öster om norra murstocken |  |  |
| 21431 | 76 | 53971 | Innervägg |  |  |
| 21432 | 77 | 53971 | 4:e stockvarvet |  |  |
| 21433 | 72 | 53972 | 2 plan |  |  |
| 21434 | 73 | 53972 | Garderob |  |  |
| 21435 | 74 | 53972 | Vägg |  |  |
| 21436 | 75 | 53972 | Västra långväggen |  |  |
| 21437 | 76 | 53972 | 3 m från norra gaveln |  |  |
| 21438 | 77 | 53972 | 3:e stockvarvet uppifrån |  |  |
## Sheet: tbl_sample_notes
| system_id | physical_sample_id | note_type | note | date_updated | sample_note_id |
| --- | --- | --- | --- | --- | --- |
| 1 | 11952 |  | Samma träd som 10009 |  |  |
## Sheet: tbl_sample_alt_refs
| system_id | alt_ref | alt_ref_type_id | physical_sample_id | date_updated | sample_alt_ref_id |
| --- | --- | --- | --- | --- | --- |
| 2095 | 1 | 2 | 53971 |  |  |
| 2096 | 2 | 2 | 53972 |  |  |
## Sheet: tbl_analysis_entities
| system_id | dataset_id | physical_sample_id | date_updated | analysis_entity_id |
| --- | --- | --- | --- | --- |
| 4191 | 4191 | 53971 |  |  |
| 4192 | 4192 | 53972 |  |  |
| 9207 | 9207 | 53971 |  |  |
| 9208 | 9208 | 53972 |  |  |
| 14223 | 14223 | 53971 |  |  |
| 14224 | 14224 | 53972 |  |  |
| 19239 | 19239 | 53971 |  |  |
| 19240 | 19240 | 53972 |  |  |
| 24255 | 24255 | 53971 |  |  |
| 24256 | 24256 | 53972 |  |  |
| 29267 | 29267 | 53971 |  |  |
| 29268 | 29268 | 53972 |  |  |
## Sheet: tbl_dendro
| system_id | analysis_entity_id | dendro_lookup_id | measurement_value | date_updated | dendro_id |
| --- | --- | --- | --- | --- | --- |
| 4191 | 4191 | 121 | Tall |  |  |
| 4192 | 4192 | 121 | Tall |  |  |
| 26032 | 9207 | 125 | Nej |  |  |
| 26033 | 9207 | 126 | 36 |  |  |
| 26034 | 9207 | 127 | Nej |  |  |
| 26035 | 9207 | 128 | W |  |  |
| 26036 | 9207 | 129 | ~ 5 |  |  |
| 26037 | 9208 | 125 | Nej |  |  |
| 26038 | 9208 | 126 | 50 |  |  |
| 26039 | 9208 | 127 | Nej |  |  |
| 26040 | 9208 | 128 | W |  |  |
| 26041 | 9208 | 129 | ~ 3 |  |  |
| 36124 | 14223 | 122 | 49 |  |  |
| 36125 | 14224 | 122 | 102 |  |  |
| 41607 | 19239 | 124 | 2 |  |  |
| 41608 | 19240 | 124 | 2 |  |  |
| 59193 | 24255 | 130 | 60 |  |  |
| 59194 | 24255 | 131 | 80 |  |  |
| 59195 | 24255 | 132 | 1670 |  |  |
| 59196 | 24255 | 133 | 1710 |  |  |
| 59197 | 24256 | 130 | 110 |  |  |
| 59198 | 24256 | 131 | 130 |  |  |
| 59199 | 24256 | 132 | 1710 |  |  |
| 59200 | 24256 | 133 | 1750 |  |  |
## Sheet: tbl_dendro_dates
| system_id | age_older | age_younger | age_type_id | dating_uncertainty_id | season_id | analysis_entity_id | dendro_lookup_id | date_updated | dendro_date_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3072 | 1774 |  | 1 |  |  | 14223 | 137 |  |  |
| 3073 | 1865 |  | 1 |  |  | 14224 | 137 |  |  |
| 6734 | 1774 |  | 1 |  | 3 | 29267 | 134 |  |  |
| 6735 | 1865 |  | 1 |  | 3 | 29268 | 134 |  |  |
## Sheet: tbl_dendro_date_notes
| system_id | note | dendro_date_id | date_updated | dendro_date_note_id |
| --- | --- | --- | --- | --- |
| 1 | Fällningsåret omräknat med nuvarande splintstatistik för ek 17±7 | 3072 |  |  |
## Sheet: tbl_datasets
| system_id | biblio_id | data_type_id | dataset_name | master_set_id | method_id | project_id | updated_dataset_id | date_updated | dataset_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4191 | 129 | 19 | 75699 Categorical | 10 | 10 | 550 |  |  |  |
| 4192 | 129 | 19 | 75800 Categorical | 10 | 10 | 550 |  |  |  |
| 9207 | 129 | 6 | 75699 Presence | 10 | 10 | 550 |  |  |  |
| 9208 | 129 | 6 | 75800 Presence | 10 | 10 | 550 |  |  |  |
| 14223 | 129 | 15 | 75699 Counted dates | 10 | 10 | 550 |  |  |  |
| 14224 | 129 | 15 | 75800 Counted dates | 10 | 10 | 550 |  |  |  |
| 19239 | 129 | 5 | 75699 Abundance | 10 | 10 | 550 |  |  |  |
| 19240 | 129 | 5 | 75800 Abundance | 10 | 10 | 550 |  |  |  |
| 24255 | 129 | 43 | 75699 Estimated Years | 10 | 10 | 550 |  |  |  |
| 24256 | 129 | 43 | 75800 Estimated Years | 10 | 10 | 550 |  |  |  |
| 29267 | 129 | 44 | 75699 Composite Dates | 10 | 10 | 550 |  |  |  |
| 29268 | 129 | 44 | 75800 Composite Dates | 10 | 10 | 550 |  |  |  |
## Sheet: tbl_dataset_contacts
| system_id | contact_id | contact_type_id | dataset_id | date_updated | dataset_contact_id |
| --- | --- | --- | --- | --- | --- |
| 4191 | 56 | 2 | 4191 |  |  |
| 4192 | 56 | 2 | 4192 |  |  |
| 9207 | 56 | 2 | 9207 |  |  |
| 9208 | 56 | 2 | 9208 |  |  |
| 14223 | 56 | 2 | 14223 |  |  |
| 14224 | 56 | 2 | 14224 |  |  |
| 19239 | 56 | 2 | 19239 |  |  |
| 19240 | 56 | 2 | 19240 |  |  |
| 24255 | 56 | 2 | 24255 |  |  |
| 24256 | 56 | 2 | 24256 |  |  |
| 29267 | 56 | 2 | 29267 |  |  |
| 29268 | 56 | 2 | 29268 |  |  |
## Sheet: tbl_dataset_submissions
| system_id | contact_id | dataset_id | date_submitted | date_updated | notes | submission_type_id | dataset_submission_id |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 12188 | 65 | 4191 | 2005-01-26 00:00:00 |  |  | 10 |  |
| 12189 | 34 | 4191 | 2020-06-30 00:00:00 |  |  | 3 |  |
| 12190 | 67 | 4191 | 2023-12-19 00:00:00 |  |  | 5 |  |
| 12191 | 65 | 4192 | 2005-01-26 00:00:00 |  |  | 10 |  |
| 12192 | 34 | 4192 | 2020-06-30 00:00:00 |  |  | 3 |  |
| 12193 | 67 | 4192 | 2023-12-19 00:00:00 |  |  | 5 |  |
| 26715 | 65 | 9207 | 2005-01-26 00:00:00 |  |  | 10 |  |
| 26716 | 34 | 9207 | 2020-06-30 00:00:00 |  |  | 3 |  |
| 26717 | 67 | 9207 | 2023-12-19 00:00:00 |  |  | 5 |  |
| 26718 | 65 | 9208 | 2005-01-26 00:00:00 |  |  | 10 |  |
| 26719 | 34 | 9208 | 2020-06-30 00:00:00 |  |  | 3 |  |
| 26720 | 67 | 9208 | 2023-12-19 00:00:00 |  |  | 5 |  |
| 41242 | 65 | 14223 | 2005-01-26 00:00:00 |  |  | 10 |  |
| 41243 | 34 | 14223 | 2020-06-30 00:00:00 |  |  | 3 |  |
| 41244 | 67 | 14223 | 2023-12-19 00:00:00 |  |  | 5 |  |
| 41245 | 65 | 14224 | 2005-01-26 00:00:00 |  |  | 10 |  |
| 41246 | 34 | 14224 | 2020-06-30 00:00:00 |  |  | 3 |  |
| 41247 | 67 | 14224 | 2023-12-19 00:00:00 |  |  | 5 |  |
| 55769 | 65 | 19239 | 2005-01-26 00:00:00 |  |  | 10 |  |
| 55770 | 34 | 19239 | 2020-06-30 00:00:00 |  |  | 3 |  |
| 55771 | 67 | 19239 | 2023-12-19 00:00:00 |  |  | 5 |  |
| 55772 | 65 | 19240 | 2005-01-26 00:00:00 |  |  | 10 |  |
| 55773 | 34 | 19240 | 2020-06-30 00:00:00 |  |  | 3 |  |
| 55774 | 67 | 19240 | 2023-12-19 00:00:00 |  |  | 5 |  |
| 70296 | 65 | 24255 | 2005-01-26 00:00:00 |  |  | 10 |  |
| 70297 | 34 | 24255 | 2020-06-30 00:00:00 |  |  | 3 |  |
| 70298 | 67 | 24255 | 2023-12-19 00:00:00 |  |  | 5 |  |
| 70299 | 65 | 24256 | 2005-01-26 00:00:00 |  |  | 10 |  |
| 70300 | 34 | 24256 | 2020-06-30 00:00:00 |  |  | 3 |  |
| 70301 | 67 | 24256 | 2023-12-19 00:00:00 |  |  | 5 |  |
| 84811 | 65 | 29267 | 2005-01-26 00:00:00 |  |  | 10 |  |
| 84812 | 34 | 29267 | 2020-06-30 00:00:00 |  |  | 3 |  |
| 84813 | 67 | 29267 | 2023-12-19 00:00:00 |  |  | 5 |  |
| 84814 | 65 | 29268 | 2005-01-26 00:00:00 |  |  | 10 |  |
| 84815 | 34 | 29268 | 2020-06-30 00:00:00 |  |  | 3 |  |
| 84816 | 67 | 29268 | 2023-12-19 00:00:00 |  |  | 5 |  |
## Sheet: tbl_projects
| system_id | project_type_id | project_stage_id | project_name | project_abbrev_name | description | date_updated | project_id |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 550 | 8 | 6 | 75699 Fröjden |  | CONTRACTOR: Fastighetsägaren SAMPLING REASON: Byggnadsundersökning DESCRIPTION: Att få klarhet i byggnadens ålder och tillkomst |  |  |
## Sheet: tbl_abundances
| system_id | taxon_id | analysis_entity_id | abundance_element_id | abundance | date_updated | abundance_id |
| --- | --- | --- | --- | --- | --- | --- |
| 3930 | 18197 | 4191 | 44 | 1 |  |  |
| 3931 | 18197 | 4192 | 44 | 1 |  |  |