# ProjectService

> God node · 247 connections · `backend/app/services/project_service.py`

**Community:** [[Community 11]]

## Connections by Relation

### calls
- [[get_project_service()]] `EXTRACTED`

### imports
- [[projects.py]] `EXTRACTED`
- [[data-sources.ts]] `EXTRACTED`
- [[__init__.py]] `EXTRACTED`
- [[entities.py]] `EXTRACTED`
- [[preview.py]] `EXTRACTED`
- [[materialization.ts]] `EXTRACTED`
- [[service.py]] `EXTRACTED`
- [[validation.py]] `EXTRACTED`
- [[query.py]] `EXTRACTED`
- [[resolvers.py]] `EXTRACTED`
- [[validate_fk_service.py]] `EXTRACTED`
- [[caches.py]] `EXTRACTED`
- [[mapping_manager.py]] `EXTRACTED`
- [[columns.py]] `EXTRACTED`
- [[directives.py]] `EXTRACTED`

### method
- [[.__init__()]] `EXTRACTED`
- [[.load_project()]] `EXTRACTED`
- [[.save_project()]] `EXTRACTED`
- [[._resolve_project_file_path()]] `EXTRACTED`
- [[.list_projects()]] `EXTRACTED`
- [[.save_with_version_check()]] `EXTRACTED`
- [[.activate_project()]] `EXTRACTED`
- [[.add_entity()]] `EXTRACTED`
- [[.create_project()]] `EXTRACTED`
- [[.get_entity()]] `EXTRACTED`
- [[._invalidate_all_caches()]] `EXTRACTED`
- [[.save_data_source_file()]] `EXTRACTED`
- [[.save_entity_boundary()]] `EXTRACTED`
- [[.save_metadata_boundary()]] `EXTRACTED`
- [[.save_options_boundary()]] `EXTRACTED`
- [[.save_project_file()]] `EXTRACTED`
- [[._serialize_entity()]] `EXTRACTED`
- [[.update_entity()]] `EXTRACTED`
- [[._verify_save()]] `EXTRACTED`
- [[.add_entity_by_name()]] `EXTRACTED`

### rationale_for
- [[Service for managing project files and entities.      Thread safety:         All]] `EXTRACTED`

### references
- [[get_project_service()]] `EXTRACTED`

### uses
- [[Project]] `INFERRED`
- [[project_mapper.py]] `INFERRED`
- [[.target_model()]] `INFERRED`
- [[project_name_mapper.py]] `INFERRED`
- [[YamlService]] `INFERRED`
- [[ShapeShiftService]] `INFERRED`
- [[ValidationService]] `INFERRED`
- [[TaskListSidecarManager]] `INFERRED`
- [[ResourceNotFoundError]] `INFERRED`
- [[ProjectMetadata]] `INFERRED`
- [[ValidationResult]] `INFERRED`
- [[ProjectFileInfo]] `INFERRED`
- [[task_service.py]] `INFERRED`
- [[entity_values_service.py]] `INFERRED`
- [[data_validation_orchestrator.py]] `INFERRED`
- [[ResourceConflictError]] `INFERRED`
- [[materialization_service.py]] `INFERRED`
- [[auto_fix_service.py]] `INFERRED`
- [[shapeshift_service.py]] `INFERRED`
- [[ApplicationStateManager]] `INFERRED`

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*