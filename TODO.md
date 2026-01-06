
# Finally cleanup step

### Bugs

 - [] FIXME: When opening YAML view in entity editor, an empty entity is displayed
 - [] FIXME: Saving a configuration stores the YAML in a file with a new filename
 - [] FIXME: Right preview pane doesn't clear values between entities
 - [] FIXME: Keys is a mandatory field, but many entities has no value in Keys
 - [x] FIXME: #81 Opening entity editor from dependency graph fails.
 - [] FIXME: Active route only highlighted in navigation breadcrumbs for "Projects"
 - [] FIXME: Entity count: description not shown for project cards in "Projects"
 - [] FIXME: Search projects:  Fails: "No results" message for no matches
 - [] FIXME: Create project: No description field in create dialog
 - [] FIXME: New prodject's name is displayed as "test_config_manua", missing last character, correct inside project's metadata
 - [ ] FIXME: #93 Auto-accept threshold in recon view is disabled.

### Tech debts:

 - [x] FIXME: Improve test coverage (+85%)
 - [x] FIXME: #59 [Frontend] Create frontend (manual) testing guide 
 - [ ] FIXME: #88 Add automatic import of all data loaders (__init__.py)
 - [ ] FIXME: #89 Test Faker or mimesis for data generation in normalization tests

### New features

 - [] TODO: [Frontend/Backend] Edit data source configuration in a dual-mode editor (Form/YAML).
 - [] TODO: #21 Add UX for mapping/reconciling remote/target entities to local entities.
 - [] TODO: Add additional frontend/backend options (e.g., themes, temp directory, logging level, etc.)
 - [] TODO: Add capability to generate a default reconciliation YAML based on service manifest received from calling services /reconcile endpoint.
 - [] TODO: Change so that only entities avaliable for service reconciliation are displayed  
 - [] TODO: #56 Add capability to export preview
 - [x] TODO: #72 Add capability to run full normalization from frontend, and save output to selected dispatch target.
 - [] TODO: #68 Add a "finally" step.
 - [] TODO: #66 Introduce a "transformations" section.
 - [] TODO: #69 Add "parent" property to entity definitions.
 - [] TODO: #67 Introduce support for string concatenation in "extra_columns".
 - [x] TODO: #65 Add the capability to edit a configuration's metadata section.
 - [x] TODO: #70 Add capability to load data from Excel files.
 - [x] TODO: #74 Rename "Configuration" to "Project" throughout the application.
 - [] TODO: Add capability to duplicate an existing configuration.
 - [x] TODO: #57 Add capability to set number of rows (including all) from preview
 - [x] TODO: #75 Add capability to select number of rows from preview.
 - [x] TODO: #77 Change graph visualization to use Cytoscape.js instead of basic SVG.
 - [x] TODO: #80 [Frontend/Backend] Edit entire project YAML file in dual-mode editor (Form/YAML).
 - [ ] TODO: Publish frontend files via the backend (FastAPI) server for easier deployment.
 - [x] TODO: #92 Add status endpoint (backend) and indicator (UX) for reconciliation service health check.
 - [x] TODO: #94 Add reconciliation CLI script
 - [ ] TODO: #95 Display data lineage/source information in dependency graph
 - [ ] TODO: #98 Enable entity to have multiple reconciliation specifications.
 - [ ] TODO: #99 Add capability to edit a project's reconciliation specifications.

We need to change the format of the reconciliation file, since the entity's name is currently the key to a single reconciliation specification. We need to allow an entity to have several specifications targeting other columns.
The "keys" in the current specification format is effectively the reconciliation target column. Currently I see no use case for having several keys in a single specification, so we will change the format to have a single "target-field" instead of "keys", and thus allow several specifications per entity. Furthermore, I see no use for the "columns" field so we can remove that field.

Please do an review of this proposed change and provide feedback if you see any issues with this approach, and create an implementation plan for this change.

Old/existing structure:
```YAML
entities:
   entity_name:
      ...a single recon specification including a "keys" field
```
New YAML:
```YAML
entities:
   entity_name:
       target-field:   # previous "keys" field, but singular
          ...specification without "keys" fiield...
```

