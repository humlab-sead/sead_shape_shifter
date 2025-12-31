# Migration Plan: Configuration → Project Terminology

## Overview
This document outlines the step-by-step plan to rename "configuration" to "project" throughout the Shape Shifter codebase to avoid confusion with the generic application configuration framework.

**Date:** December 31, 2025  
**Branch:** `rename-to-project-copilot`  
**Status:** Planning Phase

---

## Terminology Changes

### Primary Renamings
| Old Term | New Term | Context |
|----------|----------|---------|
| Configuration | Project | Main shape shifting setup |
| ConfigMetadata | ProjectMetadata | Project metadata model |
| ShapeShiftProject | ShapeShiftProject | Core configuration class |
| ConfigurationService | ProjectService | Backend service class |
| entity configuration | entity | Simplified terminology |
| data source configuration | data source | Simplified terminology |

### Preserved Terms
| Term | Reason |
|------|--------|
| `src/configuration/` | Generic application configuration framework (distinct from projects) |
| `ConfigStore` | Part of generic configuration framework |
| `Config`, `ConfigFactory`, `ConfigLike` | Generic configuration framework interfaces |

---

## Phase 1: Core Module Changes

### 1.1 Rename Core Model Class
**File:** `src/model.py`

**Changes:**
- [ ] Rename `class ShapeShiftProject` → `class ShapeShiftProject`
- [ ] Update all docstrings mentioning "configuration" to "project"
- [ ] Keep `cfg` parameter names (internal implementation detail)
- [ ] Update method names if they reference "config" (e.g., `get_config_version` → `get_project_version`)

**Impact:** ~100+ usages in tests and core modules

---

### 1.2 Update Core Imports and References
**Files to update:**
- [ ] `src/normalizer.py` - Update `ShapeShiftProject` imports and usages
- [ ] `src/extract.py` - Update references
- [ ] `src/filter.py` - Update references
- [ ] `src/link.py` - Update references
- [ ] `src/unnest.py` - Update references
- [ ] `src/mapping.py` - Update references
- [ ] `src/constraints.py` - Update docstrings mentioning "configuration"
- [ ] `src/specifications.py` - Update validation messages and docstrings
- [ ] `src/utility.py` - Update helper function docstrings

**Note:** Keep `src/configuration/` module untouched (generic framework)

---

## Phase 2: Backend API Changes

### 2.1 Rename API Models
**File:** `backend/app/models/config.py` → `backend/app/models/project.py`

**Changes:**
- [ ] Rename file: `config.py` → `project.py`
- [ ] `class ConfigMetadata` → `class ProjectMetadata`
  - Update field descriptions
  - Update docstring
- [ ] `class Configuration` → `class Project`
  - Update field descriptions
  - Update method docstrings
- [ ] Update all imports in other files to `from backend.app.models.project import Project, ProjectMetadata`

**Files importing from config.py:**
- [ ] `backend/app/api/v1/endpoints/configurations.py`
- [ ] `backend/app/services/project_service.py`
- [ ] `backend/app/services/validation_service.py`
- [ ] `backend/app/services/shapeshift_service.py`
- [ ] `backend/app/services/yaml_service.py`
- [ ] `backend/app/mappers/*`
- [ ] `backend/tests/*`

---

### 2.2 Rename Configuration Service
**File:** `backend/app/services/project_service.py` → `backend/app/services/project_service.py`

**Changes:**
- [ ] Rename file
- [ ] `class ConfigurationService` → `class ProjectService`
- [ ] `get_config_service()` → `get_project_service()`
- [ ] Update all method docstrings
- [ ] Update error messages to use "project" terminology
- [ ] Update log messages

**Methods to review:**
- `list_configurations()` → `list_projects()`
- `get_project()` → `get_project()`
- `create_project()` → `create_project()`
- `update_configuration()` → `update_project()`
- `delete_project()` → `delete_project()`
- `rename_configuration()` → `rename_project()`
- `get_configuration_metadata()` → `get_project_metadata()`
- `update_configuration_metadata()` → `update_project_metadata()`
- `list_backups()` → (keep as-is)
- `create_backup()` → (keep as-is)
- `restore_backup()` → (keep as-is)

