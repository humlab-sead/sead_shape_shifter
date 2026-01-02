
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
 - [x] FIXME: #83 Project editor: No Edit YAML visible (not implemented)
 - [] FIXME: #84 FK Editor: "RUN TEST" reports ShapeShiftProject source must be a ShapeShiftProject instance or a valid project file path
 - [] FIXME: #82 In FK editor, constraints cannot be added/changed.
 - [] FIXME: #85 In entity editor, data source should be a dropdown, not free text
 - [] FIXME:
### Tech debts:

 - [x] FIXME: Improve test coverage (+85%)
 - [ ] FIXME: #59 [Frontend] Create frontend (manual) testing guide 
 - [ ] FIXME: Add automatic import of all data loaders (__init__.py)
 - [ ] FIXME: Test Faker or mimesis for data generation in normalization tests

### New features

 - [] TODO: [Frontend/Backend] Edit data source configuration in a dual-mode editor (Form/YAML).
 - [] TODO: #21 Add UX for mapping/reconciling remote/target entities to local entities.
 - [] TODO: Add additional frontend/backend options (e.g., themes, temp directory, logging level, etc.)
 - [] TODO: Add capability to generate a default reconciliation YAML based on service manifest received from calling services /reconcile endpoint.
 - [] TODO: Change so that only entities avaliable for service reconciliation are displayed  
 - [] TODO: #56 Add capability to export preview
 - [] TODO: #72 Add capability to run full normalization from frontend, and save output to selected dispatch target.
 - [] TODO: #68 Add a "finally" step.
 - [] TODO: #66 Introduce a "transformations" section.
 - [] TODO: #69 Add "parent" property to entity definitions.
 - [] TODO: #67 Introduce support for string concatenation in "extra_columns".
 - [x] TODO: #65 Add the capability to edit a configuration's metadata section.
 - [x] TODO: #70 Add capability to load data from Excel files.
 - [] TODO: #74 Rename "Configuration" to "Project" throughout the application.
 - [] TODO: Add capability to duplicate an existing configuration.
 - [] TODO: #57 Add capability to set number of rows (including all) from preview
 - [] TODO: #75 Add capability to select number of rows from preview.
 - [x] TODO: #77 Change graph visualization to use Cytoscape.js instead of basic SVG.
 - [x] TODO: #80 [Frontend/Backend] Edit entire project YAML file in dual-mode editor (Form/YAML).
 - [ ] TODO: Publish frontend files via the backend (FastAPI) server for easier deployment.
