# File Path Handling Refactoring Proposal

## Current State Analysis

### Problem Overview
File-based entities (CSV, Excel, MS Access) need to reference data files that can exist in two locations:
- **Global**: Shared data directory (`GLOBAL_DATA_DIR`) - shared across all projects
- **Local**: Project-specific directory (`PROJECTS_DIR/{project_path}/`) - isolated per project

The current implementation has evolved through two incompatible approaches that now coexist, creating technical debt:

### Evolution of Approaches

#### Approach 1 (Legacy): Environment Variable Prefix
```yaml
entities:
  my_entity:
    options:
      filename: "${GLOBAL_DATA_DIR}/data.xlsx"  # Global file
      # or
      filename: "data.xlsx"                      # Local file (no prefix)
```
- **Stored in YAML**: `${GLOBAL_DATA_DIR}/filename` for global files
- **Resolution**: Environment variable resolution in config layer
- **Problem**: Mixed concerns - storage location encoded in filename string

#### Approach 2 (Current): Explicit Location Field
```yaml
entities:
  my_entity:
    options:
      filename: "data.xlsx"
      location: "global"  # or "local"
```
- **Stored in YAML**: Clean filename + separate location field
- **Resolution**: Multiple scattered resolvers
- **Problem**: Location field doesn't survive API → Core → API roundtrip

### Current Issues

#### 1. Mixed Approaches in Codebase
```python
# backend/app/api/v1/endpoints/entities.py:28-62
def _resolve_file_paths_in_entity(entity_data, project_name):
    """STILL USES LEGACY APPROACH - prepends ${GLOBAL_DATA_DIR}/"""
    if location == "global":
        stored_path = f"${{GLOBAL_DATA_DIR}}/{filename}"  # ❌ Approach 1
    elif location == "local":
        stored_path = filename
    options["filename"] = stored_path
    options.pop("location", None)  # ❌ Removes location info!
```

#### 2. Scattered Resolution Logic
Path resolution happens in 5+ places with inconsistent behavior:

| Location | Purpose | Approach |
|----------|---------|----------|
| `entities.py:_resolve_file_paths_in_entity` | Entity save | Legacy (${VAR}) |
| `project_mapper.py:resolve_file_path` | API → Core | Direct resolution |
| `project_mapper.py:to_core` | API → Core | Calls resolve_file_path |
| `shapeshift_service.py:_resolve_file_paths_in_config` | Preview override | Direct resolution |
| `file_manager.py:_resolve_path` | File operations | Direct resolution |

#### 3. Location Field Loss
```python
# backend/app/mappers/project_mapper.py:183-186
resolved_path = ProjectMapper.resolve_file_path(api_config.filename, filename, location)
options["filename"] = resolved_path  # Absolute path replaces filename
options["location"] = location       # ✅ Kept in to_core()

# But in entities.py:
options.pop("location", None)  # ❌ Removed when saving!
```

Result: **Location semantic is lost** - can't distinguish global vs local files after save.

#### 4. Core Receives Absolute Paths (Correct)
```python
# src/loaders/file_loaders.py:88-91
filename: str = clean_opts.pop("filename")  # Expects absolute path
df: pd.DataFrame = pd.read_csv(filename, **clean_opts)
```
Core loaders correctly expect fully resolved absolute paths, but don't need to know about "location" semantics.

## Proposed Solution

### Design Principles

1. **Single Source of Truth**: YAML stores minimal portable data (`filename` + `location`)
2. **Clear Layer Responsibilities**:
   - **API Layer**: Manages `location` field for UI/user
   - **Mapper Layer**: Resolves paths at boundaries (API → Core, Core → API)
   - **Core Layer**: Works with absolute paths only