---

### 2.3 Rename API Endpoints
**File:** `backend/app/api/v1/endpoints/configurations.py` → `backend/app/api/v1/endpoints/projects.py`

**Changes:**
- [ ] Rename file
- [ ] Update router prefix in registration: `/configurations` → `/projects`
- [ ] Update all route decorators:
  - `@router.get("/")` - List all projects
  - `@router.post("/")` - Create project
  - `@router.get("/{name}")` - Get project
  - `@router.put("/{name}")` - Update project
  - `@router.delete("/{name}")` - Delete project
  - `@router.post("/{name}/rename")` - Rename project
  - `@router.put("/{name}/metadata")` - Update project metadata
  - etc.
- [ ] Rename request/response models:
  - `ConfigurationCreateRequest` → `ProjectCreateRequest`
  - `ConfigurationUpdateRequest` → `ProjectUpdateRequest`
  - `ConfigurationResponse` → `ProjectResponse` (if exists)
- [ ] Update all docstrings and comments
- [ ] Update parameter descriptions
- [ ] Update error messages

**File:** `backend/app/api/v1/api.py`
- [ ] Update import: `from backend.app.api.v1.endpoints import projects`
- [ ] Update router inclusion: `api_router.include_router(projects.router, prefix="/projects", tags=["projects"])`

---

### 2.4 Update Other Backend Services
**Files to update:**

**`backend/app/services/validation_service.py`:**
- [ ] Update imports from `project_service` → `project_service`
- [ ] Update method parameter names: `project_name` → `project_name`
- [ ] Update docstrings and error messages
- [ ] Update log messages

**`backend/app/services/shapeshift_service.py`:**
- [ ] Update imports: `ShapeShiftProject` → `ShapeShiftProject`
- [ ] Update cache metadata to use "project" terminology
- [ ] Update parameter names: `project_name` → `project_name`
- [ ] Update docstrings

**`backend/app/services/yaml_service.py`:**
- [ ] Update parameter names
- [ ] Update docstrings

**`backend/app/services/auto_fix_service.py`:**
- [ ] Update parameter names and docstrings

**`backend/app/services/dependency_service.py`:**
- [ ] Update parameter names and docstrings

**`backend/app/services/reconciliation_service.py`:**
- [ ] Update parameter names: `project_name` → `project_name`

**`backend/app/services/test_run_service.py`:**
- [ ] Update parameter names and docstrings

---

### 2.5 Update Backend Mappers
**Files to update:**

**`backend/app/mappers/data_source_mapper.py`:**
- [ ] Update docstring: "data source configuration" → "data source"
- [ ] Update comments

**All other mappers in `backend/app/mappers/`:**
- [ ] Review and update terminology in docstrings

---

### 2.6 Update Backend Validators
**Files in `backend/app/validators/`:**
- [ ] Review and update error messages
- [ ] Update docstrings mentioning "configuration"

---

## Phase 3: Frontend Changes

### 3.1 Rename Frontend Types
**File:** `frontend/src/types/index.ts` (or wherever types are defined)

**Changes:**
- [ ] `interface Configuration` → `interface Project`
- [ ] `interface ConfigMetadata` → `interface ProjectMetadata`
- [ ] Update all field descriptions
- [ ] Update JSDoc comments

**Files to search for type imports:**
- All `.ts` and `.vue` files importing these types

---

### 3.2 Rename Configuration Store
**File:** `frontend/src/stores/configuration.ts` → `frontend/src/stores/project.ts`

**Changes:**
- [ ] Rename file
- [ ] `defineStore('configuration', ...)` → `defineStore('project', ...)`
- [ ] `useConfigurationStore` → `useProjectStore`
- [ ] Rename state variables:
  - `configurations` → `projects`
  - `selectedConfig` → `selectedProject`