Next use case is to fully implement is the capability to edit a projects reconciliation specification. Currently we can edit the  "auto_accept_threshold" and "review_threshold" on an entity specification, but we need to be able to edit the other values as well.This capabilities belongs to the "Setup/Configuration" section of the reconciliation view. 

I can see that we need to be able to add/delete entity specifications, and for each specification we need to be able to edit all fields except the "entity" and "mapping" sections. The "entity" is selected when adding a new specification.

I can see the following requirements:
- We should be able to see all combined entity specifications for the entire project.
- Each row in the list represents a single entity specification (i.e., an entity + target-field combination).
- We should be able to select an entity specification to edit its values.
- When adding a new entity specification, we should be able to select the entity and the target-field.
- When adding a new entity specification, the target-field options should be determined by the entity's available fields.
- When adding a new entity specification, we should not be able to select an entity + target-field combination that already exists in another specification.
- When editing an existing entity specification, we should not be able to change the entity or target-field.
- When editing an existing entity specification, we should be able to edit all other fields except "entity" and "mapping".
- When saving an entity specification, the values should be validated according to the reconciliation service API specification.
- When saving an entity specification, the updated project reconciliation YAML should be persisted to disk.
- The list of entity specifications should indicate the reconciliation status (e.g., as per the persisted status in the YAML file).
- The name of an entity specification must be an existing entity in the project.
- User can add, delete, update and save the recon specifications.
- When deleting an entity specification, a confirmation dialog should be shown (warning if it has mappings!).
- The remote types that can be assigned to a specification should be determined by calls to the reconciliation service API.
- For an existing specification, if the remote type no longer an  exists in the reconciliation service, then the specification should be flagged (no longer possible to run auto-reconcile).
- The "mapping" section in an entity specification should be "passthrough" in the CRUD operations  since it is handled by the subsequent reconciliation workflow 
- The avaliable properties in the "property" mappings section should be detemined by call to the reconciliation service. 
- Since the properties are shown in input fields, we no longer need the specification details section.

This change will achieve the capability to fully manage a project's reconciliation specifications from the frontend UX. The reconciliation workflow will be geared towards a project focused approach rather than individual entity specifications.

Please do an review of this proposed change and provide feedback if you see any issues with this approach, and create an implementation plan for this change.


I need to clarify the requirements. The reconciliation workflow doesn't need to know which target database, table and column the mapping belongs to. We are asking the OpenRefine service "Hey, I have a site named Uppsala, please give me it's ID.", and the service returns ID 1234. What we need to do then is to store this mapping (when accepted) between "Uppsala" and "1234". One of the final steps in the full shapeshifting workflow is to assign the mapped value "1234" to all rows having "site_name" equal to Uppsala entities in the (normalized/shapeshifted) "site" data (which is a Pandas DataFrame). This is done by LinkToRemoteService in link_to_remote. The dispatch will then store this information in the target format CSV or Excel. We do need to have enough information in the entity reconciliation specification to do this mapping.
So we need to store the following information in the entity reconciliation specification:
- The entity name (e.g. "site")
- The target field (e.g. "site_name") which is the label we asked the ID for
- The property fields that we can enrich our reconciliation queries with (e.g. "country", "region", etc)
The field in the entity's output data that we will store the reconciled ID in will **always** be the field named by the "surrogate_id" key in the entity specification. That is a mandatory field in the project's entity specifications. This field is the "public ID field" of the entity. In the output data, after reconciliation, we will have a value in that field for all mapped items. The other items are considered new items. N.B. within the output dataset, a "system_id" is maintained as the project scoped primary key. 

So the mapping in essence is "Uppsala" (from target field "site_name")  -> "1234" (to surrogate_id field "site_id"). The other property fields are only used to improve the quality of the reconciliation queries.
Thus, we do not need to store the target database, table and column in the entity reconciliation specification. The "surrogate_id" field in the entity specification is sufficient to determine where to store the reconciled IDs.


Please review this list of rules that a project file must obey. The rules are implemented in specifications.py. Please suggest improvments to the rules, and identify any potential issues. Please also suggest any additional rules that should be implemented to improve the robustness of the project file validation.