3. **Centralized Resolution**: One resolver, consistent behavior
4. **Preserve Semantics**: Location field survives full lifecycle

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ YAML File (Source of Truth)                                │
│  entities:                                                   │
│    my_entity:                                               │
│      options:                                               │
│        filename: "data.xlsx"      ← Relative filename       │
│        location: "global"          ← Storage location        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ API Layer (Pydantic Models)                                │
│  Entity.options = {                                         │
│    "filename": "data.xlsx",        ← Preserved             │
│    "location": "global"             ← Preserved             │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────[ FilePathResolver ]──────────────┐
│  resolve(filename, location, project_name) :                │
│    if location == "global":                                 │
│      return GLOBAL_DATA_DIR / filename                      │
│    else:                                                    │
│      return PROJECTS_DIR / project_path / filename          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Core Layer (ShapeShiftProject)                             │
│  entity.options = {                                         │
│    "filename": "/abs/path/to/data.xlsx"  ← Absolute        │
│  }                                                          │
│  (location field removed - not needed in Core)              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Loader (CsvLoader, ExcelLoader, etc.)                      │
│  pd.read_csv("/abs/path/to/data.xlsx")  ← Just works       │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Plan

#### Phase 1: Create Centralized Resolver

**New file**: `backend/app/utils/file_path_resolver.py`

```python
"""Centralized file path resolution for file-based data sources."""

from pathlib import Path
from typing import Literal

from backend.app.core.config import Settings, get_settings
from backend.app.mappers.project_name_mapper import ProjectNameMapper
from loguru import logger


class FilePathResolver:
    """
    Centralized file path resolution for file-based entities.
    
    Responsibilities:
    - Resolve relative filenames to absolute paths based on location
    - Maintain consistent behavior across all file operations
    - Support both global (shared) and local (project-specific) files
    
    Usage:
        resolver = FilePathResolver(settings)
        abs_path = resolver.resolve("data.xlsx", "global", "my:project")
    """
    
    def __init__(self, settings: Settings | None = None):
        """Initialize resolver with settings."""
        self.settings = settings or get_settings()
    
    def resolve(
        self, 
        filename: str, 
        location: Literal["global", "local"], 
        project_name: str | None = None
    ) -> Path:
        """
        Resolve a filename to absolute path based on location.
        
        Args:
            filename: Relative filename (e.g., "data.xlsx")
            location: Storage location - "global" (GLOBAL_DATA_DIR) or "local" (project-specific)
            project_name: Project name (required for local files, uses ":" for nested folders)
        
        Returns:
            Absolute Path to the file
        
        Raises:
            ValueError: If location is invalid or project_name missing for local files
        
        Examples:
            >>> resolver.resolve("data.xlsx", "global", "my_project")
            Path("/app/shared/shared-data/data.xlsx")
            
            >>> resolver.resolve("data.xlsx", "local", "dendro:sites")
            Path("/app/projects/dendro/sites/data.xlsx")
        """
        if location not in ["global", "local"]:
            raise ValueError(f"Invalid location: {location}. Must be 'global' or 'local'")
        
        if location == "global":
            resolved_path = self.settings.GLOBAL_DATA_DIR / filename
            logger.debug(f"Resolved global file: {filename} -> {resolved_path}")
            return resolved_path
        
        if location == "local":
            if not project_name:
                raise ValueError(f"project_name required for local file resolution: {filename}")
            
            # Convert project name (e.g., "dendro:sites") to path ("dendro/sites")
            project_path = ProjectNameMapper.to_path(project_name)
            resolved_path = self.settings.PROJECTS_DIR / project_path / filename
            logger.debug(f"Resolved local file: {filename} ({project_name}) -> {resolved_path}")
            return resolved_path
        
        # Unreachable due to validation above, but for type safety
        raise ValueError(f"Unexpected location value: {location}")
    
    def extract_location(self, filename: str) -> tuple[str, Literal["global", "local"]]:
        """
        Extract location from legacy filename format (with ${GLOBAL_DATA_DIR} prefix).
        
        This supports backward compatibility with old YAML files using the legacy format.
        
        Args:
            filename: Filename that may contain ${GLOBAL_DATA_DIR}/ prefix
        
        Returns:
            Tuple of (clean_filename, location)
        
        Examples:
            >>> resolver.extract_location("${GLOBAL_DATA_DIR}/data.xlsx")
            ("data.xlsx", "global")
            
            >>> resolver.extract_location("data.xlsx")
            ("data.xlsx", "local")
        """
        if filename.startswith("${GLOBAL_DATA_DIR}/"):
            clean_filename = filename.replace("${GLOBAL_DATA_DIR}/", "")
            return (clean_filename, "global")
        
        return (filename, "local")
```

#### Phase 2: Update ProjectMapper (Boundary Layer)

**File**: `backend/app/mappers/project_mapper.py`

```python
@staticmethod
def to_core(api_config: Project) -> ShapeShiftProject:
    """Convert API Project to Core ShapeShiftProject with resolved file paths."""
    cfg_dict = api_config.to_core_dict()
    
    # Initialize resolver
    resolver = FilePathResolver(settings)
    
    # Resolve file paths in entity options based on location field
    entities = cfg_dict.get("entities", {})
    for entity_name, entity_dict in entities.items():
        options = entity_dict.get("options")
        if not options or not isinstance(options, dict):
            continue
        
        filename: str | None = options.get("filename")
        if not filename:
            continue
        
        # Get location (explicit field or extract from legacy format)
        location: Literal["global", "local"] | None = options.get("location")
        if not location:
            # Support legacy format: "${GLOBAL_DATA_DIR}/file.xlsx"
            filename, location = resolver.extract_location(filename)
        
        # Resolve to absolute path
        try:
            resolved_path = resolver.resolve(filename, location, api_config.filename)
            options["filename"] = str(resolved_path)
            # Don't store location in Core - it's implicit in the absolute path
            options.pop("location", None)
            logger.debug(f"Entity '{entity_name}': {filename} ({location}) -> {resolved_path}")
        except ValueError as e:
            logger.warning(f"Failed to resolve path for entity '{entity_name}': {e}")
            # Keep original filename if resolution fails
    
    # Create Core project and resolve directives
    project = ShapeShiftProject(cfg=cfg_dict, filename=api_config.filename or "")
    
    if not project.is_resolved():
        project = project.resolve(
            filename=api_config.filename,
            env_prefix=settings.env_prefix,
            env_filename=settings.env_file,
        )
    
    return project

@staticmethod
def to_api_config(core_project: ShapeShiftProject, project_name: str | None) -> Project:
    """Convert Core ShapeShiftProject to API Project with location semantics restored."""
    cfg_dict = dict(core_project.cfg)
    
    # Initialize resolver
    resolver = FilePathResolver(settings)
    
    # Restore location semantics for API layer
    entities = cfg_dict.get("entities", {})
    for entity_dict in entities.values():
        options = entity_dict.get("options")
        if not options or not isinstance(options, dict):
            continue
        
        filename_str: str | None = options.get("filename")
        if not filename_str:
            continue
        
        filename_path = Path(filename_str)
        
        # Determine location by checking if path is under GLOBAL_DATA_DIR or PROJECTS_DIR
        try:
            # Try global first
            filename_path.relative_to(settings.GLOBAL_DATA_DIR)
            location = "global"
            relative_filename = str(filename_path.relative_to(settings.GLOBAL_DATA_DIR))
        except ValueError:
            # Try local (project-specific)
            try:
                if project_name:
                    project_path = ProjectNameMapper.to_path(project_name)
                    project_dir = settings.PROJECTS_DIR / project_path
                    filename_path.relative_to(project_dir)
                    location = "local"
                    relative_filename = str(filename_path.relative_to(project_dir))
                else:
                    # Fallback: assume local if can't determine
                    location = "local"
                    relative_filename = filename_path.name
            except ValueError:
                # Path is outside both directories - keep absolute path
                logger.warning(f"File path outside managed directories: {filename_str}")
                continue
        
        # Store relative filename + location for API
        options["filename"] = relative_filename
        options["location"] = location
    
    return Project.from_core_config(cfg_dict, project_name)
```

#### Phase 3: Remove Scattered Resolvers

**Remove/Update these functions:**

1. **`backend/app/api/v1/endpoints/entities.py`**:
   ```python
   # DELETE: _resolve_file_paths_in_entity function (lines 28-62)
   # It's now handled by ProjectMapper.to_core()
   
   # REMOVE calls at lines 166, 190:
   # _resolve_file_paths_in_entity(request.entity_data, project_name)
   ```

2. **`backend/app/mappers/project_mapper.py`**:
   ```python
   # DELETE: resolve_file_path static method (lines 198-213)
   # Replaced by FilePathResolver.resolve()
   ```

3. **`backend/app/services/shapeshift_service.py`**:
   ```python
   # UPDATE: _resolve_file_paths_in_config method (lines 37-67)
   # Use FilePathResolver instead of inline resolution
   
   def _resolve_file_paths_in_config(self, entity_config: dict, project_name: str):
       """Resolve file paths using centralized resolver."""
       options = entity_config.get("options")
       if not options or not isinstance(options, dict):
           return
       
       filename = options.get("filename")
       location = options.get("location", "global")
       if not filename:
           return
       
       # Use centralized resolver
       resolver = FilePathResolver(self.settings)
       try:
           resolved_path = resolver.resolve(filename, location, project_name)
           options["filename"] = str(resolved_path)
           logger.debug(f"Resolved file for preview: {filename} ({location}) -> {resolved_path}")
       except ValueError as e:
           logger.warning(f"Failed to resolve preview file path: {e}")
   ```

#### Phase 4: Update Tests

**New test file**: `backend/tests/utils/test_file_path_resolver.py`

```python
"""Tests for FilePathResolver."""

import pytest
from pathlib import Path
from backend.app.utils.file_path_resolver import FilePathResolver
from backend.app.core.config import Settings


class TestFilePathResolver:
    """Test file path resolution logic."""
    
    @pytest.fixture
    def settings(self, tmp_path):
        """Create test settings with temporary directories."""
        settings = Settings()
        settings.GLOBAL_DATA_DIR = tmp_path / "global"
        settings.PROJECTS_DIR = tmp_path / "projects"
        settings.GLOBAL_DATA_DIR.mkdir(parents=True)
        settings.PROJECTS_DIR.mkdir(parents=True)
        return settings
    
    @pytest.fixture
    def resolver(self, settings):
        """Create resolver with test settings."""
        return FilePathResolver(settings)
    
    def test_resolve_global_file(self, resolver, settings):
        """Should resolve global file to GLOBAL_DATA_DIR."""
        result = resolver.resolve("data.xlsx", "global", "my_project")
        expected = settings.GLOBAL_DATA_DIR / "data.xlsx"
        assert result == expected
    
    def test_resolve_local_file(self, resolver, settings):
        """Should resolve local file to project directory."""
        result = resolver.resolve("data.xlsx", "local", "dendro:sites")
        expected = settings.PROJECTS_DIR / "dendro" / "sites" / "data.xlsx"
        assert result == expected
    
    def test_resolve_local_requires_project_name(self, resolver):
        """Should raise ValueError when project_name missing for local file."""
        with pytest.raises(ValueError, match="project_name required"):
            resolver.resolve("data.xlsx", "local", None)
    
    def test_resolve_invalid_location(self, resolver):
        """Should raise ValueError for invalid location."""
        with pytest.raises(ValueError, match="Invalid location"):
            resolver.resolve("data.xlsx", "invalid", "project")
    
    def test_extract_location_from_legacy_format(self, resolver):
        """Should extract location from ${GLOBAL_DATA_DIR} prefix."""
        filename, location = resolver.extract_location("${GLOBAL_DATA_DIR}/data.xlsx")
        assert filename == "data.xlsx"
        assert location == "global"
    
    def test_extract_location_from_plain_filename(self, resolver):
        """Should treat plain filename as local."""
        filename, location = resolver.extract_location("data.xlsx")
        assert filename == "data.xlsx"
        assert location == "local"
```

### Migration Strategy

#### For Existing YAML Files

**Option 1: Automatic Migration (Recommended)**
Add migration logic to ProjectMapper.to_api_config() that handles legacy files transparently:

```python
def to_api_config(core_project, project_name):
    # ... entity processing ...
    
    # Handle legacy files with ${GLOBAL_DATA_DIR} prefix
    if filename_str.startswith("${GLOBAL_DATA_DIR}/"):
        options["filename"] = filename_str.replace("${GLOBAL_DATA_DIR}/", "")
        options["location"] = "global"
    # Handle files without location field (assume local for backward compat)
    elif "location" not in options:
        options["location"] = "local"
```

**Option 2: Manual Migration Script**
```bash
python -m backend.app.scripts.migrate_file_paths
```

#### Backward Compatibility

1. **Reading**: Support both formats during load
   - Files with `${GLOBAL_DATA_DIR}/` → Extract location automatically
   - Files with `location` field → Use directly
   - Files with neither → Default to "local"

2. **Writing**: Always save with new format (filename + location)

3. **Grace Period**: Keep legacy support for 2-3 releases, then remove

### Benefits of This Approach

1. **✅ Single Responsibility**: FilePathResolver owns all path resolution logic
2. **✅ Clear Boundaries**: Resolution only at API ↔ Core mapper layer
3. **✅ Preserved Semantics**: Location field survives full lifecycle
4. **✅ Core Simplicity**: Core only sees absolute paths (no location awareness needed)
5. **✅ Testability**: Centralized logic is easier to test comprehensively
6. **✅ Portability**: YAML files remain portable (relative paths + location)
7. **✅ Maintainability**: One place to change if requirements evolve

### Rollout Checklist

- [ ] Phase 1: Implement FilePathResolver
- [ ] Phase 2: Update ProjectMapper
- [ ] Phase 3: Remove scattered resolvers
- [ ] Phase 4: Add comprehensive tests
- [ ] Phase 5: Test with existing projects (backward compat)
- [ ] Phase 6: Update documentation
- [ ] Phase 7: Deploy and monitor

### Future Enhancements

1. **Path Validation**: Check file existence during resolution
2. **Path Normalization**: Handle ../ and ./ in filenames
3. **Symbolic Links**: Resolve symlinks to canonical paths
4. **Cloud Storage**: Extend resolver to support S3/Azure/GCS
5. **Relative Paths**: Support project-relative paths for local files

---

**Status**: Proposed  
**Author**: AI Assistant  
**Date**: 2026-02-18  
**Version**: 1.0