- [ ] Rename getters:
  - `currentConfigName` → `currentProjectName`
  - `sortedConfigurations` → `sortedProjects`
  - `configByName` → `projectByName`
- [ ] Rename actions:
  - `fetchConfigurations()` → `fetchProjects()`
  - `selectConfiguration()` → `selectProject()`
  - `createConfiguration()` → `createProject()`
  - `updateConfiguration()` → `updateProject()`
  - `deleteConfiguration()` → `deleteProject()`
  - `renameConfiguration()` → `renameProject()`
  - etc.
- [ ] Update all internal references
- [ ] Update comments and docstrings

**File:** `frontend/src/stores/index.ts`
- [ ] Update export: `export { useProjectStore } from './project'`

---

### 3.3 Rename API Client
**File:** `frontend/src/api/configurations.ts` → `frontend/src/api/projects.ts`

**Changes:**
- [ ] Rename file
- [ ] Update all endpoint paths: `/api/v1/configurations` → `/api/v1/projects`
- [ ] Rename request/response types:
  - `ConfigurationCreateRequest` → `ProjectCreateRequest`
  - `ConfigurationUpdateRequest` → `ProjectUpdateRequest`
- [ ] Update function names in API client (if named):
  - `listConfigurations()` → `listProjects()`
  - `getConfiguration()` → `getProject()`
  - etc.
- [ ] Update JSDoc comments

**File:** `frontend/src/api/index.ts`
- [ ] Update import and export: `import * as projects from './projects'`
- [ ] Update API object: `export const api = { projects, ... }`

---

### 3.4 Update Vue Components
**Search pattern:** Files importing `useConfigurationStore` or `Configuration` type

**Files likely to update:**
- [ ] `frontend/src/views/*` - All view components
- [ ] `frontend/src/components/*` - All components using configuration store
- [ ] Update prop names: `config` → `project` (where referring to main project)
- [ ] Update computed property names
- [ ] Update method names
- [ ] Update template variable names
- [ ] Update comments

**Specific components to check:**
- Configuration editor components
- Configuration list/selection components
- Entity editor components (update references to "entity configuration" → "entity")
- Data source components (update "data source configuration" → "data source")

---

### 3.5 Update Vue Router
**File:** `frontend/src/router/index.ts`

**Changes:**
- [ ] Update route paths if they include "configuration"
- [ ] Update route names: `configuration-*` → `project-*`
- [ ] Update route meta information
- [ ] Update breadcrumb text

---

### 3.6 Update Composables
**Files in `frontend/src/composables/`:**
- [ ] Review `useValidation.ts` - Update parameter names
- [ ] Review `useAutoFix.ts` - Update parameter names
- [ ] Review other composables referencing configuration store
- [ ] Update JSDoc comments

---

## Phase 4: Test Updates

### 4.1 Update Core Tests
**Directory:** `tests/`

**Files to update (search for `ShapeShiftProject` import):**
- [ ] `tests/test_append_processing.py`
- [ ] `tests/test_append_integration.py`
- [ ] `tests/test_config_model.py`
- [ ] `tests/test_constraints.py`
- [ ] `tests/test_link.py`
- [ ] `tests/test_mapping.py`
- [ ] `tests/test_utility.py`
- [ ] `tests/conftest.py`
- [ ] All other test files

**Changes per file:**
- [ ] Update imports: `ShapeShiftProject` → `ShapeShiftProject`
- [ ] Update class references
- [ ] Update test class names: `TestShapeShiftConfig` → `TestShapeShiftProject`
- [ ] Update docstrings
- [ ] Update assertion messages

---

### 4.2 Update Backend Tests
**Directory:** `backend/tests/`

**Files to update:**
- [ ] `backend/tests/api/v1/test_configurations.py` (rename to `test_projects.py`)
- [ ] `backend/tests/api/v1/test_validation.py` - Update endpoint paths
- [ ] `backend/tests/services/test_config_service.py` (rename to `test_project_service.py`)
- [ ] `backend/tests/services/test_validation_service.py`
- [ ] `backend/tests/services/test_shapeshift_service.py`
- [ ] All other test files referencing configuration

**Changes:**
- [ ] Update imports
- [ ] Update endpoint paths in test requests
- [ ] Update class names
- [ ] Update variable names
- [ ] Update mock objects
- [ ] Update assertion messages

---

### 4.3 Update Test Fixtures
**Files:**
- [ ] `tests/conftest.py`
- [ ] `backend/tests/conftest.py`

**Changes:**
- [ ] Update fixture names containing "config" → "project"
- [ ] Update fixture docstrings
- [ ] Update return types

---

## Phase 5: Directory and File Renames

### 5.1 Rename Root Directory
**Current:** `configurations/`  
**New:** `projects/`

**Steps:**
- [ ] Move all files: `mv configurations/ projects/`
- [ ] Update `.gitignore` if it references `configurations/`
- [ ] Update `backend/app/core/config.py` settings:
  - `CONFIG_DIR` or similar setting → `PROJECTS_DIR`
  - Update default paths
- [ ] Search codebase for hardcoded paths containing "configurations/"
- [ ] Update path references in:
  - Backend services (ConfigurationService)
  - Tests using configuration files
  - Documentation examples

---

### 5.2 Update Backup Directory References
**Current:** `backups/`

**Changes:**
- [ ] Keep directory name as `backups/` (clear enough)
- [ ] Update backup file naming if it includes "configuration"
- [ ] Review backup service logic

---

## Phase 6: Documentation Updates

### 6.1 Update Main Documentation
**Files to update:**

**`README.md`:**
- [ ] Update all references to "configuration" → "project"
- [ ] Update examples showing configuration files
- [ ] Update CLI examples
- [ ] Update directory structure diagram

**`.github/copilot-instructions.md`:**
- [ ] Update architectural overview
- [ ] Update terminology section
- [ ] Update code examples
- [ ] Update file paths
- [ ] Update model class names
- [ ] Update backend service names
- [ ] Update frontend store names
- [ ] Update API endpoint examples
- [ ] Update "Key Files" section
- [ ] Update "Recent Improvements" if referencing configuration

**`AGENTS.md`:**
- [ ] Update all terminology
- [ ] Update code examples
- [ ] Update file paths
- [ ] Update workflow commands

---

### 6.2 Update Technical Documentation
**Directory:** `docs/`

**Files to update:**

**`docs/CONFIGURATION_GUIDE.md`:**
- [ ] Rename to `docs/PROJECT_GUIDE.md`
- [ ] Update title and introduction
- [ ] Update "Entity Configuration" → "Entity" throughout
- [ ] Update "Data Source Configuration" → "Data Source" throughout
- [ ] Keep YAML examples clear (they're self-explanatory)
- [ ] Update all narrative text

**`docs/BACKEND_API.md`:**
- [ ] Update API endpoint paths: `/configurations` → `/projects`
- [ ] Update request/response model names
- [ ] Update parameter names
- [ ] Update examples

**`docs/DEVELOPER_GUIDE.md`:**
- [ ] Update architectural diagrams
- [ ] Update code examples
- [ ] Update imports
- [ ] Update class names
- [ ] Update method signatures
- [ ] Update file paths

**`docs/SYSTEM_DOCUMENTATION.md`:**
- [ ] Update architecture overview
- [ ] Update component descriptions
- [ ] Update data flow diagrams

**`docs/UI_ARCHITECTURE.md`:**
- [ ] Update component names
- [ ] Update store names
- [ ] Update API endpoint paths
- [ ] Update state management examples

**`docs/YAML_EDITOR_FEATURE.md`:**
- [ ] Update "entity configuration" → "entity"
- [ ] Update examples

**`docs/ENTITY_STATE_MANAGEMENT.md`:**
- [ ] Update "entity configuration" → "entity"
- [ ] Update API paths
- [ ] Update store references

**`docs/RECONCILIATION_SETUP_GUIDE.md`:**
- [ ] Update API endpoint paths: `/configurations/{project_name}` → `/projects/{project_name}`
- [ ] Update parameter names

**`docs/DRIVER_SCHEMA_REGISTRY.md`:**
- [ ] Update "data source configuration" → "data source"

**Other docs files:**
- [ ] `docs/STATE_MANAGEMENT_IMPLEMENTATION.md`
- [ ] `docs/SPLIT_PANE_IMPLEMENTATION.md`
- [ ] `docs/UI_REQUIREMENTS.md`
- [ ] `docs/USER_GUIDE.md`

---

### 6.3 Update Code Comments
**Scope:** Entire codebase

**Search patterns:**
- [ ] "configuration" (review context, update where referring to projects)
- [ ] "entity configuration" → "entity"
- [ ] "data source configuration" → "data source"
- [ ] "project_name" → "project_name" (in parameters/variables)

**Tools:**
- Use global search and replace with caution
- Review each match for context
- Skip false positives (e.g., "configuration framework", "database configuration")

---

## Phase 7: Configuration and Build Files

### 7.1 Update Backend Configuration
**File:** `backend/app/core/config.py`

**Changes:**
- [ ] Rename settings:
  - `CONFIG_DIR` → `PROJECTS_DIR`
  - Any other "config"-related settings
- [ ] Update descriptions
- [ ] Update default values

---

### 7.2 Update Environment Variables
**Files:**
- [ ] `.env.example`
- [ ] `.env.development`
- [ ] `.env.production`
- [ ] `docker-compose.yml`

**Changes:**
- [ ] Rename env vars: `CONFIG_DIR` → `PROJECTS_DIR`
- [ ] Update comments

---

### 7.3 Update Makefile
**File:** `Makefile`

**Changes:**
- [ ] Review targets for "config" references
- [ ] Update help text if needed

---

## Phase 8: Testing and Validation

### 8.1 Run Core Tests
```bash
uv run pytest tests/ -v
```
- [ ] Verify all tests pass
- [ ] Check for import errors
- [ ] Check for name errors

---

### 8.2 Run Backend Tests
```bash
PYTHONPATH=.:backend uv run pytest backend/tests/ -v
```
- [ ] Verify all tests pass
- [ ] Check API endpoint tests
- [ ] Check service tests

---

### 8.3 Run Backend Server
```bash
make backend-run
```
- [ ] Verify server starts without errors
- [ ] Test API endpoints manually:
  - `GET /api/v1/projects`
  - `POST /api/v1/projects`
  - `GET /api/v1/projects/{name}`
  - etc.
- [ ] Check API documentation (Swagger UI at `/docs`)

---

### 8.4 Build and Test Frontend
```bash
cd frontend
pnpm install
pnpm type-check
pnpm build
```
- [ ] Verify no TypeScript errors
- [ ] Verify build succeeds
- [ ] Run frontend dev server: `pnpm dev`
- [ ] Test UI manually:
  - Project list
  - Project creation
  - Project editing
  - Entity editing
  - Data source editing

---

### 8.5 Run Linting
```bash
make lint
```
- [ ] Fix any linting errors
- [ ] Run `make tidy` to format code

---

## Phase 9: Final Cleanup

### 9.1 Search for Remnants
**Search patterns to verify:**
- [ ] `ShapeShiftProject` (should only exist in this migration doc)
- [ ] `Configuration` class (should only exist in `src/configuration/` framework)
- [ ] `ConfigMetadata` (should be `ProjectMetadata`)
- [ ] `/api/v1/configurations` (should be `/api/v1/projects`)
- [ ] `useConfigurationStore` (should be `useProjectStore`)
- [ ] `configurations/` directory (should be `projects/`)
- [ ] "entity configuration" in prose (should be "entity")
- [ ] "data source configuration" in prose (should be "data source")

---

### 9.2 Update CHANGELOG
**File:** `CHANGELOG.md` or `RELEASE_NOTES.md`

**Add entry:**
```markdown
## [Unreleased]

### Changed
- **BREAKING**: Renamed "configuration" to "project" throughout the codebase
  - `ShapeShiftProject` → `ShapeShiftProject`
  - `Configuration` model → `Project`
  - `ConfigMetadata` → `ProjectMetadata`
  - API endpoints: `/api/v1/configurations` → `/api/v1/projects`
  - Frontend store: `useConfigurationStore` → `useProjectStore`
  - Directory: `configurations/` → `projects/`
- Simplified terminology:
  - "entity configuration" → "entity"
  - "data source configuration" → "data source"
- Preserved `src/configuration/` module as generic application configuration framework
```

---

### 9.3 Update Commit Message
**Conventional commit format:**
```bash
git add -A
git commit -m "refactor!: rename configuration to project throughout codebase

BREAKING CHANGE: Comprehensive terminology update to avoid confusion
between generic application configuration framework and shape shifting projects.

- Renamed ShapeShiftProject → ShapeShiftProject
- Renamed Configuration/ConfigMetadata → Project/ProjectMetadata  
- Updated API endpoints: /api/v1/configurations → /api/v1/projects
- Updated frontend store: useConfigurationStore → useProjectStore
- Renamed directory: configurations/ → projects/
- Simplified terminology: 'entity configuration' → 'entity', 
  'data source configuration' → 'data source'
- Preserved src/configuration/ as generic framework

Closes #XXX"
```

---

## Estimated Impact

### Files to Modify (Approximate)
- **Core (src/):** ~15 files
- **Backend (backend/app/):** ~30 files
- **Frontend (frontend/src/):** ~40 files
- **Tests (tests/ + backend/tests/):** ~50 files
- **Documentation (docs/ + root):** ~20 files
- **Total:** ~155 files

### Lines of Code Changed (Approximate)
- **Core:** ~300 lines
- **Backend:** ~800 lines
- **Frontend:** ~1200 lines
- **Tests:** ~1000 lines
- **Documentation:** ~500 lines
- **Total:** ~3800 lines

---

## Risk Assessment

### High Risk
- ✅ **API endpoint changes** - Breaking change for any external clients
- ✅ **Database migrations** - May need to update stored paths/references
- ✅ **Frontend store state** - May need migration for persisted state

### Medium Risk
- ⚠️ **Import errors** - Many files import from renamed modules
- ⚠️ **Test failures** - Extensive test updates required
- ⚠️ **Type errors** - TypeScript may catch missing updates

### Low Risk
- ℹ️ **Documentation** - No runtime impact
- ℹ️ **Comments** - No runtime impact
- ℹ️ **Variable names** - Caught by tests

---

## Rollback Plan

If issues arise:
1. **Before changes:** Create backup branch: `git branch backup-before-rename`
2. **During changes:** Commit incrementally by phase
3. **If needed:** Reset to previous state: `git reset --hard backup-before-rename`
4. **Alternative:** Revert commit: `git revert HEAD`

---

## Success Criteria

- [ ] All tests pass (core + backend)
- [ ] Frontend builds without TypeScript errors
- [ ] Backend API starts without errors
- [ ] API documentation reflects new endpoints
- [ ] Manual testing of key workflows succeeds
- [ ] No references to old terminology in user-facing text
- [ ] Documentation is consistent
- [ ] Linting passes

---

## Timeline Estimate

- **Phase 1-2 (Core + Backend):** 3-4 hours
- **Phase 3 (Frontend):** 2-3 hours
- **Phase 4 (Tests):** 2-3 hours
- **Phase 5-6 (Files + Docs):** 2-3 hours
- **Phase 7-9 (Testing + Cleanup):** 1-2 hours
- **Total:** 10-15 hours

---

## Notes

- This is a **breaking change** requiring major version bump
- External API clients will need to update endpoint paths
- User documentation/tutorials will need updates
- Consider deprecation warnings if API versioning is supported
- Review and preserve any `src/configuration/` framework code unchanged

